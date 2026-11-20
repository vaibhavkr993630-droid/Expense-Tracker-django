from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import ErrorSerializer
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

    @extend_schema(
        tags=["Analytics"],
        summary="Monthly spending summary",
        description="Total, count and average for one month. All zeros when there are no expenses. Cached.",
        parameters=[RequiredPeriodQuerySerializer],
        responses={200: MonthlySummarySerializer, 400: ErrorSerializer, 401: ErrorSerializer},
    )
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

    @extend_schema(
        tags=["Analytics"],
        summary="Spending by category",
        description=(
            "Totals, counts and percentage share per category. `month`/`year` are optional filters. Cached."
        ),
        parameters=[PeriodQuerySerializer],
        responses={200: CategoryBreakdownSerializer, 400: ErrorSerializer, 401: ErrorSerializer},
    )
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

    @extend_schema(
        tags=["Analytics"],
        summary="Spending per month (trend)",
        description=(
            "Totals per calendar month for the last N months, oldest first. Empty months are omitted."
        ),
        parameters=[TrendQuerySerializer],
        responses={200: TrendSerializer, 400: ErrorSerializer, 401: ErrorSerializer},
    )
    def get(self, request):
        query = TrendQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        months = query.validated_data["months"]
        data = get_cached(
            request.user, "trend", {"months": months},
            lambda: monthly_trend(request.user, months),
        )  # fmt: skip
        return Response(TrendSerializer(data).data)
