"""Only this adapter knows the OpenAI SDK. No SDK objects escape it."""

import math
from dataclasses import dataclass
from typing import Protocol

import openai
from django.conf import settings
from django.utils.module_loading import import_string

from .configuration import validate_provider_configuration
from .exceptions import ProviderTimeout, ProviderUnavailable


@dataclass
class Generation:
    items: list[dict]
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class GenerationProvider(Protocol):
    def generate(
        self, *, messages, instructions, tools, tool_choice, timeout
    ) -> Generation: ...


class EmbeddingProvider(Protocol):
    def embed(
        self, texts: list[str], *, timeout: float | None = None
    ) -> list[list[float]]: ...


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "insufficient_evidence": {"type": "boolean"},
    },
    "required": ["answer", "source_ids", "insufficient_evidence"],
    "additionalProperties": False,
}


def validate_embeddings(vectors, count):
    if len(vectors) != count:
        raise ProviderUnavailable()
    for vector in vectors:
        if (
            len(vector) != settings.AI_EMBEDDING_DIMENSIONS
            or not all(math.isfinite(v) for v in vector)
            or not any(vector)
        ):
            raise ProviderUnavailable()
    return vectors


class OpenAIProvider:
    def _client(self, timeout):
        if not settings.OPENAI_API_KEY:
            raise ProviderUnavailable("The AI service has not been configured.")
        return openai.OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=min(timeout, settings.AI_PROVIDER_TIMEOUT),
            max_retries=0,  # Orchestration owns the latency/cost budget.
        )

    def generate(self, *, messages, instructions, tools, tool_choice, timeout):
        try:
            with self._client(timeout) as client:
                response = client.responses.create(
                    model=settings.AI_MODEL,
                    instructions=instructions,
                    input=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    parallel_tool_calls=False,
                    max_output_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                    store=False,
                    # Preserve encrypted reasoning for stateless multi-step calls.
                    include=["reasoning.encrypted_content"],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "f1_answer",
                            "strict": True,
                            "schema": ANSWER_SCHEMA,
                        }
                    },
                )
            if response.status != "completed":
                raise ProviderUnavailable(
                    "The AI provider returned an incomplete response."
                )
            return Generation(
                items=[
                    item.model_dump(mode="json", exclude_none=True)
                    for item in response.output
                ],
                text=response.output_text,
                input_tokens=response.usage.input_tokens if response.usage else 0,
                output_tokens=response.usage.output_tokens if response.usage else 0,
            )
        except openai.APITimeoutError:
            raise ProviderTimeout() from None
        except openai.APIError:
            raise ProviderUnavailable() from None

    def embed(self, texts, *, timeout=None):
        try:
            with self._client(timeout or settings.AI_PROVIDER_TIMEOUT) as client:
                response = client.embeddings.create(
                    model=settings.AI_EMBEDDING_MODEL,
                    input=texts,
                    dimensions=settings.AI_EMBEDDING_DIMENSIONS,
                )
            vectors = [
                item.embedding
                for item in sorted(response.data, key=lambda item: item.index)
            ]
            return validate_embeddings(vectors, len(texts))
        except openai.APITimeoutError:
            raise ProviderTimeout() from None
        except openai.APIError:
            raise ProviderUnavailable() from None


def generation_provider() -> GenerationProvider:
    validate_provider_configuration()
    return import_string(settings.AI_GENERATION_PROVIDER)()


def embedding_provider() -> EmbeddingProvider:
    validate_provider_configuration()
    return import_string(settings.AI_EMBEDDING_PROVIDER)()
