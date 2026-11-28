# Shared Python runtime for development and production.
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .
RUN mkdir -p /app/data && chown -R app:app /app/data

EXPOSE 8000

# Development: source is bind-mounted; watchfiles restarts on Python changes.
FROM base AS development
RUN python -m pip install --no-cache-dir -r requirements-dev.txt
USER app
CMD ["watchfiles", "--filter", "python", "--force-polling", "python app.py", "/app"]

# Production: Gunicorn; no source-code bind mount.
FROM base AS production
USER app
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=2", "--timeout=30", "--access-logfile=-", "--error-logfile=-", "wsgi:app"]
