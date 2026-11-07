from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.expenses.models import Category, Expense

pytestmark = pytest.mark.django_db


class TestFields:
    def test_defaults(self, user):
        expense = Expense.objects.create(user=user, amount=Decimal("12.50"), category=Category.LEISURE)
        assert expense.date == timezone.localdate()  # default evaluated per row
        assert expense.description == ""
        assert expense.created_at and expense.updated_at

    def test_amount_is_exact_decimal(self, user):
        expense = Expense.objects.create(user=user, amount=Decimal("0.10"), category="Health")
        expense.refresh_from_db()
        assert expense.amount == Decimal("0.10")  # a float column would not guarantee this

    def test_str(self, user, make_expense):
        assert str(make_expense(user)) == "2026-05-15 Groceries 10.00"

    def test_category_choices_match_the_api_contract(self):
        assert Category.values == [
            "Groceries", "Leisure", "Electronics", "Utilities", "Clothing", "Health", "Others",
        ]  # fmt: skip

    def test_invalid_category_fails_model_validation(self, user):
        expense = Expense(user=user, amount=Decimal("5"), category="Gambling")
        with pytest.raises(ValidationError) as exc:
            expense.full_clean()
        assert "category" in exc.value.message_dict

    def test_description_too_long_fails_validation(self, user):
        expense = Expense(user=user, amount=Decimal("5"), category="Health", description="x" * 201)
        with pytest.raises(ValidationError) as exc:
            expense.full_clean()
        assert "description" in exc.value.message_dict


class TestDatabaseConstraints:
    @pytest.mark.parametrize("bad_amount", ["0", "-5.00"])
    def test_amount_must_be_positive_in_the_database(self, user, bad_amount):
        # objects.create() skips full_clean(), so only the CheckConstraint can stop this row.
        with pytest.raises(IntegrityError), transaction.atomic():
            Expense.objects.create(user=user, amount=Decimal(bad_amount), category="Health")

    def test_deleting_user_deletes_their_expenses_only(self, user, other_user, make_expense):
        make_expense(user)
        mine_gone = make_expense(user)
        keep = make_expense(other_user)
        user.delete()
        assert not Expense.objects.filter(pk=mine_gone.pk).exists()
        assert list(Expense.objects.all()) == [keep]

    def test_meta_declares_indexes_and_constraint(self):
        index_names = {index.name for index in Expense._meta.indexes}
        assert {"expense_user_date_idx", "expense_user_category_idx"} <= index_names
        assert [c.name for c in Expense._meta.constraints] == ["expense_amount_positive"]


class TestQuerySet:
    def test_default_ordering_is_newest_first(self, user, make_expense):
        old = make_expense(user, date=date(2026, 1, 1))
        new = make_expense(user, date=date(2026, 3, 1))
        same_day_later = make_expense(user, date=date(2026, 3, 1))
        assert list(Expense.objects.all()) == [same_day_later, new, old]

    def test_for_user_isolates_data(self, user, other_user, make_expense):
        mine = make_expense(user)
        make_expense(other_user)
        assert list(Expense.objects.for_user(user)) == [mine]

    def test_in_date_range_is_inclusive_and_optional(self, user, make_expense):
        jan = make_expense(user, date=date(2026, 1, 10))
        feb = make_expense(user, date=date(2026, 2, 10))
        mar = make_expense(user, date=date(2026, 3, 10))
        qs = Expense.objects.for_user(user)
        assert set(qs.in_date_range(date(2026, 1, 10), date(2026, 2, 10))) == {jan, feb}
        assert set(qs.in_date_range(from_date=date(2026, 2, 1))) == {feb, mar}
        assert set(qs.in_date_range(to_date=date(2026, 1, 31))) == {jan}
        assert set(qs.in_date_range()) == {jan, feb, mar}

    def test_in_month_separates_years(self, user, make_expense):
        may_2026 = make_expense(user, date=date(2026, 5, 1))
        make_expense(user, date=date(2025, 5, 1))
        make_expense(user, date=date(2026, 6, 1))
        assert list(Expense.objects.for_user(user).in_month(5, 2026)) == [may_2026]

    def test_total_sums_amounts_and_handles_empty(self, user, other_user, make_expense):
        make_expense(user, amount="10.10")
        make_expense(user, amount="20.20")
        make_expense(other_user, amount="999")
        assert Expense.objects.for_user(user).total() == Decimal("30.30")
        assert Expense.objects.for_user(other_user).in_month(1, 2000).total() == 0

    def test_helpers_chain_and_run_one_query(self, user, make_expense):
        make_expense(user, date=date(2026, 5, 2))
        with CaptureQueriesContext(connection) as queries:
            Expense.objects.for_user(user).in_month(5, 2026).in_date_range(date(2026, 5, 1)).total()
        assert len(queries) == 1  # chained filters are lazy: they merge into a single SQL query
