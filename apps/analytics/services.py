"""
Analytics queries. Every function runs exactly ONE database query: the work (sum, count, group by)
is done by the database through the ORM's aggregation API, not by looping over rows in Python.

- aggregate(): collapses all matching rows into a single result      -> Sum / Count / Avg
- values(...).annotate(...): GROUP BY, one result row per group      -> per-category, per-month
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.expenses.models import Expense

TWO_PLACES = Decimal("0.01")


def _round(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def monthly_summary(user, month, year):
    """Total, count and average spending for one month. All zeros when there are no expenses."""
    result = (
        Expense.objects.for_user(user).in_month(month, year).aggregate(total=Sum("amount"), count=Count("id"))
    )
    total = result["total"] or Decimal("0")
    count = result["count"]
    return {
        "year": year,
        "month": month,
        "total_expenses": _round(total),
        "expense_count": count,
        "average_expense": _round(total / count) if count else Decimal("0.00"),
    }


def category_breakdown(user, month=None, year=None):
    """Spending grouped by category with each category's share of the grand total."""
    rows = list(
        Expense.objects.for_user(user)
        .in_period(month, year)
        .order_by()  # remove Meta.ordering so GROUP BY groups by category only
        .values("category")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total", "category")
    )
    grand_total = sum((row["total"] for row in rows), Decimal("0"))
    return {
        "grand_total": _round(grand_total),
        "categories": [
            {
                "category": row["category"],
                "total": _round(row["total"]),
                "count": row["count"],
                "percentage": _round(row["total"] / grand_total * 100) if grand_total else Decimal("0.00"),
            }
            for row in rows
        ],
    }


def monthly_trend(user, months=6, today=None):
    """
    Spending per calendar month for the last `months` months (including the current one).

    TruncMonth rounds every date down to the first day of its month, which lets the database
    GROUP BY month. Months without expenses are simply absent from the result.
    """
    today = today or timezone.localdate()
    first_month_index = today.year * 12 + (today.month - 1) - (months - 1)
    start_year, start_month_zero_based = divmod(first_month_index, 12)
    start = date(start_year, start_month_zero_based + 1, 1)

    rows = (
        Expense.objects.for_user(user)
        .filter(date__gte=start)
        .order_by()
        .annotate(month_start=TruncMonth("date"))
        .values("month_start")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("month_start")
    )
    return {
        "months": [
            {
                "year": row["month_start"].year,
                "month": row["month_start"].month,
                "total_expenses": _round(row["total"]),
                "expense_count": row["count"],
            }
            for row in rows
        ]
    }
