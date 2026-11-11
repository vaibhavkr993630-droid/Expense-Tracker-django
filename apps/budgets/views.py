from django.http import Http404
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.core.permissions import IsOwner
from apps.core.serializers import get_month_and_year

from .models import Budget
from .serializers import BudgetAlertsResponseSerializer, BudgetSerializer
from .services import get_budget_alerts


class BudgetViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    """
    POST /budgets (upsert), GET /budgets, DELETE /budgets/{id}, GET /budgets/alerts.

    Instead of ModelViewSet we mix in only the operations the API has (no retrieve/update), which
    is how DRF lets you expose exactly the endpoints you want.
    """

    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    pagination_class = None  # the frontend expects a plain JSON array

    def get_queryset(self):
        return Budget.objects.for_user(self.request.user)

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound("Budget not found.") from None

    def list(self, request, *args, **kwargs):
        month, year = get_month_and_year(request)  # defaults to the current month and year
        queryset = self.get_queryset().for_period(month, year)
        return Response(self.get_serializer(queryset, many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Upsert: update the amount if this user already has a budget for that category + month,
        # otherwise create it. The unique constraint guarantees there can never be two.
        budget, _created = Budget.objects.update_or_create(
            user=request.user,
            category=data["category"],
            month=data["month"],
            year=data["year"],
            defaults={"amount": data["amount"]},
        )
        # 201 in both cases: that is what the old API (and therefore the frontend) does.
        return Response(self.get_serializer(budget).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="alerts", pagination_class=None)
    def alerts(self, request):
        """GET /budgets/alerts: spending vs budget per category for a month."""
        month, year = get_month_and_year(request)
        alerts = get_budget_alerts(request.user, month, year)
        payload = {"month": month, "year": year, "alerts": alerts}
        return Response(BudgetAlertsResponseSerializer(payload).data)
