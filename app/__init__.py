import time
from flask_jwt_extended import JWTManager
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import Flask
from flask import request, g
from flask_cors import CORS
from flask_restx import Api
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import REGISTRY
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_marshmallow import Marshmallow
from config import DevelopmentConfig, TestingConfig
from logger import setup_logger
from app.routes import register_namespaces, register_routes
from app.database import init_db, set_db_globals, setup_listeners
from app.database.vacuum import start_background_task
from app.utils.db_setting_tables import set_roles, set_object_status
from app.error_handlers import setup_error_handlers


authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Добавьте JWT-токен в формате: Bearer <jwt_token>'
    }
}


ma = Marshmallow()


def create_app(config_name="development"):
    """Функция для создания экземпляра приложения"""
    app = Flask(__name__)
    # Выбираем конфигурацию
    if config_name == "development":
        metrics = PrometheusMetrics(app)
    # необязательно, но можно указать кастомные метрики
        if "app_info" not in REGISTRY._names_to_collectors:
            metrics.info('app_info', 'Описание приложения', version='1.0.3')
        app.config.from_object(DevelopmentConfig)
        # Настройка
        trace.set_tracer_provider(
            TracerProvider(
                resource=Resource.create({"service.name": "ok_service"})
            )
        )

        jaeger_exporter = JaegerExporter(
            agent_host_name="jaeger",  # имя контейнера!
            agent_port=6831,
        )

        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        FlaskInstrumentor().instrument_app(app)
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
                extra={'login': 'init'})

    # Запуск фоновой задачи при старте приложения

    # Инициализация ролей и админа

    set_roles()

    set_object_status()

    if config_name != "testing":
        setup_listeners()
        with app.app_context():
            start_background_task()

    # Инициализация JWT
    try:
        JWTManager(app)
        logger.info(f"JWT инициализирован. {app.config['JWT_ACCESS_TOKEN_EXPIRES']}",
                    extra={'login': 'init'})
    except Exception as e:
        logger.error(f"Ошибка при инициализации JWT: {e}",
                     extra={'login': 'init'})
        raise

    # Регистрация маршрутов
    try:
        register_routes(app)
        logger.info("Маршруты успешно зарегистрированы.",
                    extra={'login': 'init'})
    except Exception as e:
        logger.error(f"Ошибка при регистрации маршрутов: {e}",
                     extra={'login': 'init'})
        raise

    # Инициализация Marshmallow
    ma.init_app(app)

    # Инициализация API
    api = Api(
        app,
        doc='/swagger',
        security='Bearer',
        authorizations=authorizations
    )
    # Регистрация маршрутов
    register_namespaces(api)

    setup_error_handlers(app)

    @app.before_request
    def inject_user_info():
        try:
            verify_jwt_in_request(optional=True)
            g.user_info = get_jwt_identity() or "anonymous"
        except Exception:
            g.user_info = "anonymous"

    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        try:
            path = request.path

            # Не логируем /metrics
            if path == "/metrics":
                return response

            duration = time.time() - g.get("start_time", time.time())
            method = request.method
            status = response.status_code
            user_agent = request.headers.get("User-Agent", "unknown")
            user_info = getattr(g, "user_info", "anonymous")

            logger.info(
                f"{method} {path} {status} {round(duration * 1000)}ms {user_agent}",
                extra={"login": user_info}
            )
        except Exception as e:
            logger.error(f"Error while logging request: {e}")
        return response

    # Настройка CORS
    CORS(app, resources={r"/*": {"origins": '*'}})

    return app
