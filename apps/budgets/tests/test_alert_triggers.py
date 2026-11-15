"""The API endpoints trigger alerts after spending or budgets change."""

from smtplib import SMTPException
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def budget_100(user, make_budget):
    return make_budget(user, "Groceries", amount="100")


def expense(amount, category="Groceries", date="2026-05-10"):
    return {"amount": amount, "category": category, "date": date}


def test_adding_expenses_emails_when_a_level_is_crossed_only(auth_client, budget_100, mailoutbox):
    auth_client.post("/expenses", expense("50"), format="json")
    assert len(mailoutbox) == 0  # 50%: ok
    auth_client.post("/expenses", expense("35"), format="json")
    assert len(mailoutbox) == 1  # 85%: warning
    auth_client.post("/expenses", expense("5"), format="json")
    assert len(mailoutbox) == 1  # 90%: still warning, no repeat
    auth_client.post("/expenses", expense("20"), format="json")
    assert len(mailoutbox) == 2  # 110%: exceeded
    assert "EXCEEDED" in mailoutbox[1].body


def test_only_the_matching_month_and_category_count(auth_client, budget_100, mailoutbox):
    auth_client.post("/expenses", expense("500", category="Health"), format="json")
    auth_client.post("/expenses", expense("500", date="2026-06-10"), format="json")
    assert mailoutbox == []


def test_updating_an_expense_can_trigger(auth_client, user, budget_100, make_expense, mailoutbox):
    small = make_expense(user, amount="10")
    auth_client.put(f"/expenses/{small.id}", {"amount": "95"}, format="json")
    assert len(mailoutbox) == 1


def test_moving_an_expense_into_the_budget_month_triggers(
    auth_client, user, budget_100, make_expense, mailoutbox
):
    elsewhere = make_expense(user, amount="95", date="2026-04-10")
    auth_client.put(f"/expenses/{elsewhere.id}", {"date": "2026-05-10"}, format="json")
    assert len(mailoutbox) == 1


def test_deleting_resets_the_level_so_it_can_alert_again(
    auth_client, user, budget_100, make_expense, mailoutbox
):
    big = make_expense(user, amount="90")
    auth_client.post("/expenses", expense("1"), format="json")  # crosses 80% -> email
    assert len(mailoutbox) == 1
    auth_client.delete(f"/expenses/{big.id}")  # back to ok -> reset
    budget_100.refresh_from_db()
    assert budget_100.last_alert_status == ""
    auth_client.post("/expenses", expense("85"), format="json")
    assert len(mailoutbox) == 2


def test_lowering_a_budget_below_current_spending_triggers(
    auth_client, user, budget_100, make_expense, mailoutbox
):
    make_expense(user, amount="60")
    auth_client.post(
        "/budgets", {"category": "Groceries", "amount": 50, "month": 5, "year": 2026}, format="json"
    )
    assert len(mailoutbox) == 1
    assert "EXCEEDED" in mailoutbox[0].body


def test_a_broken_mail_server_does_not_break_the_api(auth_client, budget_100):
    with patch("apps.budgets.notifications.EmailMultiAlternatives.send", side_effect=SMTPException("down")):
        response = auth_client.post("/expenses", expense("95"), format="json")
    assert response.status_code == 201  # the expense was still saved


def test_other_users_budgets_are_never_emailed(auth_client, other_user, make_budget, mailoutbox):
    make_budget(other_user, "Groceries", amount="10")
    auth_client.post("/expenses", expense("500"), format="json")
    assert mailoutbox == []
