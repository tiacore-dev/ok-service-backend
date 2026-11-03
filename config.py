import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Базовая конфигурация."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # The limit applies to the complete HTTP request, including multipart
    # headers and boundaries. It is slightly above the per-file 100 MiB limit
    # enforced by AsyncS3Manager.

    MAX_CONTENT_LENGTH = 105 * 1024 * 1024
    TESTING = False
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    DATABASE_NAME = os.getenv("DATABASE_NAME")
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "30")
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRES_MINUTES)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    API_KEY = os.getenv("API_KEY")
    ORIGIN = os.getenv("ORIGIN")
    BROWSER_ID_COOKIE_NAME = "browser_id"
    BROWSER_ID_COOKIE_MAX_AGE = 90 * 24 * 60 * 60
    TEMPLATE_SERVICE_OLD_URL = os.getenv("TEMPLATE_SERVICE_OLD_URL")
    TEMPLATE_SERVICE_NEW_URL = os.getenv("TEMPLATE_SERVICE_NEW_URL")
    TEMPLATE_SERVICE_API_KEY = os.getenv("TEMPLATE_SERVICE_API_KEY")
    MOONSHOT_API_KEY = os.getenv("MOONSHOT_API_KEY")
    MOONSHOT_MODEL = os.getenv("MOONSHOT_MODEL")
    MOONSHOT_URL = os.getenv("MOONSHOT_URL", "https://api.moonshot.ai")
    MOONSHOT_COMPLETION_TIMEOUT_SECONDS = float(
        os.getenv("MOONSHOT_COMPLETION_TIMEOUT_SECONDS", "300")
    )
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "ok_service")
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT = os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "http://jaeger:4318/v1/traces"
    )
    OTEL_EXPORTER_OTLP_TIMEOUT = int(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "10"))
    # Клиент создаётся лениво: соединение с Redis открывается только при команде.
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Push delivery is not invoked from HTTP handlers.  These settings prepare
    # the provider for the forthcoming dedicated delivery worker.
    PUSH_PROVIDER = os.getenv("PUSH_PROVIDER", "noop")
    FCM_PROJECT_ID = os.getenv("FCM_PROJECT_ID")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    ENDPOINT_URL = os.getenv("ENDPOINT_URL")
    REGION_NAME = os.getenv("REGION_NAME")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    BUCKET_NAME = os.getenv("BUCKET_NAME")


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


class TestingConfig(Config):
    """Конфигурация для тестирования."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL")
