# Используем официальный образ Python в качестве базового
FROM python:3.12-slim

# Указываем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем зависимости системы (включая curl и ping)
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



# Копируем файл зависимостей в рабочую директорию
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Gunicorn
RUN pip install gunicorn


# Копируем весь код приложения в рабочую директорию
COPY . .

