from datetime import timedelta

import django_filters
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Category, Expense

# Predefined periods of the old API: name -> number of days back from today.
PERIOD_DAYS = {"week": 7, "month": 30, "3months": 90}


class ExpenseFilter(django_filters.FilterSet):
    """
    Query-string filters for GET /expenses (and later the exports).

    django-filter turns declared filters into validated query parameters and applies them
    to the queryset. Here `filter_queryset` is overridden because `period` and the date range
    interact (a period overrides from_date/to_date, as in the old API).
    """

    from_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    to_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    period = django_filters.CharFilter(method="filter_noop")
    category = django_filters.ChoiceFilter(choices=Category.choices)

    class Meta:
        model = Expense
        fields = ["from_date", "to_date", "period", "category"]

    def filter_noop(self, queryset, name, value):
        return queryset  # `period` is handled together with the dates in filter_queryset

    def filter_queryset(self, queryset):
        data = self.form.cleaned_data
        from_date, to_date, period = data.get("from_date"), data.get("to_date"), data.get("period")

        if from_date and to_date and from_date > to_date:
            raise ValidationError({"detail": "'from_date' cannot be later than 'to_date'."})

        if period:
            days = PERIOD_DAYS.get(period.lower())
            if days is None:
                raise ValidationError(
                    {"detail": "Invalid 'period' value. Accepted values are 'week', 'month', '3months'."}
                )
            to_date = timezone.localdate()
            from_date = to_date - timedelta(days=days)

        if data.get("category"):
            queryset = queryset.filter(category=data["category"])
        return queryset.in_date_range(from_date, to_date)
