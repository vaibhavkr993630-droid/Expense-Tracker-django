from datetime import date

import pytest
from django.utils import timezone

from apps.budgets.models import Budget

pytestmark = pytest.mark.django_db

NEW = {"category": "Groceries", "amount": 300, "month": 5, "year": 2026}


class TestAuthRequired:
    @pytest.mark.parametrize(
        "method, url",
        [("get", "/budgets"), ("post", "/budgets"), ("delete", "/budgets/1"), ("get", "/budgets/alerts")],
    )
    def test_401_without_token(self, api_client, method, url):
        assert getattr(api_client, method)(url).status_code == 401


class TestSetBudget:
    def test_create_returns_201_and_the_budget(self, auth_client, user):
        response = auth_client.post("/budgets", NEW, format="json")
        assert response.status_code == 201
        budget = Budget.objects.get()
        assert response.json() == {
            "id": budget.id,
            "category": "Groceries",
            "amount": 300.0,
            "month": 5,
            "year": 2026,
        }
        assert budget.user == user

    def test_posting_again_updates_instead_of_duplicating(self, auth_client):
        first = auth_client.post("/budgets", NEW, format="json").json()
        second = auth_client.post("/budgets", {**NEW, "amount": 450.5}, format="json")
        assert second.status_code == 201  # the old API returned 201 for updates too
        assert second.json()["id"] == first["id"]
        assert second.json()["amount"] == 450.5
        assert Budget.objects.count() == 1

    def test_category_is_case_insensitive_so_it_still_upserts(self, auth_client):
        auth_client.post("/budgets", NEW, format="json")
        auth_client.post("/budgets", {**NEW, "category": "GROCERIES", "amount": 10}, format="json")
        assert Budget.objects.count() == 1

    def test_same_category_in_another_month_is_a_new_budget(self, auth_client):
        auth_client.post("/budgets", NEW, format="json")
        auth_client.post("/budgets", {**NEW, "month": 6}, format="json")
        assert Budget.objects.count() == 2

    def test_other_users_budget_is_never_touched(self, auth_client, other_user, make_budget):
        theirs = make_budget(other_user, "Groceries", amount="100", month=5, year=2026)
        auth_client.post("/budgets", {**NEW, "amount": 999}, format="json")
        theirs.refresh_from_db()
        assert theirs.amount == 100
        assert Budget.objects.count() == 2

    @pytest.mark.parametrize(
        "changes",
        [
            {"amount": 0},
            {"amount": -5},
            {"month": 0},
            {"month": 13},
            {"year": 1999},
            {"year": 2101},
            {"category": "Gambling"},
        ],
    )
    def test_invalid_input_is_400(self, auth_client, changes):
        response = auth_client.post("/budgets", {**NEW, **changes}, format="json")
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)
        assert Budget.objects.count() == 0

    def test_missing_fields_are_400(self, auth_client):
        assert auth_client.post("/budgets", {"category": "Health"}, format="json").status_code == 400


class TestListBudgets:
    def test_returns_a_plain_array_for_the_requested_month(self, auth_client, user, make_budget):
        may = make_budget(user, "Groceries", month=5, year=2026)
        make_budget(user, "Health", month=6, year=2026)
        response = auth_client.get("/budgets?month=5&year=2026")
        assert response.status_code == 200
        assert response.json() == [
            {"id": may.id, "category": "Groceries", "amount": 100.0, "month": 5, "year": 2026}
        ]

    def test_defaults_to_current_month_and_year(self, auth_client, user, make_budget):
        today = timezone.localdate()
        current = make_budget(user, month=today.month, year=today.year)
        make_budget(user, "Health", month=today.month % 12 + 1, year=today.year)
        assert [b["id"] for b in auth_client.get("/budgets").json()] == [current.id]

    def test_only_own_budgets(self, auth_client, other_user, make_budget):
        make_budget(other_user)
        assert auth_client.get("/budgets?month=5&year=2026").json() == []

    @pytest.mark.parametrize("query", ["month=13", "month=0", "month=abc", "year=1999", "year=2101"])
    def test_invalid_period_is_400(self, auth_client, query):
        assert auth_client.get(f"/budgets?{query}").status_code == 400


class TestDeleteBudget:
    def test_delete(self, auth_client, user, make_budget):
        budget = make_budget(user)
        assert auth_client.delete(f"/budgets/{budget.id}").status_code == 204
        assert not Budget.objects.filter(pk=budget.pk).exists()

    def test_other_users_budget_is_404_and_survives(self, auth_client, other_user, make_budget):
        theirs = make_budget(other_user)
        response = auth_client.delete(f"/budgets/{theirs.id}")
        assert response.status_code == 404
        assert response.json() == {"detail": "Budget not found."}
        assert Budget.objects.filter(pk=theirs.pk).exists()

    def test_missing_budget_is_404(self, auth_client):
        assert auth_client.delete("/budgets/99999").status_code == 404


class TestAlertsEndpoint:
    def test_empty_when_no_budgets(self, auth_client):
        response = auth_client.get("/budgets/alerts?month=5&year=2026")
        assert response.status_code == 200
        assert response.json() == {"month": 5, "year": 2026, "alerts": []}

    def test_response_shape_and_statuses(self, auth_client, user, make_budget, make_expense):
        make_budget(user, "Groceries", amount="100")
        make_budget(user, "Health", amount="100")
        make_budget(user, "Leisure", amount="100")
        make_expense(user, amount="50", category="Groceries")  # 50%  -> ok
        make_expense(user, amount="85", category="Health")  # 85%  -> warning
        make_expense(user, amount="120", category="Leisure")  # 120% -> exceeded
        body = auth_client.get("/budgets/alerts?month=5&year=2026").json()
        assert (body["month"], body["year"]) == (5, 2026)
        by_category = {a["category"]: a for a in body["alerts"]}
        assert by_category["Groceries"] == {
            "category": "Groceries",
            "budget_limit": 100.0,
            "spent": 50.0,
            "remaining": 50.0,
            "percentage_used": 50.0,
            "status": "ok",
        }
        assert by_category["Health"]["status"] == "warning"
        assert by_category["Leisure"]["status"] == "exceeded"
        assert by_category["Leisure"]["remaining"] == -20.0

    def test_other_users_spending_is_ignored(self, auth_client, user, other_user, make_budget, make_expense):
        make_budget(user, "Groceries", amount="100")
        make_expense(other_user, amount="500", category="Groceries", date=date(2026, 5, 10))
        [alert] = auth_client.get("/budgets/alerts?month=5&year=2026").json()["alerts"]
        assert alert["spent"] == 0 and alert["status"] == "ok"

    def test_defaults_to_current_month(self, auth_client):
        today = timezone.localdate()
        body = auth_client.get("/budgets/alerts").json()
        assert (body["month"], body["year"]) == (today.month, today.year)

    def test_alerts_route_is_not_swallowed_by_the_detail_route(self, auth_client):
        # "/budgets/alerts" must not be treated as "/budgets/{id}" with id="alerts"
        assert auth_client.get("/budgets/alerts").status_code == 200

    def test_invalid_month_is_400(self, auth_client):
        assert auth_client.get("/budgets/alerts?month=13").status_code == 400
