from django.conf import settings
from django.core.checks import Error, register

from .configuration import provider_configuration_errors


@register()
def ai_configuration(app_configs, **kwargs):
    errors = []
    bounds = {
        "AI_MAX_TOOL_CALLS": (1, 12),
        "AI_MAX_OUTPUT_TOKENS": (256, 16000),
        "RAG_TOP_K": (1, 20),
        "RAG_CHUNK_SIZE": (100, 4000),
        "AI_EMBEDDING_DIMENSIONS": (1, 3072),
        "AI_PROVIDER_TIMEOUT": (1, 120),
        "AI_REQUEST_TIMEOUT": (1, 300),
    }
    for name, (low, high) in bounds.items():
        if not low <= getattr(settings, name) <= high:
            errors.append(
                Error(f"{name} must be between {low} and {high}.", id="ai.E001")
            )
    if not 0 <= settings.RAG_CHUNK_OVERLAP < settings.RAG_CHUNK_SIZE:
        errors.append(
            Error(
                "RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE and nonnegative.",
                id="ai.E002",
            )
        )
    if not -1 <= settings.RAG_MIN_SIMILARITY <= 1:
        errors.append(
            Error("RAG_MIN_SIMILARITY must be between -1 and 1.", id="ai.E003")
        )
    errors.extend(
        Error(message, id="ai.E004") for message in provider_configuration_errors()
    )
    return errors
