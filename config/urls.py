from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health_check(request):
    """Liveness probe used by Docker, load balancers and the frontend proxy."""
    return JsonResponse({"status": "Healthy"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthy", health_check, name="health"),
]
