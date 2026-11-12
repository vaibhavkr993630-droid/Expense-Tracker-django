from rest_framework import serializers


class RequiredPeriodQuerySerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class TrendQuerySerializer(serializers.Serializer):
    months = serializers.IntegerField(min_value=1, max_value=24, required=False, default=6)


def _money():
    return serializers.DecimalField(max_digits=14, decimal_places=2)


class MonthlySummarySerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    total_expenses = _money()
    expense_count = serializers.IntegerField()
    average_expense = _money()


class CategoryItemSerializer(serializers.Serializer):
    category = serializers.CharField()
    total = _money()
    count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=6, decimal_places=2)


class CategoryBreakdownSerializer(serializers.Serializer):
    grand_total = _money()
    categories = CategoryItemSerializer(many=True)


class TrendItemSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    total_expenses = _money()
    expense_count = serializers.IntegerField()


class TrendSerializer(serializers.Serializer):
    months = TrendItemSerializer(many=True)
