"""Fail closed on demo selection, independently of DEBUG or provider failures."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


def provider_configuration_errors():
    mode = settings.AI_MODE
    if mode not in {"openai", "demo"}:
        return ["AI_MODE must be openai or demo."]
    try:
        demo_classes = [
            bool(getattr(import_string(path), "is_demo", False))
            for path in (
                settings.AI_GENERATION_PROVIDER,
                settings.AI_EMBEDDING_PROVIDER,
            )
        ]
    except (ImportError, AttributeError):
        return ["An AI provider class cannot be loaded."]
    if mode == "demo" or any(demo_classes):
        if mode != "demo" or not all(demo_classes):
            return [
                "Demo mode requires both demo providers; mixed real/demo providers are disabled."
            ]
        if (
            settings.SETTINGS_MODULE == "config.settings.production"
            or not settings.AI_DEMO_ALLOWED
            or settings.AI_ENVIRONMENT
            not in {
                "development",
                "test",
            }
        ):
            return [
                "Demo providers are permitted only by explicit development/test settings, never in production."
            ]
        if (
            settings.AI_MODEL != "scripted-demo-v1"
            or settings.AI_EMBEDDING_MODEL != "demo-token-hash-v1"
        ):
            return ["Demo providers require their versioned demo model identifiers."]
        if settings.AI_EMBEDDING_DIMENSIONS < 64:
            return ["Demo token-hash embeddings require at least 64 dimensions."]
    return []


def validate_provider_configuration():
    errors = provider_configuration_errors()
    if errors:
        raise ImproperlyConfigured(" ".join(errors))


def require_demo_configuration():
    validate_provider_configuration()
    if settings.AI_MODE != "demo":
        raise ImproperlyConfigured(
            "Demo providers require explicit offline demo settings."
        )
