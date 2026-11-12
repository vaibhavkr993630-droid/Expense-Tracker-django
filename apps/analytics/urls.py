from django.urls import path

from . import views

urlpatterns = [
    path("expenses/summary/monthly", views.MonthlySummaryView.as_view(), name="summary-monthly"),
    path("expenses/summary/category", views.CategoryBreakdownView.as_view(), name="summary-category"),
    path("expenses/summary/trend", views.MonthlyTrendView.as_view(), name="summary-trend"),
]
