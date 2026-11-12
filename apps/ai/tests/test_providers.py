import json
from unittest.mock import Mock, patch

import httpx
import openai
from django.test import SimpleTestCase, override_settings

from apps.ai.exceptions import ProviderTimeout, ProviderUnavailable
from apps.ai.providers import OpenAIProvider
from apps.ai.tools import tool_definitions


@override_settings(OPENAI_API_KEY="test-key-never-real", AI_EMBEDDING_DIMENSIONS=3)
class ProviderTests(SimpleTestCase):
    @patch("apps.ai.providers.openai.OpenAI")
    def test_malformed_sdk_responses_are_sanitized(self, factory):
        client = factory.return_value.__enter__.return_value
        client.embeddings.create.return_value = Mock(data=None)
        with self.assertRaises(ProviderUnavailable):
            OpenAIProvider().embed(["question"])
        client.responses.create.return_value = Mock(status="completed", output=None)
        with self.assertRaises(ProviderUnavailable):
            OpenAIProvider().generate(
                messages=[],
                instructions="Trusted",
                tools=[],
                tool_choice="required",
                timeout=10,
            )

    def test_real_sdk_serializes_responses_contract_without_network(self):
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "id": "resp_offline",
                    "object": "response",
                    "created_at": 1,
                    "model": "contract-test",
                    "status": "completed",
                    "output": [
                        {
                            "type": "reasoning",
                            "id": "reasoning_offline",
                            "summary": [],
                            "encrypted_content": "opaque-test-data",
                        },
                        {
                            "type": "function_call",
                            "id": "fc_offline",
                            "call_id": "call_offline",
                            "name": "get_constructor_standings",
                            "arguments": '{"season":2026,"team":null}',
                            "status": "completed",
                        },
                    ],
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 8,
                        "total_tokens": 20,
                        "input_tokens_details": {"cached_tokens": 0},
                        "output_tokens_details": {"reasoning_tokens": 3},
                    },
                },
            )

        client = openai.OpenAI(
            api_key="test-key-never-real",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        with patch.object(OpenAIProvider, "_client", return_value=client):
            response = OpenAIProvider().generate(
                messages=[{"role": "user", "content": "Question"}],
                instructions="Trusted",
                tools=tool_definitions(),
                tool_choice="required",
                timeout=10,
            )
        self.assertEqual(response.items[1]["call_id"], "call_offline")
        self.assertEqual(response.items[0]["encrypted_content"], "opaque-test-data")
        self.assertEqual(response.output_tokens, 8)
        self.assertEqual(requests[0]["include"], ["reasoning.encrypted_content"])
        self.assertTrue(all(tool["strict"] for tool in requests[0]["tools"]))
        self.assertFalse(requests[0]["store"])

    @patch("apps.ai.providers.openai.OpenAI")
    def test_duplicate_embedding_indices_are_rejected(self, factory):
        client = factory.return_value.__enter__.return_value
        client.embeddings.create.return_value = Mock(
            data=[
                Mock(index=0, embedding=[1.0, 0.0, 0.0]),
                Mock(index=0, embedding=[0.0, 1.0, 0.0]),
            ]
        )
        with self.assertRaises(ProviderUnavailable):
            OpenAIProvider().embed(["first", "second"])

    @patch("apps.ai.providers.openai.OpenAI")
    def test_responses_api_parameters_and_normalization(self, factory):
        client = factory.return_value.__enter__.return_value
        client.responses.create.return_value = Mock(
            status="completed",
            output=[],
            output_text="{}",
            usage=Mock(input_tokens=10, output_tokens=5),
        )
        result = OpenAIProvider().generate(
            messages=[{"role": "user", "content": "Question"}],
            instructions="system",
            tools=[],
            tool_choice="required",
            timeout=10,
        )
        kwargs = client.responses.create.call_args.kwargs
        self.assertFalse(kwargs["store"])
        self.assertFalse(kwargs["parallel_tool_calls"])
        self.assertEqual(kwargs["text"]["format"]["type"], "json_schema")
        self.assertEqual(factory.call_args.kwargs["max_retries"], 0)
        self.assertEqual(result.input_tokens, 10)

    @patch("apps.ai.providers.openai.OpenAI")
    def test_embedding_order_and_dimensions(self, factory):
        client = factory.return_value.__enter__.return_value
        client.embeddings.create.return_value = Mock(
            data=[
                Mock(index=1, embedding=[0.0, 1.0, 0.0]),
                Mock(index=0, embedding=[1.0, 0.0, 0.0]),
            ]
        )
        self.assertEqual(
            OpenAIProvider().embed(["first", "second"]),
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        )
        self.assertEqual(client.embeddings.create.call_args.kwargs["dimensions"], 3)

    @patch("apps.ai.providers.openai.OpenAI")
    def test_timeout_and_api_failures_are_sanitized(self, factory):
        client = factory.return_value.__enter__.return_value
        request = httpx.Request("POST", "https://api.openai.com/v1/responses")
        for error, expected in [
            (openai.APITimeoutError(request=request), ProviderTimeout),
            (
                openai.APIConnectionError(request=request, message="sensitive body"),
                ProviderUnavailable,
            ),
        ]:
            client.embeddings.create.side_effect = error
            with self.assertRaises(expected) as caught:
                OpenAIProvider().embed(["question"])
            self.assertNotIn("sensitive", str(caught.exception))

    @override_settings(OPENAI_API_KEY="")
    def test_missing_credentials_fail_cleanly(self):
        with self.assertRaises(ProviderUnavailable):
            OpenAIProvider().embed(["text"])
