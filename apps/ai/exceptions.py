from rest_framework.exceptions import APIException


class ProviderUnavailable(APIException):
    status_code = 503
    default_detail = "The AI provider is unavailable. Please try again later."
    default_code = "ai_unavailable"


class ProviderTimeout(APIException):
    status_code = 504
    default_detail = "The AI request timed out. Please try again."
    default_code = "ai_timeout"


class ConversationConflict(APIException):
    status_code = 409
    default_detail = (
        "This conversation changed during the request. Reload it and retry."
    )


class ConversationLimit(APIException):
    status_code = 409
    default_detail = "This conversation is full. Start a new conversation."


class ToolInputError(ValueError):
    """A safe, user-visible validation/resolution failure."""
