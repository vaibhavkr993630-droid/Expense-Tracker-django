"""Production settings. Every sensitive value must come from the environment."""

from .base import *  # noqa: F403
from .base import MIDDLEWARE, env

# No defaults: if these are missing the app refuses to start, which is what we want.
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
DEBUG = False

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# gunicorn does not serve static files (admin CSS/JS), so WhiteNoise middleware does it.
# It must sit right after SecurityMiddleware.
MIDDLEWARE = [MIDDLEWARE[0], "whitenoise.middleware.WhiteNoiseMiddleware", *MIDDLEWARE[1:]]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Compresses files and adds a content hash to their names so browsers can cache them forever.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# HTTPS hardening (checked by `manage.py check --deploy`). On by default.
# Set USE_HTTPS=false ONLY for a local run over plain http (e.g. docker compose on localhost):
# secure cookies and HTTPS redirects would otherwise make the admin login impossible there.
USE_HTTPS = env.bool("USE_HTTPS", default=True)
# Platforms such as Railway/Render/nginx terminate TLS, so trust the proxy's forwarded-protocol header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = USE_HTTPS
SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600 if USE_HTTPS else 0)
