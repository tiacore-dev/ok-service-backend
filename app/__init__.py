from flask_jwt_extended import JWTManager
from flask import Flask
from config import Config
from app.database import init_db, set_db_globals
from logger import setup_logger

def create_app():
    app = Flask(__name__)


    app.config.from_object(Config)

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

    return app



