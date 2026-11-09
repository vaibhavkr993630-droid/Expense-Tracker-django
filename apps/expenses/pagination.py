from django.core.paginator import InvalidPage
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ExpensePagination(PageNumberPagination):
    """
    Page-number pagination shaped like the old API:
    GET /expenses?page=2&limit=10  ->  {"expenses": [...], "page": 2, "limit": 10, "total": 37}

    DRF's default response is {"count", "next", "previous", "results"} and uses `page_size`,
    so we rename the query parameter and customise the response. A page past the end returns an
    empty list (not a 404) because the React app can end up there after deleting the last item.
    """

    page_size = 10
    page_size_query_param = "limit"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_page_size(request)
        paginator = self.django_paginator_class(queryset, self.limit)
        self.total = paginator.count

        raw_page = request.query_params.get(self.page_query_param, 1)
        try:
            self.page_number = int(raw_page)
        except (TypeError, ValueError):
            self.page_number = 0
        if self.page_number < 1:
            raise ValidationError({"detail": "'page' must be a whole number starting at 1."})

        try:
            return list(paginator.page(self.page_number))
        except InvalidPage:
            return []

    def get_paginated_response(self, data):
        return Response(
            {"expenses": data, "page": self.page_number, "limit": self.limit, "total": self.total}
        )
