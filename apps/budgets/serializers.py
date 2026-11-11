from decimal import Decimal

from rest_framework import serializers

from apps.expenses.serializers import CategoryField

from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    category = CategoryField(max_length=50)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)

    class Meta:
        model = Budget
        fields = ("id", "category", "amount", "month", "year")
        # DRF would turn the model's UniqueConstraint into a validator that rejects an existing
        # budget. We want an upsert instead, so the view handles uniqueness itself.
        validators = []


class BudgetAlertSerializer(serializers.Serializer):
    """Output shape of one alert. Used to build the response and (later) the API docs."""

    category = serializers.CharField()
    budget_limit = serializers.DecimalField(max_digits=12, decimal_places=2)
    spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentage_used = serializers.DecimalField(max_digits=8, decimal_places=2)
    status = serializers.ChoiceField(choices=["ok", "warning", "exceeded"])


class BudgetAlertsResponseSerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    alerts = BudgetAlertSerializer(many=True)
