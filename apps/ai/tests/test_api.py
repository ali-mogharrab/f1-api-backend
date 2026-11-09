from unittest.mock import patch

from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ai.exceptions import ProviderTimeout, ProviderUnavailable
from apps.ai.models import Conversation, Message
from apps.ai.orchestration import Analysis

from .helpers import user


class APITests(APITestCase):
    @patch("apps.ai.orchestration.generation_provider")
    def test_chat_runs_real_orchestration_tools_and_persists_verified_sources(
        self, provider_factory
    ):
        from .helpers import answer, dataset, function_call

        data = dataset()
        source_id = f"race_result:{data['result'].pk}"
        provider_factory.return_value.generate.side_effect = [
            function_call(
                "get_driver_recent_results",
                {"driver": "NOR", "season": 2026, "limit": 5},
            ),
            answer(
                f"Norris scored 25 points in one recorded race [{source_id}].",
                [source_id],
            ),
        ]
        self.login()
        response = self.client.post(
            self.url, {"message": "How did Norris perform in 2026?"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        result = response.data["data"]
        self.assertEqual(result["sources"][0]["entity_id"], str(data["result"].pk))
        self.assertEqual(
            result["metadata"]["tool_calls"], ["get_driver_recent_results"]
        )
        saved = Message.objects.get(
            conversation_id=result["conversation_id"], role="assistant"
        )
        self.assertEqual(saved.sources, result["sources"])

    def test_ai_openapi_contract_has_all_endpoints(self):
        from django.urls import include, path
        from drf_spectacular.generators import SchemaGenerator
        from drf_spectacular.validation import validate_schema

        schema = SchemaGenerator(
            patterns=[path("api/ai/", include("apps.ai.urls"))]
        ).get_schema(public=True)
        validate_schema(schema)
        self.assertEqual(
            set(schema["paths"]),
            {"/api/ai/chat/", "/api/ai/conversations/", "/api/ai/conversations/{id}/"},
        )
        self.assertIn("503", schema["paths"]["/api/ai/chat/"]["post"]["responses"])

    def setUp(self):
        caches["ai"].clear()
        self.user = user()
        self.other = user("other")
        self.conversation = Conversation.objects.create(
            user=self.other, title="Private"
        )
        self.url = reverse("ai:chat")

    def login(self):
        token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_auth_required_on_all_endpoints(self):
        self.assertEqual(
            self.client.post(self.url, {"message": "Question"}).status_code, 401
        )
        self.assertEqual(
            self.client.get(reverse("ai:conversation-list")).status_code, 401
        )
        self.assertEqual(
            self.client.get(
                reverse("ai:conversation-detail", args=[self.conversation.pk])
            ).status_code,
            401,
        )

    @patch("apps.ai.views.analyze")
    def test_ownership_prevents_read_and_continue(self, analyze):
        self.login()
        detail = self.client.get(
            reverse("ai:conversation-detail", args=[self.conversation.pk])
        )
        self.assertEqual(detail.status_code, 404)
        response = self.client.post(
            self.url,
            {"message": "Question", "conversation_id": str(self.conversation.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        analyze.assert_not_called()
        response = self.client.get(reverse("ai:conversation-list"))
        self.assertEqual(response.data["count"], 0)

    @patch(
        "apps.ai.views.analyze",
        return_value=Analysis(
            "Evidence is unavailable.", [], {"insufficient_evidence": True}
        ),
    )
    def test_jwt_chat_contract_and_history(self, analyze):
        self.login()
        response = self.client.post(self.url, {"message": "Question"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertEqual(
            set(data), {"conversation_id", "answer", "sources", "metadata"}
        )
        conversation = Conversation.objects.get(pk=data["conversation_id"])
        self.assertEqual(conversation.user, self.user)
        self.assertEqual(Message.objects.filter(conversation=conversation).count(), 2)
        response = self.client.post(
            self.url,
            {"message": "Follow up", "conversation_id": str(conversation.pk)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        detail = self.client.get(
            reverse("ai:conversation-detail", args=[conversation.pk])
        )
        self.assertEqual(
            [m["sequence"] for m in detail.data["data"]["messages"]], [0, 1, 2, 3]
        )
        self.assertEqual(
            self.client.get(reverse("ai:conversation-list")).data["count"], 1
        )

    @patch("apps.ai.views.analyze")
    def test_input_validation(self, analyze):
        self.login()
        for payload in [
            {},
            {"message": " "},
            {"message": "x" * 4001},
            {"message": "Question", "conversation_id": "invalid"},
        ]:
            self.assertEqual(
                self.client.post(self.url, payload, format="json").status_code, 400
            )
        analyze.assert_not_called()

    @patch("apps.ai.views.analyze")
    def test_provider_failures_do_not_persist_turns_or_leak_errors(self, analyze):
        self.login()
        for error, code in [(ProviderUnavailable(), 503), (ProviderTimeout(), 504)]:
            analyze.side_effect = error
            response = self.client.post(
                self.url, {"message": "Question"}, format="json"
            )
            self.assertEqual(response.status_code, code)
            self.assertFalse(response.data["success"])
        self.assertEqual(Conversation.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Message.objects.count(), 0)

    @override_settings(AI_THROTTLE_RATE="1/hour")
    @patch("apps.ai.views.analyze", return_value=Analysis("No evidence", [], {}))
    def test_per_user_throttle(self, analyze):
        self.login()
        self.assertEqual(
            self.client.post(self.url, {"message": "Question"}).status_code, 200
        )
        self.assertEqual(
            self.client.post(self.url, {"message": "Question"}).status_code, 429
        )
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.post(self.url, {"message": "Question"}).status_code, 200
        )

    @patch("apps.ai.views.analyze")
    def test_conversation_limit(self, analyze):
        self.login()
        conversation = Conversation.objects.create(
            user=self.user, title="Full", revision=50
        )
        response = self.client.post(
            self.url, {"message": "Question", "conversation_id": str(conversation.pk)}
        )
        self.assertEqual(response.status_code, 409)
        analyze.assert_not_called()

    @patch("apps.ai.views.analyze")
    def test_concurrent_revision_does_not_append_out_of_order(self, analyze):
        self.login()
        conversation = Conversation.objects.create(user=self.user, title="Concurrent")

        def concurrent(*args, **kwargs):
            Conversation.objects.filter(pk=conversation.pk).update(revision=1)
            return Analysis("No evidence", [], {})

        analyze.side_effect = concurrent
        response = self.client.post(
            self.url, {"message": "Question", "conversation_id": str(conversation.pk)}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Message.objects.count(), 0)
