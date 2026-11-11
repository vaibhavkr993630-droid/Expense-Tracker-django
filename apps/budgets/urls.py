from rest_framework.routers import SimpleRouter

from .views import BudgetViewSet

router = SimpleRouter(trailing_slash=False)
router.register("budgets", BudgetViewSet, basename="budget")

urlpatterns = router.urls
