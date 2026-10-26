
# syntax=docker/dockerfile:1.7

# ===== BUILDER =====
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn


# ===== BASE =====
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOME="/home/appuser"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    media-types \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv


# ===== TESTING =====
FROM base AS test

RUN pip install --no-cache-dir pytest

COPY . .

CMD ["pytest", "--maxfail=3", "--disable-warnings"]


# ===== PRODUCTION =====
FROM base AS prod

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 \
       --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app/logs /home/appuser

COPY --chown=appuser:appuser . /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
