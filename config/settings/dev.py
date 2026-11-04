"""Local development settings. Used by manage.py and pytest."""

from .base import *  # noqa: F403
from .base import env

# A throw-away key is acceptable ONLY here, never in production.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-do-not-use-in-production")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])

# The React dev server (Vite) runs on a different origin.
CORS_ALLOW_ALL_ORIGINS = True

# Print emails to the terminal instead of sending them.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
