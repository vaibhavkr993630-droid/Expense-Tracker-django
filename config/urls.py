from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.core.views import health_check

admin.site.site_header = "Expense Tracker administration"
admin.site.site_title = "Expense Tracker admin"
admin.site.index_title = "Manage users, expenses and budgets"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthy", health_check, name="health"),
    # API documentation: the raw OpenAPI schema plus two UIs that render it.
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.expenses.urls")),
    path("", include("apps.budgets.urls")),
    path("", include("apps.analytics.urls")),
]
