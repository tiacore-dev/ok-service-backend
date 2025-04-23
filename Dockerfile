# ===== BASE =====
FROM python:3.12-slim AS base
WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    ca-certificates \
    build-essential \
    python3-dev \
    libpq-dev \
    gcc \
    && update-ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# ===== TESTING =====
FROM base AS test
COPY . .
CMD ["pytest", "--maxfail=3", "--disable-warnings"]

# ===== FINAL =====
FROM base AS prod
COPY . .
CMD ["gunicorn", "app.main:app", "--bind", "0.0.0.0:8000"]
