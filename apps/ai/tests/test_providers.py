from unittest.mock import Mock, patch

import httpx
import openai
from django.test import SimpleTestCase, override_settings

from apps.ai.exceptions import ProviderTimeout, ProviderUnavailable
from apps.ai.providers import OpenAIProvider


@override_settings(OPENAI_API_KEY="test-key-never-real", AI_EMBEDDING_DIMENSIONS=3)
class ProviderTests(SimpleTestCase):
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
