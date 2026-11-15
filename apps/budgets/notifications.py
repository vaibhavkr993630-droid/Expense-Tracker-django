"""
Budget alert emails.

Rule: email a user only when a budget's alert level gets WORSE than the level we last told them
about (ok -> warning -> exceeded). The level we last emailed is stored on the budget
(`Budget.last_alert_status`), so:
  - adding more expenses at the same level does not send another email,
  - running the scheduled command every day does not spam anyone,
  - once spending drops back to "ok", the level resets and a future warning emails again.
"""

import calendar
import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import Budget
from .services import EXCEEDED, OK, WARNING, get_budget_alerts

logger = logging.getLogger(__name__)

# Higher number = worse. "" (never alerted) counts the same as ok.
SEVERITY = {"": 0, OK: 0, WARNING: 1, EXCEEDED: 2}


def _send_alert_email(user, alerts, month, year):
    context = {
        "username": user.username,
        "month_name": calendar.month_name[month],
        "year": year,
        "alerts": alerts,
    }
    # Templates keep wording/layout out of Python code. We send a plain-text body plus an HTML
    # alternative; mail clients show the HTML and fall back to text.
    text_body = render_to_string("budgets/budget_alert_email.txt", context)
    html_body = render_to_string("budgets/budget_alert_email.html", context)
    subject = f"Budget alert: {calendar.month_name[month]} {year} | Expense Tracker"
    message = EmailMultiAlternatives(subject, text_body, to=[user.email])  # From = DEFAULT_FROM_EMAIL
    message.attach_alternative(html_body, "text/html")
    message.send()  # raises if the mail server rejects it


def send_budget_alerts(user, month, year, dry_run=False):
    """
    Email `user` about budgets that crossed a worse alert level. Returns the alerts that triggered.

    The stored level is updated only AFTER the email was sent, so if sending fails nothing is
    marked as sent and the next run tries again.
    """
    if not user.is_active:
        return []

    alerts = get_budget_alerts(user, month, year)  # 2 queries, see services.py
    to_notify = [a for a in alerts if SEVERITY[a["status"]] > SEVERITY[a["previous_status"]]]
    if dry_run:
        return to_notify

    if to_notify:
        _send_alert_email(user, to_notify, month, year)

    # Remember the current level of every budget whose level changed (including "back to ok").
    ids_by_new_level = {}
    for alert in alerts:
        new_level = "" if alert["status"] == OK else alert["status"]
        if new_level != alert["previous_status"]:
            ids_by_new_level.setdefault(new_level, []).append(alert["budget_id"])
    for new_level, budget_ids in ids_by_new_level.items():
        Budget.objects.filter(pk__in=budget_ids).update(last_alert_status=new_level)

    return to_notify


def notify_budget_alerts(user, month, year):
    """
    Called from API views after spending or budgets change.

    A broken mail server must never make "add expense" fail, so errors are logged and swallowed
    here. (The management command calls send_budget_alerts directly and reports failures.)
    """
    try:
        return send_budget_alerts(user, month, year)
    except Exception:
        logger.exception("Could not send budget alert email for user %s", user.pk)
        return []
