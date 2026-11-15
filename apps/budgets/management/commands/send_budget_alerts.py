from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.budgets.notifications import send_budget_alerts

User = get_user_model()


class Command(BaseCommand):
    """
    Run with:  python manage.py send_budget_alerts [--month 5 --year 2026] [--dry-run]

    A management command is Django's way to run a task outside a web request, e.g. from cron:
        0 8 * * *  cd /app && python manage.py send_budget_alerts
    It replaces the old APScheduler job. Because emails are only sent when a budget gets worse,
    running it daily is safe. (Celery beat could schedule it later; cron needs no extra services.)
    """

    help = "Email users whose budgets crossed the warning (80%) or exceeded level this month."

    def add_arguments(self, parser):
        parser.add_argument("--month", type=int, help="Month 1-12 (default: current month)")
        parser.add_argument("--year", type=int, help="Year (default: current year)")
        parser.add_argument(
            "--dry-run", action="store_true", help="Show who would be emailed without sending anything"
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        # `is None`, not `or`: 0 is a real (invalid) value that must be rejected, not replaced.
        month = today.month if options["month"] is None else options["month"]
        year = today.year if options["year"] is None else options["year"]
        if not 1 <= month <= 12:
            raise CommandError("--month must be between 1 and 12.")
        if not 2000 <= year <= 2100:
            raise CommandError("--year must be between 2000 and 2100.")
        dry_run = options["dry_run"]

        # Only users who actually have a budget this month; distinct() because the join on
        # budgets would otherwise return a user once per budget.
        users = User.objects.filter(is_active=True, budgets__month=month, budgets__year=year).distinct()

        emailed, failed = 0, 0
        for user in users.iterator():
            try:
                alerts = send_budget_alerts(user, month, year, dry_run=dry_run)
            except Exception as error:  # one user's failure must not stop the others
                failed += 1
                self.stderr.write(self.style.ERROR(f"{user.email}: failed to send ({error})"))
                continue
            if alerts:
                emailed += 1
                summary = ", ".join(f"{a['category']}: {a['status']}" for a in alerts)
                verb = "would email" if dry_run else "emailed"
                self.stdout.write(f"{verb} {user.email} -> {summary}")

        label = "would be emailed" if dry_run else "emailed"
        self.stdout.write(self.style.SUCCESS(f"Done: {emailed} user(s) {label} for {month}/{year}."))
        if failed:
            raise CommandError(f"{failed} email(s) failed.")  # non-zero exit code for cron/monitoring
