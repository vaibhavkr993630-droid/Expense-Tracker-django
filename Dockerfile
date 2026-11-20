# Image for the Django API (the React frontend is built and served separately).
FROM python:3.12-slim

# No .pyc files, unbuffered logs (so `docker logs` shows output immediately), smaller pip layer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# Install dependencies first: this layer is cached and only rebuilt when requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy only what the API needs (see .dockerignore: no frontend, tests data, secrets or legacy code).
COPY manage.py ./
COPY config ./config
COPY apps ./apps
COPY docker/entrypoint.sh ./docker/entrypoint.sh

# Collect admin/static files into /app/staticfiles (served by WhiteNoise). The values below exist only
# for this build step so Django can start; the real ones are supplied when the container runs.
RUN DJANGO_SECRET_KEY=build-only DJANGO_ALLOWED_HOSTS=localhost python manage.py collectstatic --noinput \
    && chmod +x docker/entrypoint.sh

# Do not run as root inside the container.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000
ENTRYPOINT ["./docker/entrypoint.sh"]
