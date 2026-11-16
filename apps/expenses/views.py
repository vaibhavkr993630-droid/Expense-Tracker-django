from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.utils import timezone
from django_filters.utils import translate_validation
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import ModelViewSet

from apps.budgets.notifications import notify_budget_alerts
from apps.core.permissions import IsOwner

from . import exports
from .filters import ExpenseFilter
from .models import Expense
from .pagination import ExpensePagination
from .serializers import ExpenseSerializer

NOT_FOUND_MESSAGES = {
    "update": "The expense doesn't exist.",
    "partial_update": "The expense doesn't exist.",
    "destroy": "The expense doesn't exist or you don't have permission to delete it.",
}


class ExpenseViewSet(ModelViewSet):
    """
    CRUD for the logged-in user's expenses.

    A ModelViewSet bundles list / create / retrieve / update / destroy in one class; the router
    in urls.py turns it into URLs. Everything is scoped to request.user.
    """

    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    pagination_class = ExpensePagination
    filterset_class = ExpenseFilter  # applied by the DjangoFilterBackend set in settings
    # Must exist on the class so @action(throttle_scope=...) below may override it per action.
    throttle_scope = None

    def get_queryset(self):
        # The most important line for data isolation: other users' rows are never even queried.
        return Expense.objects.for_user(self.request.user)

    def get_object(self):
        try:
            return super().get_object()  # also runs IsOwner.has_object_permission
        except Http404:
            raise NotFound(NOT_FOUND_MESSAGES.get(self.action, "Not found.")) from None

    # After every change we re-check the user's budgets for the affected month(s).
    # perform_create / perform_update / perform_destroy are the hooks DRF calls to do the actual save.
    def perform_create(self, serializer):
        expense = serializer.save(user=self.request.user)  # the owner always comes from the token
        notify_budget_alerts(self.request.user, expense.date.month, expense.date.year)

    def perform_update(self, serializer):
        old_period = (serializer.instance.date.month, serializer.instance.date.year)
        expense = serializer.save()
        # If the date moved to another month, both months' spending changed.
        for month, year in {old_period, (expense.date.month, expense.date.year)}:
            notify_budget_alerts(self.request.user, month, year)

    def perform_destroy(self, instance):
        month, year = instance.date.month, instance.date.year
        instance.delete()
        # Less spending can bring a budget back to "ok", which resets its alert level.
        notify_budget_alerts(self.request.user, month, year)

    # The responses below keep the old API's shapes (the React app depends on them).
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        expense = serializer.instance
        return Response(
            {"message": f"Expense ${expense.amount} added.", "id": expense.id},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True  # PUT only changes the fields that were sent, like before
        super().update(request, *args, **kwargs)
        return Response({"message": f"Expense with ID {kwargs['pk']} successfully updated."})

    # --- Exports -----------------------------------------------------------------------------
    # `@action(detail=False)` adds extra routes to the viewset: /expenses/export/csv and /pdf.
    # They accept the same filters as the list endpoint but are not paginated. The router
    # matches these before /expenses/{id}.

    def _filtered_for_export(self, request):
        """The user's expenses after applying the query-string filters, plus the effective date range."""
        filterset = ExpenseFilter(request.query_params, queryset=self.get_queryset(), request=request)
        if not filterset.is_valid():
            raise translate_validation(filterset.errors)
        return filterset.qs, filterset.date_range()

    @staticmethod
    def _filename(extension):
        return f"expenses_{timezone.localdate():%Y%m%d}.{extension}"

    @action(
        detail=False,
        methods=["get"],
        url_path="export/csv",
        pagination_class=None,
        throttle_classes=[ScopedRateThrottle],
        throttle_scope="export",
    )
    def export_csv(self, request):
        expenses, _ = self._filtered_for_export(request)
        response = StreamingHttpResponse(exports.iter_csv(expenses), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{self._filename("csv")}"'
        return response

    @action(
        detail=False,
        methods=["get"],
        url_path="export/pdf",
        pagination_class=None,
        throttle_classes=[ScopedRateThrottle],
        throttle_scope="export",
    )
    def export_pdf(self, request):
        queryset, (from_date, to_date) = self._filtered_for_export(request)
        expenses = list(queryset[: exports.PDF_MAX_ROWS + 1])
        if len(expenses) > exports.PDF_MAX_ROWS:
            message = (
                f"Too many expenses for a PDF (over {exports.PDF_MAX_ROWS}). Narrow the range or use CSV."
            )
            raise ValidationError({"detail": message})
        pdf_bytes = exports.build_expenses_pdf(
            expenses, request.user.username, from_date, to_date, generated_at=timezone.localtime()
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{self._filename("pdf")}"'
        return response
