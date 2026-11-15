from io import StringIO

import pytest
from django.core import mail
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db


def run(**options):
    out, err = StringIO(), StringIO()
    call_command("send_budget_alerts", stdout=out, stderr=err, **options)
    return out.getvalue(), err.getvalue()


@pytest.fixture
def scenario(user, other_user, make_budget, make_expense):
    make_budget(user, "Groceries", amount="100")
    make_expense(user, amount="90", category="Groceries")  # warning
    make_budget(other_user, "Health", amount="100")
    make_expense(other_user, amount="500", category="Health")  # exceeded
    return user, other_user


def test_emails_every_user_with_a_triggered_budget(scenario):
    out, _ = run(month=5, year=2026)
    assert sorted(m.to[0] for m in mail.outbox) == ["alice@example.com", "bob@example.com"]
    assert "emailed alice@example.com -> Groceries: warning" in out
    assert "emailed bob@example.com -> Health: exceeded" in out
    assert "Done: 2 user(s) emailed for 5/2026." in out


def test_running_twice_does_not_email_again(scenario):
    run(month=5, year=2026)
    out, _ = run(month=5, year=2026)
    assert len(mail.outbox) == 2
    assert "Done: 0 user(s) emailed" in out


def test_dry_run_reports_without_sending_or_marking(scenario):
    out, _ = run(month=5, year=2026, dry_run=True)
    assert mail.outbox == []
    assert "would email alice@example.com" in out
    run(month=5, year=2026)  # a real run afterwards still sends
    assert len(mail.outbox) == 2


def test_only_the_requested_month_is_processed(scenario):
    run(month=6, year=2026)
    assert mail.outbox == []


def test_defaults_to_the_current_month(user, make_budget, make_expense):
    from django.utils import timezone

    today = timezone.localdate()
    make_budget(user, "Groceries", amount="10", month=today.month, year=today.year)
    make_expense(user, amount="50", date=today)
    run()
    assert len(mail.outbox) == 1


def test_inactive_users_are_skipped(scenario):
    user, _ = scenario
    user.is_active = False
    user.save()
    run(month=5, year=2026)
    assert [m.to[0] for m in mail.outbox] == ["bob@example.com"]


@pytest.mark.parametrize("options", [{"month": 0}, {"month": 13}, {"year": 1999}, {"year": 2101}])
def test_invalid_arguments_are_rejected(options):
    with pytest.raises(CommandError):
        run(**options)


def test_one_failing_user_does_not_stop_the_others(scenario, monkeypatch):
    from smtplib import SMTPException

    from apps.budgets import notifications

    real_send = notifications._send_alert_email

    def flaky(user, alerts, month, year):
        if user.email == "alice@example.com":
            raise SMTPException("rejected")
        return real_send(user, alerts, month, year)

    monkeypatch.setattr(notifications, "_send_alert_email", flaky)
    out = StringIO()
    err = StringIO()
    with pytest.raises(CommandError, match="1 email"):
        call_command("send_budget_alerts", month=5, year=2026, stdout=out, stderr=err)
    assert [m.to[0] for m in mail.outbox] == ["bob@example.com"]  # bob was still processed
    assert "alice@example.com: failed to send" in err.getvalue()
