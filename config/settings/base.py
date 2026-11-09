"""
Settings shared by every environment.

Environment-specific values live in dev.py / prod.py, which start with
`from .base import *` and then override what they need.
Secrets and deployment values are read from environment variables (12-factor style)
so nothing sensitive is ever committed.
"""

from datetime import timedelta
from pathlib import Path

import environ

# BASE_DIR = project root (the folder that contains manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Read a local .env file if there is one. In Docker / production the variables come
# from the real environment instead, so a missing file is fine.
environ.Env.read_env(BASE_DIR / ".env")

# NOTE: SECRET_KEY and DEBUG are deliberately NOT defined here: dev.py and prod.py set them.

INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "apps.accounts",
    "apps.expenses",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # must sit above CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DATABASE_URL (e.g. postgres://user:pass@host:5432/db) selects the database.
# Without it we fall back to a local SQLite file so the project runs with zero setup.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

# Custom user model: must be set before the very first migration.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email settings are read from the environment; dev.py switches to the console backend.
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Expense Tracker <noreply@example.com>")

# --- Authentication -------------------------------------------------------------------
# Tried in order. Ours lets people log in with either their email or their username
# (the React login form has a single "username" box); the default backend stays for the admin.
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# --- Cache -----------------------------------------------------------------------------
# Per-process memory cache: enough for development and for DRF's throttle counters.
# (Day 6 reuses it for analytics; production could swap in Redis with one setting change.)
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Django REST Framework ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    # Secure by default: every endpoint needs a valid token unless a view opts out.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Throttling replaces slowapi. "Scoped" throttles are switched on per view.
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_RATES": {"signup": "5/min", "login": "10/min"},
    # The frontend expects {"detail": "..."} for every error.
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
    # Money is returned as a JSON number (the old API did that), not a string.
    "COERCE_DECIMAL_TO_STRING": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),  # same lifetime as the FastAPI version
    "AUTH_HEADER_TYPES": ("Bearer",),
}
