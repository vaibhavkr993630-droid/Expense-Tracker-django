"""Small helpers shared by the API-documentation annotations."""

from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    """Shape of every error response (see config/exceptions.py)."""

    detail = serializers.CharField(help_text="Human-readable message.")
    errors = serializers.JSONField(required=False, help_text="Field-level messages for validation errors.")
