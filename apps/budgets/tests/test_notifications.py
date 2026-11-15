import logging
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from django.core import mail

from apps.budgets.notifications import notify_budget_alerts, send_budget_alerts

pytestmark = pytest.mark.django_db


@pytest.fixture
def groceries_budget(user, make_budget):
    return make_budget(user, "Groceries", amount="100")  # May 2026


def send(user, **kwargs):
    return send_budget_alerts(user, 5, 2026, **kwargs)


class TestWhenToEmail:
    def test_ok_status_sends_nothing(self, user, groceries_budget, make_expense, mailoutbox):
        make_expense(user, amount="50")
        assert send(user) == []
        assert mailoutbox == []

    def test_no_budgets_sends_nothing(self, user, make_expense, mailoutbox):
        make_expense(user, amount="500")
        assert send(user) == []
        assert mailoutbox == []

    @pytest.mark.parametrize("amount, level", [("80", "warning"), ("100", "warning"), ("100.01", "exceeded")])
    def test_warning_and_exceeded_send_one_email(
        self, user, groceries_budget, make_expense, mailoutbox, amount, level
    ):
        make_expense(user, amount=amount)
        alerts = send(user)
        assert [a["status"] for a in alerts] == [level]
        assert len(mailoutbox) == 1
        groceries_budget.refresh_from_db()
        assert groceries_budget.last_alert_status == level

    def test_same_level_is_not_emailed_twice(self, user, groceries_budget, make_expense, mailoutbox):
        make_expense(user, amount="85")
        send(user)
        make_expense(user, amount="5")  # still warning (90%)
        assert send(user) == []
        assert len(mailoutbox) == 1

    def test_escalation_from_warning_to_exceeded_emails_again(
        self, user, groceries_budget, make_expense, mailoutbox
    ):
        make_expense(user, amount="85")
        send(user)
        make_expense(user, amount="30")  # now 115%
        assert [a["status"] for a in send(user)] == ["exceeded"]
        assert len(mailoutbox) == 2

    def test_dropping_back_to_ok_resets_so_a_later_warning_emails_again(
        self, user, groceries_budget, make_expense, mailoutbox
    ):
        big = make_expense(user, amount="85")
        send(user)  # warning emailed
        big.delete()
        send(user)  # back to ok -> level reset, no email
        groceries_budget.refresh_from_db()
        assert groceries_budget.last_alert_status == ""
        make_expense(user, amount="90")
        assert [a["status"] for a in send(user)] == ["warning"]
        assert len(mailoutbox) == 2

    def test_improving_from_exceeded_to_warning_does_not_email_but_remembers(
        self, user, groceries_budget, make_expense, mailoutbox
    ):
        extra = make_expense(user, amount="120")
        send(user)  # exceeded emailed
        extra.amount = 85
        extra.save()
        assert send(user) == []  # warning is better than exceeded: no email
        groceries_budget.refresh_from_db()
        assert groceries_budget.last_alert_status == "warning"
        assert len(mailoutbox) == 1


class TestEmailContent:
    def test_one_email_per_user_listing_every_triggered_category(
        self, user, make_budget, make_expense, mailoutbox
    ):
        make_budget(user, "Groceries", amount="100")
        make_budget(user, "Health", amount="100")
        make_budget(user, "Leisure", amount="100")
        make_expense(user, amount="85", category="Groceries")
        make_expense(user, amount="150", category="Health")
        make_expense(user, amount="10", category="Leisure")  # ok: must not be listed
        send(user)
        assert len(mailoutbox) == 1
        email = mailoutbox[0]
        assert email.to == [user.email]
        assert email.subject == "Budget alert: May 2026 | Expense Tracker"
        assert "Groceries: WARNING" in email.body
        assert "Health: EXCEEDED" in email.body
        assert "spent $150.00 of $100.00 (150.0% used)" in email.body
        assert "Leisure" not in email.body
        assert "alice" in email.body

    def test_has_an_html_alternative(self, user, groceries_budget, make_expense, mailoutbox):
        make_expense(user, amount="90")
        send(user)
        html, mimetype = mailoutbox[0].alternatives[0]
        assert mimetype == "text/html"
        assert "<table" in html and "Groceries" in html


class TestSafetyRules:
    def test_other_users_spending_never_triggers_my_email(
        self, user, other_user, groceries_budget, make_expense, mailoutbox
    ):
        make_expense(other_user, amount="999")
        assert send(user) == []
        assert mailoutbox == []

    def test_inactive_users_are_skipped(self, user, groceries_budget, make_expense, mailoutbox):
        make_expense(user, amount="90")
        user.is_active = False
        user.save()
        assert send(user) == []
        assert mailoutbox == []

    def test_dry_run_sends_and_saves_nothing(self, user, groceries_budget, make_expense, mailoutbox):
        make_expense(user, amount="90")
        assert [a["status"] for a in send(user, dry_run=True)] == ["warning"]
        assert mailoutbox == []
        groceries_budget.refresh_from_db()
        assert groceries_budget.last_alert_status == ""

    def test_failed_send_marks_nothing_so_the_next_run_retries(
        self, user, groceries_budget, make_expense, mailoutbox
    ):
        make_expense(user, amount="90")
        with patch(
            "apps.budgets.notifications.EmailMultiAlternatives.send", side_effect=SMTPException("down")
        ):
            with pytest.raises(SMTPException):
                send(user)
        groceries_budget.refresh_from_db()
        assert groceries_budget.last_alert_status == ""
        assert [a["status"] for a in send(user)] == ["warning"]  # works once the server is back
        assert len(mailoutbox) == 1

    def test_view_helper_swallows_and_logs_failures(self, user, groceries_budget, make_expense, caplog):
        make_expense(user, amount="90")
        with patch(
            "apps.budgets.notifications.EmailMultiAlternatives.send", side_effect=SMTPException("down")
        ):
            with caplog.at_level(logging.ERROR):
                assert notify_budget_alerts(user, 5, 2026) == []  # does not raise
        assert "Could not send budget alert email" in caplog.text

    def test_query_count_does_not_grow_with_budget_count(
        self, user, make_budget, make_expense, django_assert_max_num_queries
    ):
        for category in ["Groceries", "Leisure", "Electronics", "Utilities", "Clothing", "Health", "Others"]:
            make_budget(user, category, amount="10")
            make_expense(user, category=category, amount="50")  # all exceeded
        # 2 (alerts) + 3 at most (one UPDATE per new level) + no per-budget queries
        with django_assert_max_num_queries(6):
            assert len(send(user)) == 7
        assert len(mail.outbox) == 1
