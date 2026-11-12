from datetime import date
from decimal import Decimal

import pytest

from apps.analytics.services import category_breakdown, monthly_summary, monthly_trend

pytestmark = pytest.mark.django_db


class TestMonthlySummary:
    def test_empty_month_is_all_zeros(self, user):
        assert monthly_summary(user, 5, 2026) == {
            "year": 2026,
            "month": 5,
            "total_expenses": Decimal("0.00"),
            "expense_count": 0,
            "average_expense": Decimal("0.00"),
        }

    def test_totals_count_and_average(self, user, make_expense):
        make_expense(user, amount="10.00")
        make_expense(user, amount="20.00")
        make_expense(user, amount="30.50")
        result = monthly_summary(user, 5, 2026)
        assert result["total_expenses"] == Decimal("60.50")
        assert result["expense_count"] == 3
        assert result["average_expense"] == Decimal("20.17")  # 60.50 / 3 rounded to 2 places

    def test_only_this_user_and_this_month(self, user, other_user, make_expense):
        make_expense(user, amount="10", date=date(2026, 5, 1))
        make_expense(user, amount="10", date=date(2026, 5, 31))
        make_expense(user, amount="500", date=date(2026, 6, 1))
        make_expense(user, amount="500", date=date(2025, 5, 15))
        make_expense(other_user, amount="500", date=date(2026, 5, 15))
        result = monthly_summary(user, 5, 2026)
        assert (result["total_expenses"], result["expense_count"]) == (Decimal("20.00"), 2)

    def test_one_query(self, user, make_expense, django_assert_num_queries):
        for _ in range(5):
            make_expense(user)
        with django_assert_num_queries(1):
            monthly_summary(user, 5, 2026)


class TestCategoryBreakdown:
    def test_empty(self, user):
        assert category_breakdown(user) == {"grand_total": Decimal("0.00"), "categories": []}

    def test_groups_orders_and_percentages(self, user, make_expense):
        make_expense(user, amount="50", category="Groceries")
        make_expense(user, amount="25", category="Groceries")
        make_expense(user, amount="25", category="Health")
        result = category_breakdown(user)
        assert result["grand_total"] == Decimal("100.00")
        assert result["categories"] == [
            {"category": "Groceries", "total": Decimal("75.00"), "count": 2, "percentage": Decimal("75.00")},
            {"category": "Health", "total": Decimal("25.00"), "count": 1, "percentage": Decimal("25.00")},
        ]

    def test_percentages_are_rounded(self, user, make_expense):
        for category in ["Groceries", "Health", "Leisure"]:
            make_expense(user, amount="10", category=category)
        percentages = [c["percentage"] for c in category_breakdown(user)["categories"]]
        assert percentages == [Decimal("33.33")] * 3

    def test_equal_totals_are_ordered_by_category_name(self, user, make_expense):
        make_expense(user, amount="10", category="Leisure")
        make_expense(user, amount="10", category="Groceries")
        assert [c["category"] for c in category_breakdown(user)["categories"]] == ["Groceries", "Leisure"]

    def test_month_and_year_filters_are_independent_and_optional(self, user, make_expense):
        make_expense(user, amount="1", date=date(2026, 5, 1))
        make_expense(user, amount="10", date=date(2025, 5, 1))
        make_expense(user, amount="100", date=date(2026, 6, 1))
        assert category_breakdown(user)["grand_total"] == Decimal("111.00")
        assert category_breakdown(user, month=5)["grand_total"] == Decimal("11.00")  # May of any year
        assert category_breakdown(user, year=2026)["grand_total"] == Decimal("101.00")
        assert category_breakdown(user, month=5, year=2026)["grand_total"] == Decimal("1.00")

    def test_other_users_are_excluded(self, user, other_user, make_expense):
        make_expense(other_user, amount="999")
        assert category_breakdown(user)["categories"] == []

    def test_one_query_for_many_categories(self, user, make_expense, django_assert_num_queries):
        for category in ["Groceries", "Leisure", "Electronics", "Utilities", "Clothing", "Health", "Others"]:
            make_expense(user, category=category)
        with django_assert_num_queries(1):
            assert len(category_breakdown(user)["categories"]) == 7


class TestMonthlyTrend:
    def test_groups_by_month_oldest_first_across_year_boundary(self, user, make_expense):
        make_expense(user, amount="10", date=date(2025, 12, 5))
        make_expense(user, amount="5", date=date(2025, 12, 28))
        make_expense(user, amount="20", date=date(2026, 2, 1))
        result = monthly_trend(user, months=3, today=date(2026, 2, 15))
        assert result["months"] == [
            {"year": 2025, "month": 12, "total_expenses": Decimal("15.00"), "expense_count": 2},
            {"year": 2026, "month": 2, "total_expenses": Decimal("20.00"), "expense_count": 1},
        ]  # January had no expenses, so it is simply absent

    def test_window_start_is_the_first_day_of_the_oldest_month(self, user, make_expense):
        make_expense(user, amount="1", date=date(2025, 11, 30))  # just outside a 3-month window
        make_expense(user, amount="2", date=date(2025, 12, 1))  # first day inside
        months = monthly_trend(user, months=3, today=date(2026, 2, 15))["months"]
        assert [(m["year"], m["month"]) for m in months] == [(2025, 12)]

    def test_only_this_user(self, user, other_user, make_expense):
        make_expense(other_user, date=date(2026, 2, 1))
        assert monthly_trend(user, months=6, today=date(2026, 2, 15))["months"] == []

    def test_one_query(self, user, make_expense, django_assert_num_queries):
        make_expense(user, date=date(2026, 2, 1))
        with django_assert_num_queries(1):
            monthly_trend(user, months=6, today=date(2026, 2, 15))
