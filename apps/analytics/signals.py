"""
Signals let one part of the app react to events elsewhere without the two knowing each other.
The Expense model and the expense views know nothing about caching; this module listens for
"an expense was saved / deleted" and invalidates that user's cached analytics.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.expenses.models import Expense

from .cache import invalidate_user_analytics


@receiver([post_save, post_delete], sender=Expense, dispatch_uid="analytics_invalidate_on_expense_change")
def expense_changed(sender, instance, **kwargs):
    invalidate_user_analytics(instance.user_id)
