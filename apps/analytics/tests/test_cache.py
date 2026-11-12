import pytest
from django.core.cache import cache

from apps.analytics.cache import invalidate_user_analytics

pytestmark = pytest.mark.django_db

MONTHLY = "/expenses/summary/monthly?month=5&year=2026"
CATEGORY = "/expenses/summary/category"


def test_second_identical_request_is_served_from_cache(
    auth_client, user, make_expense, django_assert_num_queries
):
    make_expense(user, amount="10")
    first = auth_client.get(MONTHLY).json()
    with django_assert_num_queries(0):  # no database access at all
        second = auth_client.get(MONTHLY).json()
    assert first == second


def test_different_parameters_are_cached_separately(auth_client, user, make_expense):
    make_expense(user, amount="10")
    assert auth_client.get("/expenses/summary/monthly?month=5&year=2026").json()["expense_count"] == 1
    assert auth_client.get("/expenses/summary/monthly?month=6&year=2026").json()["expense_count"] == 0


def test_creating_an_expense_through_the_api_invalidates(auth_client):
    assert auth_client.get(MONTHLY).json()["total_expenses"] == 0  # cached as empty
    auth_client.post("/expenses", {"amount": "42", "category": "Health", "date": "2026-05-10"}, format="json")
    assert auth_client.get(MONTHLY).json()["total_expenses"] == 42.0
    assert auth_client.get(CATEGORY).json()["grand_total"] == 42.0


def test_updating_an_expense_invalidates(auth_client, user, make_expense):
    expense = make_expense(user, amount="10")
    assert auth_client.get(MONTHLY).json()["total_expenses"] == 10.0
    auth_client.put(f"/expenses/{expense.id}", {"amount": "99"}, format="json")
    assert auth_client.get(MONTHLY).json()["total_expenses"] == 99.0


def test_deleting_an_expense_invalidates(auth_client, user, make_expense):
    expense = make_expense(user, amount="10")
    assert auth_client.get(MONTHLY).json()["expense_count"] == 1
    auth_client.delete(f"/expenses/{expense.id}")
    assert auth_client.get(MONTHLY).json()["expense_count"] == 0


def test_another_users_change_does_not_invalidate_my_cache(
    auth_client, user, other_user, make_expense, django_assert_num_queries
):
    make_expense(user, amount="10")
    auth_client.get(MONTHLY)  # warm the cache
    make_expense(other_user, amount="500")  # a different user's expense
    with django_assert_num_queries(0):  # still served from cache
        assert auth_client.get(MONTHLY).json()["total_expenses"] == 10.0


def test_users_never_share_cache_entries(api_client, user, other_user, make_expense):
    make_expense(user, amount="10")
    make_expense(other_user, amount="70")
    api_client.force_authenticate(user=user)
    assert api_client.get(MONTHLY).json()["total_expenses"] == 10.0
    api_client.force_authenticate(user=other_user)
    assert api_client.get(MONTHLY).json()["total_expenses"] == 70.0


def test_cascade_deleting_a_users_expenses_also_invalidates(user, make_expense):
    make_expense(user)
    version_key = f"analytics:version:{user.id}"
    invalidate_user_analytics(user.id)
    before = cache.get(version_key)
    user.delete()  # cascade-deletes the expense, which fires post_delete
    assert cache.get(version_key) != before


def test_invalidate_creates_a_new_version(user):
    invalidate_user_analytics(user.id)
    first = cache.get(f"analytics:version:{user.id}")
    invalidate_user_analytics(user.id)
    assert cache.get(f"analytics:version:{user.id}") != first
