from django.contrib import admin

from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "amount", "month", "year", "last_alert_status")
    list_filter = ("category", "year", "month", "last_alert_status")
    search_fields = ("user__email", "user__username")
    list_select_related = ("user",)  # avoid one query per row for the user column
    raw_id_fields = ("user",)
    ordering = ("-year", "-month", "category")
    list_per_page = 25
