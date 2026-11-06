import pytest
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestProfile:
    def test_me_returns_only_own_profile(self, auth_client, user, other_user):
        response = auth_client.get("/users/me")
        assert response.status_code == 200
        assert response.json() == {"id": user.id, "username": "alice", "email": "alice@example.com"}
        assert "password" not in response.json()

    def test_delete_me_deletes_only_the_caller(self, auth_client, user, other_user):
        assert auth_client.delete("/users/me").status_code == 204
        assert not User.objects.filter(pk=user.pk).exists()
        assert User.objects.filter(pk=other_user.pk).exists()

    def test_legacy_delete_user_url(self, auth_client, user):
        assert auth_client.delete("/user").status_code == 204
        assert not User.objects.filter(pk=user.pk).exists()

    def test_requires_authentication(self, api_client):
        assert api_client.delete("/users/me").status_code == 401


class TestUpdateUsername:
    def test_update_username(self, auth_client, user):
        response = auth_client.put("/user", {"username": "alice_new"}, format="json")
        assert response.status_code == 200
        assert response.json() == {"msg": "Username updated successfully.", "username": "alice_new"}
        user.refresh_from_db()
        assert user.username == "alice_new"

    def test_cannot_take_another_users_username(self, auth_client, other_user):
        response = auth_client.put("/user", {"username": "bob"}, format="json")
        assert response.status_code == 400
        assert response.json()["detail"] == "Username already in use."

    def test_can_keep_own_username(self, auth_client):
        assert auth_client.put("/user", {"username": "alice"}, format="json").status_code == 200

    def test_invalid_username_rejected(self, auth_client):
        assert auth_client.put("/user", {"username": "no spaces"}, format="json").status_code == 400


class TestChangePassword:
    def test_change_password(self, auth_client, user):
        response = auth_client.patch(
            "/users/change-password",
            {"current_password": "StrongPass123", "new_password": "BrandNewPass456"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json() == {"msg": "Password updated successfully."}
        user.refresh_from_db()
        assert user.check_password("BrandNewPass456")

    def test_wrong_current_password(self, auth_client, user):
        response = auth_client.patch(
            "/users/change-password",
            {"current_password": "wrong-one", "new_password": "BrandNewPass456"},
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Current password is incorrect."
        user.refresh_from_db()
        assert user.check_password("StrongPass123")  # unchanged

    def test_weak_new_password(self, auth_client):
        response = auth_client.patch(
            "/users/change-password",
            {"current_password": "StrongPass123", "new_password": "short"},
            format="json",
        )
        assert response.status_code == 400

    def test_requires_authentication(self, api_client):
        assert api_client.patch("/users/change-password", {}, format="json").status_code == 401
