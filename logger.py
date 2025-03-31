import logging
import os
from opentelemetry.trace import get_current_span, Span
from prometheus_client import Counter

error_counter = Counter('flask_errors_total', 'Total number of errors')

error_counter_by_user = Counter(
    'flask_errors_total_by_user',
    'Total number of errors per user',
    ['user_id', 'login', 'role']
)


class LokiFormatter(logging.Formatter):
    def format(self, record):
        # Получим текущий span, если есть
        span: Span = get_current_span()
        trace_id = "unknown"

        if span and span.get_span_context().trace_id:
            trace_id = format(span.get_span_context().trace_id, '032x')

        # Пользовательская информация
        user_info = getattr(record, "login", {})
        if isinstance(user_info, dict):
            user_id = user_info.get("user_id", "unknown")
            login = user_info.get("login", "unknown")
            role = user_info.get("role", "unknown")
        elif isinstance(user_info, str):
            user_id = "system"
            login = user_info
            role = "system"
        else:
            user_id = login = role = "unknown"

        base_msg = super().format(record)
        return f"{base_msg} [trace_id={trace_id} user_id={user_id} login={login} role={role}]"


class PrometheusHandler(logging.Handler):
    def emit(self, record):
        print("[PrometheusHandler] record.levelno =", record.levelno)
        if record.levelno >= logging.ERROR:
            error_counter.inc()

            login_data = getattr(record, "login", {})

            try:
                if isinstance(login_data, dict):
                    user_id = str(login_data.get("user_id", "unknown"))
                    login = login_data.get("login", "unknown")
                    role = login_data.get("role", "unknown")
                elif isinstance(login_data, str):
                    user_id = "system"
                    login = login_data
                    role = "system"
                else:
                    user_id = login = role = "unknown"

                error_counter_by_user.labels(
                    user_id=user_id,
                    login=login,
                    role=role
                ).inc()
            except Exception as e:
                print(f"[PrometheusHandler] Error recording metric: {e}")


def setup_logger(name: str = "ok_service", log_file: str = "ok_service.log") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = LokiFormatter("%(asctime)s %(levelname)s: %(message)s")

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not any(isinstance(h, PrometheusHandler) for h in logger.handlers):
        logger.addHandler(PrometheusHandler())

    return logger
