import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_create_user_hashes_password_and_lowercases_email():
    user = User.objects.create_user(email="Alice@Example.COM", username="alice", password="secret123")
    assert user.email == "alice@example.com"
    assert user.password != "secret123"  # stored as a hash
    assert user.check_password("secret123")
    assert not user.is_staff and not user.is_superuser


def test_create_superuser_sets_flags():
    admin = User.objects.create_superuser(email="root@example.com", username="root", password="secret123")
    assert admin.is_staff and admin.is_superuser


def test_email_is_the_login_field():
    assert User.USERNAME_FIELD == "email"


def test_email_must_be_unique():
    User.objects.create_user(email="a@example.com", username="a1", password="secret123")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="a@example.com", username="a2", password="secret123")


def test_create_user_without_email_fails():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", username="nomail", password="secret123")


@pytest.mark.parametrize("bad_username", ["ab", "has space", "bad-name!", "x" * 31])
def test_username_validation(bad_username):
    user = User(email="v@example.com", username=bad_username)
    with pytest.raises(ValidationError) as exc:
        user.full_clean(exclude=["password"])
    assert "username" in exc.value.message_dict
