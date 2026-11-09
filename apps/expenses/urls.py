from rest_framework.routers import SimpleRouter

from .views import ExpenseViewSet

# trailing_slash=False because the React app calls "/expenses", not "/expenses/".
router = SimpleRouter(trailing_slash=False)
router.register("expenses", ExpenseViewSet, basename="expense")

urlpatterns = router.urls
