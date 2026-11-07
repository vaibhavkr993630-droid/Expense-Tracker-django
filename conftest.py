"""Shared pytest fixtures, available to every test in the project."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def fast_password_hasher(settings):
    """Django's default hasher is deliberately slow (good for security, bad for 40+ tests)."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def clear_cache():
    """Throttle counters live in the cache; reset them so tests cannot affect each other."""
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="alice@example.com", username="alice", password="StrongPass123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="bob@example.com", username="bob", password="StrongPass123")


@pytest.fixture
def auth_client(api_client, user):
    """An API client already logged in as `user` (force_authenticate skips the token step)."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def make_expense(db):
    """Factory fixture: make_expense(user, amount=10, category="Groceries", date=...)."""
    from datetime import date as date_cls
    from decimal import Decimal

    from apps.expenses.models import Expense

    def _make(user, amount="10.00", category="Groceries", description="", date=None):
        return Expense.objects.create(
            user=user,
            amount=Decimal(str(amount)),
            category=category,
            description=description,
            date=date or date_cls(2026, 5, 15),
        )

    return _make
