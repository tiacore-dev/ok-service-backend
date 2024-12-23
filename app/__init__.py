from flask_jwt_extended import JWTManager
from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from werkzeug.middleware.proxy_fix import ProxyFix
from config import DevelopmentConfig, TestingConfig
from logger import setup_logger
from app.routes import register_namespaces, register_routes
from app.database import init_db, set_db_globals
from app.utils.db_setting_tables import set_admin, set_roles, set_object_status

authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Добавьте JWT-токен в формате: Bearer <jwt_token>'
    }
}


def create_app(config_name="development"):
    """Функция для создания экземпляра приложения"""
    app = Flask(__name__)
    # Выбираем конфигурацию
    if config_name == "development":
        app.config.from_object(DevelopmentConfig)
    elif config_name == "testing":
        app.config.from_object(TestingConfig)
    else:
        raise ValueError(f"Неизвестное имя конфигурации: {config_name}")

    # Добавляем ProxyFix для корректной обработки заголовков от прокси-сервера
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,  # Используем 1 прокси для заголовка X-Forwarded-For
        x_proto=1,  # Учитываем X-Forwarded-Proto (HTTP/HTTPS)
        x_host=1,  # Учитываем X-Forwarded-Host
        x_port=1   # Учитываем X-Forwarded-Port
    )
    # Инициализация базы данных
    engine, Session, Base = init_db(
        app.config['SQLALCHEMY_DATABASE_URI'], config_name)
    set_db_globals(engine, Session, Base)
    logger = setup_logger()
    logger.info("База данных успешно инициализирована.",
                extra={'user_id': 'init'})

    # Инициализация ролей и админа

    set_roles()
    set_admin()
    set_object_status()

    # Инициализация JWT
    try:
        JWTManager(app)
        logger.info(f"JWT инициализирован. {app.config['JWT_EXPIRES']}",
                    extra={'user_id': 'init'})
    except Exception as e:
        logger.error(f"Ошибка при инициализации JWT: {e}",
                     extra={'user_id': 'init'})
        raise

    # Регистрация маршрутов
    try:
        register_routes(app)
        logger.info("Маршруты успешно зарегистрированы.",
                    extra={'user_id': 'init'})
    except Exception as e:
        logger.error(f"Ошибка при регистрации маршрутов: {e}",
                     extra={'user_id': 'init'})
        raise

    # Инициализация API
    api = Api(
        app,
        doc='/swagger',
        security='Bearer',
        authorizations=authorizations
    )
    # Регистрация маршрутов
    register_namespaces(api)

    # Настройка CORS
    CORS(app, resources={r"/*": {"origins": app.config['ORIGIN']}})
    return app
