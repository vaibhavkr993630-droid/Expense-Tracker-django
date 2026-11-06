from urllib.parse import urlencode

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


def post_login(client, username, password):
    """POST /login the way the React app does: application/x-www-form-urlencoded."""
    return client.post(
        "/login",
        urlencode({"username": username, "password": password}),
        content_type="application/x-www-form-urlencoded",
    )


SIGNUP = {
    "username": "carol",
    "email": "carol@example.com",
    "password": "StrongPass123",
    "confirm_password": "StrongPass123",
}


class TestSignup:
    def test_signup_creates_user(self, api_client):
        response = api_client.post("/signup", SIGNUP, format="json")
        assert response.status_code == 201
        assert response.json()["detail"] == "User 'carol' successfully registered"
        user = User.objects.get(username="carol")
        assert response.json()["id"] == user.id
        assert user.check_password("StrongPass123")  # stored hashed

    def test_duplicate_email_is_rejected_case_insensitively(self, api_client, user):
        payload = {**SIGNUP, "email": "ALICE@example.com"}
        response = api_client.post("/signup", payload, format="json")
        assert response.status_code == 400
        assert response.json()["detail"] == "Email already registered."

    def test_duplicate_username_is_rejected(self, api_client, user):
        response = api_client.post("/signup", {**SIGNUP, "username": "alice"}, format="json")
        assert response.status_code == 400
        assert response.json()["detail"] == "Username already taken."

    def test_passwords_must_match(self, api_client):
        response = api_client.post("/signup", {**SIGNUP, "confirm_password": "different123"}, format="json")
        assert response.status_code == 400
        assert response.json()["detail"] == "Passwords do not match."

    @pytest.mark.parametrize(
        "changes",
        [
            {"username": "ab"},  # too short
            {"username": "bad name!"},  # illegal characters
            {"email": "not-an-email"},
            {"password": "short", "confirm_password": "short"},
            {"password": "12345678", "confirm_password": "12345678"},  # Django: entirely numeric
        ],
    )
    def test_invalid_payloads_return_400_with_detail_string(self, api_client, changes):
        response = api_client.post("/signup", {**SIGNUP, **changes}, format="json")
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str) and response.json()["detail"]
        assert not User.objects.filter(username="carol").exists()

    def test_signup_is_rate_limited(self, api_client):
        statuses = [api_client.post("/signup", {}, format="json").status_code for _ in range(6)]
        assert statuses[:5] == [400] * 5  # invalid payloads, but not yet throttled
        assert statuses[5] == 429  # 6th request within a minute


class TestLogin:
    def test_login_with_username_form_encoded(self, api_client, user):
        # This is exactly what the React app sends.
        response = post_login(api_client, "alice", "StrongPass123")
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    def test_login_with_email(self, api_client, user):
        response = post_login(api_client, "Alice@Example.com", "StrongPass123")
        assert response.status_code == 200

    def test_login_with_json_body(self, api_client, user):
        response = api_client.post(
            "/login", {"username": "alice", "password": "StrongPass123"}, format="json"
        )
        assert response.status_code == 200

    def test_wrong_password_returns_401(self, api_client, user):
        response = post_login(api_client, "alice", "nope-nope-nope")
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid credentials."}

    def test_unknown_user_returns_401(self, api_client):
        response = post_login(api_client, "ghost", "StrongPass123")
        assert response.status_code == 401

    def test_inactive_user_cannot_login(self, api_client, user):
        user.is_active = False
        user.save()
        response = post_login(api_client, "alice", "StrongPass123")
        assert response.status_code == 401

    def test_missing_fields_return_400(self, api_client):
        response = api_client.post(
            "/login", urlencode({"username": "alice"}), content_type="application/x-www-form-urlencoded"
        )
        assert response.status_code == 400

    def test_login_is_rate_limited(self, api_client, user):
        statuses = [post_login(api_client, "alice", "wrong-password").status_code for _ in range(11)]
        assert statuses[:10] == [401] * 10
        assert statuses[10] == 429


class TestTokenUsage:
    def test_token_from_login_authenticates_requests(self, api_client, user):
        token = post_login(api_client, "alice", "StrongPass123").json()["access_token"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = api_client.get("/users/me")
        assert response.status_code == 200
        assert response.json()["username"] == "alice"

    def test_no_token_returns_401_not_403(self, api_client):
        # The frontend logs the user out on 401, so this must not be 403.
        assert api_client.get("/users/me").status_code == 401

    def test_garbage_token_returns_401(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer not.a.token")
        assert api_client.get("/users/me").status_code == 401

    def test_expired_token_returns_401(self, api_client, user):
        from datetime import timedelta

        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(user)
        token.set_exp(lifetime=-timedelta(minutes=1))  # already expired
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        assert api_client.get("/users/me").status_code == 401
