from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.budgets.models import Budget

pytestmark = pytest.mark.django_db


def test_one_budget_per_user_category_and_period(user, make_budget):
    make_budget(user, "Groceries", month=5, year=2026)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_budget(user, "Groceries", month=5, year=2026)


def test_same_period_is_allowed_for_other_users_categories_and_months(user, other_user, make_budget):
    make_budget(user, "Groceries", month=5, year=2026)
    make_budget(other_user, "Groceries", month=5, year=2026)  # other user
    make_budget(user, "Health", month=5, year=2026)  # other category
    make_budget(user, "Groceries", month=6, year=2026)  # other month
    make_budget(user, "Groceries", month=5, year=2027)  # other year
    assert Budget.objects.count() == 5


@pytest.mark.parametrize(
    "field, value",
    [("amount", "0"), ("amount", "-1"), ("month", 0), ("month", 13), ("year", 1999), ("year", 2101)],
)
def test_database_check_constraints(user, field, value):
    values = {"user": user, "category": "Health", "amount": Decimal("10"), "month": 5, "year": 2026}
    values[field] = Decimal(value) if field == "amount" else value
    with pytest.raises(IntegrityError), transaction.atomic():
        Budget.objects.create(**values)


def test_model_validators_reject_bad_month(user):
    budget = Budget(user=user, category="Health", amount=Decimal("5"), month=13, year=2026)
    with pytest.raises(ValidationError) as exc:
        budget.full_clean(validate_unique=False)
    assert "month" in exc.value.message_dict


def test_queryset_helpers(user, other_user, make_budget):
    may = make_budget(user, month=5, year=2026)
    make_budget(user, month=6, year=2026)
    make_budget(other_user, month=5, year=2026)
    assert list(Budget.objects.for_user(user).for_period(5, 2026)) == [may]


def test_deleting_user_deletes_budgets(user, other_user, make_budget):
    make_budget(user)
    keep = make_budget(other_user)
    user.delete()
    assert list(Budget.objects.all()) == [keep]
