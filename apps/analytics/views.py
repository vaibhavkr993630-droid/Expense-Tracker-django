from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.serializers import PeriodQuerySerializer

from .cache import get_cached
from .serializers import (
    CategoryBreakdownSerializer,
    MonthlySummarySerializer,
    RequiredPeriodQuerySerializer,
    TrendQuerySerializer,
    TrendSerializer,
)
from .services import category_breakdown, monthly_summary, monthly_trend


class MonthlySummaryView(APIView):
    """GET /expenses/summary/monthly?month=&year=  (both required)"""

    def get(self, request):
        query = RequiredPeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        month, year = query.validated_data["month"], query.validated_data["year"]
        data = get_cached(
            request.user, "monthly", {"month": month, "year": year},
            lambda: monthly_summary(request.user, month, year),
        )  # fmt: skip
        return Response(MonthlySummarySerializer(data).data)


class CategoryBreakdownView(APIView):
    """GET /expenses/summary/category?month=&year=  (both optional)"""

    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        month, year = query.validated_data.get("month"), query.validated_data.get("year")
        data = get_cached(
            request.user, "category", {"month": month, "year": year},
            lambda: category_breakdown(request.user, month, year),
        )  # fmt: skip
        return Response(CategoryBreakdownSerializer(data).data)


class MonthlyTrendView(APIView):
    """GET /expenses/summary/trend?months=6  (extra endpoint: totals per month, oldest first)"""

    def get(self, request):
        query = TrendQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        months = query.validated_data["months"]
        data = get_cached(
            request.user, "trend", {"months": months},
            lambda: monthly_trend(request.user, months),
        )  # fmt: skip
        return Response(TrendSerializer(data).data)
