import os
from datetime import timedelta
from dotenv import load_dotenv


load_dotenv()


class Config:
    """Базовая конфигурация."""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = False
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    DATABASE_NAME = os.getenv('DATABASE_NAME')
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_EXPIRES = timedelta(days=1)
    # JWT_EXPIRES = 60
    # JWT_REFRESH_TOKEN_EXPIRES = 300
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    API_KEY = os.getenv('API_KEY')
    ORIGIN = os.getenv('ORIGIN')


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


class TestingConfig(Config):
    """Конфигурация для тестирования."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL')
