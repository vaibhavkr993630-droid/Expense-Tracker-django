from django.urls import path

from . import views

urlpatterns = [
    path("signup", views.SignupView.as_view(), name="signup"),
    path("login", views.LoginView.as_view(), name="login"),
    path("users/me", views.ProfileView.as_view(), name="user-me"),
    path("users/change-password", views.ChangePasswordView.as_view(), name="change-password"),
    # Legacy URL kept from the FastAPI API (PUT = rename, DELETE = delete account).
    path("user", views.ProfileView.as_view(), name="user-legacy"),
]
