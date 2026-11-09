from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.core.permissions import IsOwner

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

    def get_queryset(self):
        # The most important line for data isolation: other users' rows are never even queried.
        return Expense.objects.for_user(self.request.user)

    def get_object(self):
        try:
            return super().get_object()  # also runs IsOwner.has_object_permission
        except Http404:
            raise NotFound(NOT_FOUND_MESSAGES.get(self.action, "Not found.")) from None

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # the owner always comes from the token

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
