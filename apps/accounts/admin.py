from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Reuse Django's UserAdmin (password hashing form etc.) with email-based fields."""

    list_display = ("id", "username", "email", "expense_count", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "username", "password1", "password2")}),
    )

    def get_queryset(self, request):
        # annotate() adds a COUNT to the same query that loads the users, so the "Expenses" column
        # costs no extra queries (counting per user in Python would be N+1).
        return super().get_queryset(request).annotate(_expense_count=Count("expenses"))

    @admin.display(description="Expenses", ordering="_expense_count")  # makes the column sortable
    def expense_count(self, user):
        return user._expense_count
