"""Custom DRF exception handler so every error looks like {"detail": "<message>"}."""

from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def _first_message(data):
    """Dig the first human-readable message out of DRF's nested error structure."""
    if isinstance(data, dict):
        for key, value in data.items():
            message = _first_message(value)
            # Name the field unless the error is not about one specific field.
            if key in ("detail", "non_field_errors"):
                return message
            return f"{key}: {message}"
    if isinstance(data, (list, tuple)):
        return _first_message(data[0]) if data else ""
    return str(data)


def api_exception_handler(exc, context):
    """
    Wrap DRF's default handler.

    DRF validation errors look like {"email": ["Enter a valid email address."]}, but the React
    app shows `error.response.data.detail` directly, so we flatten them into one string and keep
    the original structure under "errors" for anyone who wants field-level messages.
    """
    response = exception_handler(exc, context)  # DRF's default: handles 401/403/404/400...
    if response is not None and isinstance(exc, ValidationError):
        response.data = {"detail": _first_message(response.data), "errors": response.data}
    return response
