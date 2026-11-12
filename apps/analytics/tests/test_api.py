from datetime import date

import pytest

pytestmark = pytest.mark.django_db

URLS = [
    "/expenses/summary/monthly?month=5&year=2026",
    "/expenses/summary/category",
    "/expenses/summary/trend",
]


@pytest.mark.parametrize("url", URLS)
def test_requires_authentication(api_client, url):
    assert api_client.get(url).status_code == 401


class TestMonthlySummary:
    def test_response_shape_and_types(self, auth_client, user, make_expense):
        make_expense(user, amount="10")
        make_expense(user, amount="15")
        body = auth_client.get("/expenses/summary/monthly?month=5&year=2026").json()
        assert body == {
            "year": 2026,
            "month": 5,
            "total_expenses": 25.0,
            "expense_count": 2,
            "average_expense": 12.5,
        }

    def test_empty_month_returns_zeros(self, auth_client):
        body = auth_client.get("/expenses/summary/monthly?month=1&year=2020").json()
        assert (body["total_expenses"], body["expense_count"], body["average_expense"]) == (0, 0, 0)

    @pytest.mark.parametrize(
        "query",
        [
            "",
            "month=5",
            "year=2026",
            "month=0&year=2026",
            "month=13&year=2026",
            "month=5&year=1999",
            "month=x&year=2026",
        ],
    )
    def test_month_and_year_are_required_and_validated(self, auth_client, query):
        response = auth_client.get(f"/expenses/summary/monthly?{query}")
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)

    def test_other_users_data_is_not_included(self, auth_client, other_user, make_expense):
        make_expense(other_user, amount="999")
        assert auth_client.get("/expenses/summary/monthly?month=5&year=2026").json()["expense_count"] == 0


class TestCategoryBreakdown:
    def test_response_shape(self, auth_client, user, make_expense):
        make_expense(user, amount="75", category="Groceries")
        make_expense(user, amount="25", category="Health")
        body = auth_client.get("/expenses/summary/category?month=5&year=2026").json()
        assert body == {
            "grand_total": 100.0,
            "categories": [
                {"category": "Groceries", "total": 75.0, "count": 1, "percentage": 75.0},
                {"category": "Health", "total": 25.0, "count": 1, "percentage": 25.0},
            ],
        }

    def test_params_are_optional(self, auth_client, user, make_expense):
        make_expense(user, amount="10", date=date(2024, 1, 1))
        make_expense(user, amount="20", date=date(2026, 5, 1))
        assert auth_client.get("/expenses/summary/category").json()["grand_total"] == 30.0
        assert auth_client.get("/expenses/summary/category?year=2024").json()["grand_total"] == 10.0

    def test_invalid_month_is_400(self, auth_client):
        assert auth_client.get("/expenses/summary/category?month=13").status_code == 400

    def test_empty(self, auth_client):
        assert auth_client.get("/expenses/summary/category").json() == {"grand_total": 0, "categories": []}


class TestTrend:
    def test_default_and_custom_window(self, auth_client, user, make_expense):
        from django.utils import timezone

        make_expense(user, amount="40", date=timezone.localdate())
        body = auth_client.get("/expenses/summary/trend").json()
        assert body["months"][-1]["total_expenses"] == 40.0
        assert auth_client.get("/expenses/summary/trend?months=1").status_code == 200

    @pytest.mark.parametrize("months", ["0", "25", "abc"])
    def test_invalid_months(self, auth_client, months):
        assert auth_client.get(f"/expenses/summary/trend?months={months}").status_code == 400


class TestRoutingDoesNotClashWithExpenseDetailRoute:
    def test_summary_is_not_treated_as_an_expense_id(self, auth_client):
        assert auth_client.get("/expenses/summary/monthly?month=5&year=2026").status_code == 200
        assert auth_client.get("/expenses/99999").status_code == 404  # real detail route still works
