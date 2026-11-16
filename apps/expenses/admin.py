from django.contrib import admin
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.text import Truncator

from . import exports
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    # Columns of the list page.
    list_display = ("id", "date", "user", "category", "amount", "short_description")
    # Sidebar filters.
    list_filter = ("category", "date")
    # The search box looks in these fields; "user__email" follows the foreign key.
    search_fields = ("description", "user__email", "user__username")
    # Year > month > day drill-down links above the list.
    date_hierarchy = "date"
    # Without this the list runs one extra query per row to fetch each expense's user (N+1).
    # select_related makes it a single JOIN.
    list_select_related = ("user",)
    # A plain text box with the user's id instead of a dropdown listing every user.
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 25
    actions = ["export_selected_as_csv"]

    @admin.display(description="Description")
    def short_description(self, expense):
        return Truncator(expense.description).chars(40)

    @admin.action(description="Export selected expenses as CSV")
    def export_selected_as_csv(self, request, queryset):
        # Reuses the same streaming CSV builder as the API export.
        response = StreamingHttpResponse(exports.iter_csv(queryset), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="expenses_{timezone.localdate():%Y%m%d}.csv"'
        return response
