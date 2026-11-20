from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    tags=["Health"],
    summary="Liveness check",
    auth=[],
    responses=inline_serializer("HealthResponse", {"status": serializers.CharField()}),
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    """Liveness probe used by Docker, load balancers and the frontend proxy."""
    return Response({"status": "Healthy"})
