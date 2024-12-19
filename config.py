import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Базовая конфигурация."""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = False
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    # TEST_DATABSE_URI = os.getenv('TEST_DATABASE_URL')
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_EXPIRES = 3600
    API_KEY = os.getenv('API_KEY')
    ORIGIN = os.getenv('ORIGIN')


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URL", "sqlite:///dev.db")


class TestingConfig(Config):
    """Конфигурация для тестирования."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL')
