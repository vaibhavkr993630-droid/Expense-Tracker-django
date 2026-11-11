from django.utils import timezone
from rest_framework import serializers


class PeriodQuerySerializer(serializers.Serializer):
    """
    Validates the optional ?month=&year= query parameters used by several endpoints.

    Serializers are not only for request bodies: validating query parameters with one keeps the
    rules (1-12, 2000-2100) and the error format identical everywhere.
    """

    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)


def get_month_and_year(request):
    """Read ?month=&year= from the request, defaulting to the current month/year."""
    serializer = PeriodQuerySerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    today = timezone.localdate()
    return (
        serializer.validated_data.get("month", today.month),
        serializer.validated_data.get("year", today.year),
    )
