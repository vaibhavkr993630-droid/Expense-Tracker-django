from decimal import Decimal

from rest_framework import serializers

from .models import Category, Expense


class ExpenseSerializer(serializers.ModelSerializer):
    """Validates expense input and shapes expense output."""

    # `user_id` is part of the API contract. read_only: clients can never set the owner;
    # the view fills it from request.user.
    user_id = serializers.IntegerField(read_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    # A plain CharField (not ChoiceField) because the old API accepted any letter case
    # ("groceries" -> "Groceries"); validate_category normalises it and checks it.
    category = serializers.CharField(max_length=50)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Expense
        fields = ("id", "user_id", "amount", "category", "description", "date")

    def validate_category(self, value):
        value = value.strip().title()
        if value not in Category.values:
            raise serializers.ValidationError(
                f"Invalid category. Allowed categories are: {', '.join(Category.values)}"
            )
        return value

    def validate_description(self, value):
        return value or ""  # store "" instead of NULL
