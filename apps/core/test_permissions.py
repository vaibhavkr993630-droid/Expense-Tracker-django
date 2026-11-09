import pytest
from rest_framework.test import APIRequestFactory

from apps.core.permissions import IsOwner

pytestmark = pytest.mark.django_db


def test_is_owner_allows_only_the_owner(user, other_user, make_expense):
    expense = make_expense(user)
    request = APIRequestFactory().get("/")
    request.user = user
    assert IsOwner().has_object_permission(request, None, expense) is True
    request.user = other_user
    assert IsOwner().has_object_permission(request, None, expense) is False
