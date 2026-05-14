from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    status_code = response.status_code
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
