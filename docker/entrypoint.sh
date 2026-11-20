#!/bin/sh
# Container start-up: apply database migrations, then run the app server.
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn..."
# exec replaces this shell with gunicorn so it receives stop signals (graceful shutdown).
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY:-3}" \
    --access-logfile -
