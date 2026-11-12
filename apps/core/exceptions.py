from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(
            exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        )
    response = exception_handler(exc, context)

    if response is None:
        return response

    original_data = response.data

    message = "Something went wrong."
    errors = original_data

    if isinstance(original_data, dict):
        if "detail" in original_data:
            message = str(original_data["detail"])
            errors = None
        else:
            message = "Validation error."
            errors = original_data

    elif isinstance(original_data, list):
        message = "Validation error."
        errors = original_data

    response.data = {
        "success": False,
        "message": message,
        "errors": errors,
    }

    return response
