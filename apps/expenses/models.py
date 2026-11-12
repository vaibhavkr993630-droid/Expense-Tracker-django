from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Category(models.TextChoices):
    """
    The allowed expense categories.

    TextChoices gives us, from one definition: the values stored in the database, human
    labels, validation (`full_clean`), dropdowns in the admin, and `Category.choices` for forms
    and serializers. It replaces the old hard-coded ALLOWED_CATEGORIES list.
    """

    GROCERIES = "Groceries"
    LEISURE = "Leisure"
    ELECTRONICS = "Electronics"
    UTILITIES = "Utilities"
    CLOTHING = "Clothing"
    HEALTH = "Health"
    OTHERS = "Others"


class ExpenseQuerySet(models.QuerySet):
    """
    Reusable, chainable query helpers.

    Because they live on the QuerySet (and the manager is built with `as_manager()`),
    they work both as `Expense.objects.for_user(u)` and when chained:
    `Expense.objects.for_user(u).in_month(5, 2026).total()`.
    Views and services call these instead of repeating `.filter(...)` everywhere.
    """

    def for_user(self, user):
        """Only this user's expenses: the basis of 'users see only their own data'."""
        return self.filter(user=user)

    def in_date_range(self, from_date=None, to_date=None):
        """Inclusive date range; either end may be omitted."""
        queryset = self
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)
        return queryset

    def in_month(self, month, year):
        # __month / __year lookups translate to the database's date-extraction functions.
        return self.filter(date__month=month, date__year=year)

    def in_period(self, month=None, year=None):
        """Filter by month and/or year; each is optional (used by the category breakdown)."""
        queryset = self
        if month:
            queryset = queryset.filter(date__month=month)
        if year:
            queryset = queryset.filter(date__year=year)
        return queryset

    def total(self):
        """Sum of amounts, as a Decimal (0 when there are no rows) - one SQL query."""
        return self.aggregate(total=Sum("amount"))["total"] or 0


class Expense(models.Model):
    # settings.AUTH_USER_MODEL (not a direct import) keeps the app working with any user model.
    # on_delete=CASCADE: deleting a user deletes their expenses (same as the old ON DELETE CASCADE).
    # related_name lets us write `user.expenses.all()`.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")
    # DecimalField (not float) so money is exact: 0.1 + 0.2 == 0.3.
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=Category.choices)
    # Django convention: text fields use "" instead of NULL for "no value" (blank=True).
    description = models.CharField(max_length=200, blank=True, default="")
    # Pass the function, not its result: it is evaluated per row, not once at startup.
    # localdate() respects the project time zone.
    date = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ExpenseQuerySet.as_manager()

    class Meta:
        # Default ordering for every query: newest first (id breaks ties so pagination is stable).
        ordering = ["-date", "-id"]
        indexes = [
            # Almost every query is "this user's expenses, newest first / in a date range".
            models.Index(fields=["user", "-date"], name="expense_user_date_idx"),
            # Used by the category breakdown (filter by user, group by category).
            models.Index(fields=["user", "category"], name="expense_user_category_idx"),
        ]
        constraints = [
            # Enforced by the DATABASE, so bad data is impossible even if code skips validation.
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="expense_amount_positive"),
        ]

    def __str__(self):
        return f"{self.date} {self.category} {self.amount}"
