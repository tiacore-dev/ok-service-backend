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
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=365)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    API_KEY = os.getenv("API_KEY")
    ORIGIN = os.getenv("ORIGIN")
    TEMPLATE_SERVICE_URL = os.getenv("TEMPLATE_SERVICE_URL")
    # Клиент создаётся лениво: соединение с Redis открывается только при команде.
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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
