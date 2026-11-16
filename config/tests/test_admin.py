import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.budgets.models import Budget
from apps.expenses.models import Expense

User = get_user_model()
pytestmark = pytest.mark.django_db


def changelist(model):
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")


class TestAccess:
    def test_anonymous_is_redirected_to_login(self, client):
        response = client.get(changelist(Expense))
        assert response.status_code == 302 and "/admin/login/" in response["Location"]

    def test_non_staff_cannot_enter(self, client, user):
        client.force_login(user)
        assert client.get(changelist(Expense)).status_code == 302

    def test_superuser_sees_every_changelist(self, admin_client):
        for model in (User, Expense, Budget):
            assert admin_client.get(changelist(model)).status_code == 200

    def test_branding(self, admin_client):
        assert "Expense Tracker administration" in admin_client.get("/admin/").content.decode()


class TestExpenseAdmin:
    def test_list_search_filter_and_date_hierarchy(self, admin_client, user, other_user, make_expense):
        make_expense(user, category="Groceries", description="Fresh milk", date="2026-05-10")
        make_expense(other_user, category="Health", description="Vitamins", date="2025-01-02")
        url = changelist(Expense)
        assert b"Fresh milk" in admin_client.get(url).content
        by_description = admin_client.get(url, {"q": "vitamins"}).content
        assert b"Vitamins" in by_description and b"Fresh milk" not in by_description
        by_email = admin_client.get(url, {"q": "alice@example.com"}).content
        assert b"Fresh milk" in by_email and b"Vitamins" not in by_email
        by_category = admin_client.get(url, {"category__exact": "Health"}).content
        assert b"Vitamins" in by_category and b"Fresh milk" not in by_category
        by_year = admin_client.get(url, {"date__year": "2026"}).content
        assert b"Fresh milk" in by_year and b"Vitamins" not in by_year

    def test_changelist_query_count_does_not_grow_with_rows(
        self, admin_client, user, other_user, make_expense
    ):
        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                admin_client.get(changelist(Expense))
            return len(queries)

        make_expense(user)
        few = count_queries()
        for index in range(20):
            make_expense(user if index % 2 else other_user)
        assert count_queries() == few  # list_select_related prevents one query per row

    def test_add_page_and_creating_an_expense(self, admin_client, user):
        add_url = reverse("admin:expenses_expense_add")
        assert admin_client.get(add_url).status_code == 200
        response = admin_client.post(
            add_url,
            {
                "user": user.id,
                "amount": "12.50",
                "category": "Health",
                "description": "x",
                "date": "2026-05-10",
            },
        )
        assert response.status_code == 302
        assert Expense.objects.get().user == user

    def test_admin_validation_uses_the_model_rules(self, admin_client, user):
        response = admin_client.post(
            reverse("admin:expenses_expense_add"),
            {"user": user.id, "amount": "12.50", "category": "Gambling", "date": "2026-05-10"},
        )
        assert response.status_code == 200  # form re-displayed with an error
        assert Expense.objects.count() == 0

    def test_export_action_returns_only_the_selected_rows_as_csv(self, admin_client, user, make_expense):
        keep = make_expense(user, description="chosen")
        make_expense(user, description="skipped")
        response = admin_client.post(
            changelist(Expense),
            {"action": "export_selected_as_csv", "_selected_action": [keep.id]},
        )
        body = b"".join(response.streaming_content).decode()
        assert response["Content-Type"] == "text/csv"
        assert "chosen" in body and "skipped" not in body


class TestBudgetAdmin:
    def test_list_filter_and_search(self, admin_client, user, other_user, make_budget):
        groceries = make_budget(user, "Groceries")
        health = make_budget(other_user, "Health")
        url = changelist(Budget)

        def rows(**params):
            # Inspect the rows of the list (not the page text: the filter sidebar names every category).
            return list(admin_client.get(url, params).context["cl"].result_list)

        assert set(rows()) == {groceries, health}
        assert rows(q="bob@example.com") == [health]
        assert rows(category__exact="Groceries") == [groceries]

    def test_changelist_query_count_is_constant(self, admin_client, user, other_user, make_budget):
        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                admin_client.get(changelist(Budget))
            return len(queries)

        make_budget(user, "Groceries")
        few = count_queries()
        for category in ["Health", "Leisure", "Others", "Clothing"]:
            make_budget(other_user, category)
        assert count_queries() == few


class TestUserAdmin:
    def test_shows_expense_counts_without_extra_queries(self, admin_client, user, other_user, make_expense):
        make_expense(user)
        make_expense(user)

        def count_queries():
            with CaptureQueriesContext(connection) as queries:
                response = admin_client.get(changelist(User))
            return len(queries), response

        few, response = count_queries()
        assert response.status_code == 200
        for index in range(5):
            User.objects.create_user(
                email=f"extra{index}@example.com", username=f"extra{index}", password="x" * 12
            )
        assert count_queries()[0] == few

    def test_search_by_email(self, admin_client, user, other_user):
        content = admin_client.get(changelist(User), {"q": "bob@"}).content
        assert b"bob@example.com" in content and b"alice@example.com" not in content

    def test_can_create_a_user_with_a_hashed_password(self, admin_client):
        response = admin_client.post(
            reverse("admin:accounts_user_add"),
            {
                "email": "new@example.com",
                "username": "newbie",
                "password1": "ComplexPass987",
                "password2": "ComplexPass987",
            },
        )
        assert response.status_code == 302
        created = User.objects.get(email="new@example.com")
        assert created.password != "ComplexPass987" and created.check_password("ComplexPass987")
