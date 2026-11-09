from datetime import timedelta

import pytest
from django.utils import timezone

from apps.expenses.models import Expense

pytestmark = pytest.mark.django_db

NEW = {"amount": "12.50", "category": "Groceries", "description": "Milk", "date": "2026-05-15"}


class TestAuthRequired:
    @pytest.mark.parametrize(
        "method, url",
        [("get", "/expenses"), ("post", "/expenses"), ("put", "/expenses/1"), ("delete", "/expenses/1")],
    )
    def test_401_without_token(self, api_client, method, url):
        assert getattr(api_client, method)(url).status_code == 401


class TestCreate:
    def test_create_returns_message_and_id(self, auth_client, user):
        response = auth_client.post("/expenses", NEW, format="json")
        assert response.status_code == 201
        expense = Expense.objects.get()
        assert response.json() == {"message": "Expense $12.50 added.", "id": expense.id}
        assert expense.user == user

    def test_owner_always_comes_from_the_token(self, auth_client, user, other_user):
        auth_client.post("/expenses", {**NEW, "user_id": other_user.id, "user": other_user.id}, format="json")
        assert Expense.objects.get().user == user

    def test_category_is_case_insensitive(self, auth_client):
        auth_client.post("/expenses", {**NEW, "category": "gROCERIES"}, format="json")
        assert Expense.objects.get().category == "Groceries"

    def test_date_defaults_to_today_and_description_is_optional(self, auth_client):
        response = auth_client.post("/expenses", {"amount": 5, "category": "Health"}, format="json")
        assert response.status_code == 201
        expense = Expense.objects.get()
        assert expense.date == timezone.localdate()
        assert expense.description == ""

    def test_null_description_is_stored_as_empty_string(self, auth_client):
        auth_client.post("/expenses", {**NEW, "description": None}, format="json")
        assert Expense.objects.get().description == ""

    @pytest.mark.parametrize(
        "changes",
        [
            {"amount": 0},
            {"amount": -3},
            {"amount": "abc"},
            {"category": "Gambling"},
            {"description": "x" * 201},
            {"date": "not-a-date"},
        ],
    )
    def test_invalid_input_returns_400_with_detail_string(self, auth_client, changes):
        response = auth_client.post("/expenses", {**NEW, **changes}, format="json")
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)
        assert Expense.objects.count() == 0

    def test_invalid_category_message_lists_allowed_values(self, auth_client):
        response = auth_client.post("/expenses", {**NEW, "category": "Gambling"}, format="json")
        assert "Allowed categories are: Groceries, Leisure" in response.json()["detail"]


class TestList:
    def test_response_shape_and_types(self, auth_client, user, make_expense):
        expense = make_expense(user, amount="12.50", category="Health", description="Vitamins")
        body = auth_client.get("/expenses").json()
        assert set(body) == {"expenses", "page", "limit", "total"}
        assert (body["page"], body["limit"], body["total"]) == (1, 10, 1)
        assert body["expenses"][0] == {
            "id": expense.id,
            "user_id": user.id,
            "amount": 12.5,  # a JSON number, not a string
            "category": "Health",
            "description": "Vitamins",
            "date": "2026-05-15",
        }
        assert isinstance(body["expenses"][0]["amount"], float)

    def test_only_own_expenses_are_listed(self, auth_client, user, other_user, make_expense):
        mine = make_expense(user)
        make_expense(other_user)
        body = auth_client.get("/expenses").json()
        assert [e["id"] for e in body["expenses"]] == [mine.id]
        assert body["total"] == 1

    def test_newest_first(self, auth_client, user, make_expense):
        old = make_expense(user, date="2026-01-01")
        new = make_expense(user, date="2026-03-01")
        ids = [e["id"] for e in auth_client.get("/expenses").json()["expenses"]]
        assert ids == [new.id, old.id]

    def test_pagination(self, auth_client, user, make_expense):
        for day in range(1, 26):
            make_expense(user, date=f"2026-05-{day:02d}")
        page2 = auth_client.get("/expenses?page=2&limit=10").json()
        assert (page2["page"], page2["limit"], page2["total"]) == (2, 10, 25)
        assert len(page2["expenses"]) == 10
        last = auth_client.get("/expenses?page=3&limit=10").json()
        assert len(last["expenses"]) == 5

    def test_page_past_the_end_is_empty_not_404(self, auth_client, user, make_expense):
        make_expense(user)
        response = auth_client.get("/expenses?page=9")
        assert response.status_code == 200
        assert response.json()["expenses"] == [] and response.json()["total"] == 1

    def test_limit_is_capped_at_100(self, auth_client):
        assert auth_client.get("/expenses?limit=500").json()["limit"] == 100

    @pytest.mark.parametrize("page", ["0", "-1", "abc"])
    def test_invalid_page_is_400(self, auth_client, page):
        assert auth_client.get(f"/expenses?page={page}").status_code == 400

    def test_list_uses_a_constant_number_of_queries(
        self, auth_client, user, make_expense, django_assert_num_queries
    ):
        for _ in range(15):
            make_expense(user)
        with django_assert_num_queries(2):  # one COUNT + one SELECT, regardless of row count
            auth_client.get("/expenses?limit=10")


class TestFilters:
    @pytest.fixture
    def spread(self, user, make_expense):
        today = timezone.localdate()
        return {
            "today": make_expense(user, date=today),
            "five_days": make_expense(user, date=today - timedelta(days=5)),
            "twenty_days": make_expense(user, date=today - timedelta(days=20)),
            "sixty_days": make_expense(user, date=today - timedelta(days=60)),
            "old": make_expense(user, date=today - timedelta(days=200)),
        }

    def ids(self, client, query):
        return {e["id"] for e in client.get(f"/expenses?{query}").json()["expenses"]}

    @pytest.mark.parametrize(
        "period, expected",
        [
            ("week", {"today", "five_days"}),
            ("month", {"today", "five_days", "twenty_days"}),
            ("3months", {"today", "five_days", "twenty_days", "sixty_days"}),
            ("WEEK", {"today", "five_days"}),
        ],
    )
    def test_period(self, auth_client, spread, period, expected):
        assert self.ids(auth_client, f"period={period}") == {spread[k].id for k in expected}

    def test_from_and_to_date(self, auth_client, make_expense, user):
        a = make_expense(user, date="2026-01-10")
        b = make_expense(user, date="2026-02-10")
        c = make_expense(user, date="2026-03-10")
        assert self.ids(auth_client, "from_date=2026-01-10&to_date=2026-02-10") == {a.id, b.id}
        assert self.ids(auth_client, "from_date=2026-02-01") == {b.id, c.id}
        assert self.ids(auth_client, "to_date=2026-01-31") == {a.id}

    def test_period_overrides_dates(self, auth_client, spread):
        ids = self.ids(auth_client, "period=week&from_date=2000-01-01&to_date=2000-01-02")
        assert ids == {spread["today"].id, spread["five_days"].id}

    def test_category_filter(self, auth_client, user, make_expense):
        food = make_expense(user, category="Groceries")
        make_expense(user, category="Health")
        assert self.ids(auth_client, "category=Groceries") == {food.id}

    def test_filters_never_leak_other_users(self, auth_client, other_user, make_expense):
        make_expense(other_user, date=timezone.localdate())
        assert self.ids(auth_client, "period=week") == set()

    def test_reversed_range_is_400(self, auth_client):
        response = auth_client.get("/expenses?from_date=2026-05-02&to_date=2026-05-01")
        assert response.status_code == 400
        assert response.json()["detail"] == "'from_date' cannot be later than 'to_date'."

    def test_invalid_period_is_400(self, auth_client):
        response = auth_client.get("/expenses?period=decade")
        assert response.status_code == 400
        assert "Invalid 'period' value" in response.json()["detail"]

    def test_bad_date_is_400(self, auth_client):
        assert auth_client.get("/expenses?from_date=yesterday").status_code == 400


class TestUpdateAndDelete:
    def test_put_updates_only_sent_fields(self, auth_client, user, make_expense):
        expense = make_expense(user, amount="10", category="Health", description="Old")
        response = auth_client.put(f"/expenses/{expense.id}", {"amount": "99.99"}, format="json")
        assert response.status_code == 200
        assert response.json() == {"message": f"Expense with ID {expense.id} successfully updated."}
        expense.refresh_from_db()
        assert str(expense.amount) == "99.99"
        assert (expense.category, expense.description) == ("Health", "Old")  # untouched

    def test_put_with_full_form_like_the_frontend(self, auth_client, user, make_expense):
        expense = make_expense(user)
        payload = {"amount": "7", "category": "leisure", "description": "", "date": "2026-06-01"}
        assert auth_client.put(f"/expenses/{expense.id}", payload, format="json").status_code == 200
        expense.refresh_from_db()
        assert (expense.category, str(expense.date)) == ("Leisure", "2026-06-01")

    def test_cannot_change_the_owner(self, auth_client, user, other_user, make_expense):
        expense = make_expense(user)
        auth_client.put(
            f"/expenses/{expense.id}", {"user_id": other_user.id, "user": other_user.id}, format="json"
        )
        expense.refresh_from_db()
        assert expense.user == user

    def test_put_invalid_value(self, auth_client, user, make_expense):
        expense = make_expense(user)
        assert auth_client.put(f"/expenses/{expense.id}", {"amount": -1}, format="json").status_code == 400

    def test_other_users_expense_is_404_for_update(self, auth_client, other_user, make_expense):
        theirs = make_expense(other_user, amount="10")
        response = auth_client.put(f"/expenses/{theirs.id}", {"amount": "1"}, format="json")
        assert response.status_code == 404
        assert response.json() == {"detail": "The expense doesn't exist."}
        theirs.refresh_from_db()
        assert str(theirs.amount) == "10.00"

    def test_delete(self, auth_client, user, make_expense):
        expense = make_expense(user)
        assert auth_client.delete(f"/expenses/{expense.id}").status_code == 204
        assert not Expense.objects.filter(pk=expense.pk).exists()

    def test_other_users_expense_is_404_for_delete(self, auth_client, other_user, make_expense):
        theirs = make_expense(other_user)
        assert auth_client.delete(f"/expenses/{theirs.id}").status_code == 404
        assert Expense.objects.filter(pk=theirs.pk).exists()

    def test_missing_expense_is_404(self, auth_client):
        assert auth_client.delete("/expenses/99999").status_code == 404

    def test_retrieve_own_but_not_others(self, auth_client, user, other_user, make_expense):
        mine, theirs = make_expense(user), make_expense(other_user)
        assert auth_client.get(f"/expenses/{mine.id}").status_code == 200
        assert auth_client.get(f"/expenses/{theirs.id}").status_code == 404
