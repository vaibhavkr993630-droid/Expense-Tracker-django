from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"

    def ready(self):
        # Importing the module registers its signal receivers. Django calls ready() once at startup.
        from . import signals  # noqa: F401
