from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.expenses.models import Category


class BudgetQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def for_period(self, month, year):
        return self.filter(month=month, year=year)


class Budget(models.Model):
    """A spending limit for one category in one month of one year, owned by one user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets")
    category = models.CharField(max_length=50, choices=Category.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Small integers + validators: validators run in forms/serializers/full_clean();
    # the CheckConstraints below enforce the same rules inside the database.
    month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])

    objects = BudgetQuerySet.as_manager()

    class Meta:
        ordering = ["category", "id"]
        constraints = [
            # One budget per user + category + month + year. This is what makes "set budget" an
            # upsert (update_or_create) and it prevents duplicates even under concurrent requests.
            models.UniqueConstraint(
                fields=["user", "category", "month", "year"], name="uq_budget_user_category_period"
            ),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="budget_amount_positive"),
            models.CheckConstraint(
                condition=models.Q(month__gte=1, month__lte=12), name="budget_month_between_1_and_12"
            ),
            models.CheckConstraint(
                condition=models.Q(year__gte=2000, year__lte=2100), name="budget_year_between_2000_and_2100"
            ),
        ]
        indexes = [
            # Listing and alerts always filter by user + period; the unique constraint's index
            # starts with (user, category) so it cannot serve that lookup.
            models.Index(fields=["user", "year", "month"], name="budget_user_period_idx"),
        ]

    def __str__(self):
        return f"{self.category} {self.month}/{self.year}: {self.amount}"
