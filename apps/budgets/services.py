"""
Budget business logic, kept out of views and serializers.

A "service layer" is just plain functions that hold the rules of the app. Both the API
endpoint (GET /budgets/alerts) and, on Day 7, the email command call the same functions,
so the status rules exist in exactly one place and are easy to unit-test.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum

from apps.expenses.models import Expense

from .models import Budget

WARNING_THRESHOLD = Decimal("80")  # percent of the budget at which we start warning
TWO_PLACES = Decimal("0.01")

OK, WARNING, EXCEEDED = "ok", "warning", "exceeded"


def budget_status(spent, limit):
    """
    Return (percentage_used, status) for an amount spent against a limit.

    - exceeded: spent is more than the limit
    - warning:  80% or more of the limit is used (including exactly 100%)
    - ok:       otherwise
    """
    spent, limit = Decimal(spent), Decimal(limit)
    percentage = (
        (spent / limit * 100).quantize(TWO_PLACES, rounding=ROUND_HALF_UP) if limit > 0 else Decimal(0)
    )
    if spent > limit:
        return percentage, EXCEEDED
    if percentage >= WARNING_THRESHOLD:
        return percentage, WARNING
    return percentage, OK


def get_budget_alerts(user, month, year):
    """
    Compare the user's spending with their budgets for one month.

    Always exactly two queries, however many budgets there are:
      1. the budgets for that month
      2. total spending per category for that month (one GROUP BY query)
    A per-budget query inside a loop would be the classic N+1 mistake.
    """
    budgets = list(Budget.objects.for_user(user).for_period(month, year))
    if not budgets:
        return []

    spending_rows = (
        Expense.objects.for_user(user)
        .in_month(month, year)
        .order_by()  # drop the default ordering so GROUP BY only groups by category
        .values("category")
        .annotate(total=Sum("amount"))
    )
    spent_by_category = {row["category"]: row["total"] for row in spending_rows}

    alerts = []
    for budget in budgets:
        spent = spent_by_category.get(budget.category, Decimal("0"))
        percentage, status = budget_status(spent, budget.amount)
        alerts.append(
            {
                "category": budget.category,
                "budget_limit": budget.amount,
                "spent": spent,
                "remaining": budget.amount - spent,
                "percentage_used": percentage,
                "status": status,
            }
        )
    return alerts
