from datetime import date
from decimal import Decimal

import pytest

from apps.budgets.services import budget_status, get_budget_alerts

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "spent, limit, expected_percentage, expected_status",
    [
        ("0", "100", "0.00", "ok"),
        ("79.99", "100", "79.99", "ok"),
        ("80", "100", "80.00", "warning"),  # threshold is inclusive
        ("100", "100", "100.00", "warning"),  # exactly the limit is not "exceeded"
        ("100.01", "100", "100.01", "exceeded"),
        ("250", "100", "250.00", "exceeded"),
        ("1", "3", "33.33", "ok"),  # rounded to 2 decimals
    ],
)
def test_budget_status_boundaries(spent, limit, expected_percentage, expected_status):
    percentage, status = budget_status(Decimal(spent), Decimal(limit))
    assert (str(percentage), status) == (expected_percentage, expected_status)


def test_no_budgets_means_no_alerts(user, make_expense):
    make_expense(user, amount="500")
    assert get_budget_alerts(user, 5, 2026) == []


def test_alert_values(user, make_budget, make_expense):
    make_budget(user, "Groceries", amount="200")
    make_expense(user, amount="100", category="Groceries")
    make_expense(user, amount="70.50", category="Groceries")
    [alert] = get_budget_alerts(user, 5, 2026)
    assert alert == {
        "category": "Groceries",
        "budget_limit": Decimal("200"),
        "spent": Decimal("170.50"),
        "remaining": Decimal("29.50"),
        "percentage_used": Decimal("85.25"),
        "status": "warning",
    }


def test_budget_without_spending_is_ok(user, make_budget):
    make_budget(user, "Health", amount="50")
    [alert] = get_budget_alerts(user, 5, 2026)
    assert (alert["spent"], alert["remaining"], alert["status"]) == (0, Decimal("50"), "ok")


def test_only_matching_month_user_and_category_count(user, other_user, make_budget, make_expense):
    make_budget(user, "Groceries", amount="100")
    make_expense(user, amount="30", category="Groceries", date=date(2026, 5, 31))  # counts
    make_expense(user, amount="999", category="Groceries", date=date(2026, 6, 1))  # other month
    make_expense(user, amount="999", category="Groceries", date=date(2025, 5, 15))  # other year
    make_expense(user, amount="999", category="Health", date=date(2026, 5, 15))  # other category
    make_expense(other_user, amount="999", category="Groceries", date=date(2026, 5, 15))  # other user
    [alert] = get_budget_alerts(user, 5, 2026)
    assert alert["spent"] == Decimal("30")


def test_always_two_queries_regardless_of_budget_count(
    user, make_budget, make_expense, django_assert_num_queries
):
    for category in ["Groceries", "Leisure", "Electronics", "Utilities", "Clothing", "Health", "Others"]:
        make_budget(user, category)
        make_expense(user, category=category)
    with django_assert_num_queries(2):
        assert len(get_budget_alerts(user, 5, 2026)) == 7
