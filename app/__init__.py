from flask_jwt_extended import JWTManager
from flask import Flask
from config import Config
from app.database import init_db, set_db_globals
from logger import setup_logger
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS
from flask_restx import Api
from app.routes import register_namespaces

authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Добавьте JWT-токен в формате: Bearer <jwt_token>'
    }
}

def create_app():
    app = Flask(__name__)


    app.config.from_object(Config)
    # Добавляем ProxyFix для корректной обработки заголовков от прокси-сервера
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,  # Используем 1 прокси для заголовка X-Forwarded-For
        x_proto=1,  # Учитываем X-Forwarded-Proto (HTTP/HTTPS)
        x_host=1,  # Учитываем X-Forwarded-Host
        x_port=1   # Учитываем X-Forwarded-Port
    )
    # Инициализация базы данных
    try:
        engine, Session, Base = init_db(app.config['SQLALCHEMY_DATABASE_URI'])
        set_db_globals(engine, Session, Base)
        logger = setup_logger()
        logger.info("База данных успешно инициализирована.", extra={'user_id': 'init'})
    except Exception as e:
        #logger.error(f"Ошибка при инициализации базы данных: {e}", extra={'user_id': 'init'})
        raise

    # Инициализация JWT
    try:
        jwt = JWTManager(app)
        logger.info(f"JWT инициализирован. {app.config['JWT_ACCESS_TOKEN_EXPIRES']}", extra={'user_id': 'init'})
    except Exception as e:
        logger.error(f"Ошибка при инициализации JWT: {e}", extra={'user_id': 'init'})
        raise



    from app.routes import register_routes
    # Регистрация маршрутов
    try:
        register_routes(app)
        logger.info("Маршруты успешно зарегистрированы.", extra={'user_id': 'init'})
    except Exception as e:
        logger.error(f"Ошибка при регистрации маршрутов: {e}", extra={'user_id': 'init'})
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



