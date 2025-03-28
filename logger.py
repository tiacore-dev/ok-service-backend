import logging
import os
from prometheus_client import Counter

# Общий счётчик ошибок
error_counter = Counter(
    'flask_errors_total',
    'Total number of errors'
)

# Счётчик ошибок по пользователям
error_counter_by_user = Counter(
    'flask_errors_total_by_user',
    'Total number of errors per user',
    ['user_id', 'login', 'role']
)


class PrometheusHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            self._count_general_error()
            self._count_user_error(record)

    def _count_general_error(self):
        error_counter.inc()

    def _count_user_error(self, record):
        try:
            login_data = getattr(record, "login", {})

            if isinstance(login_data, dict):
                user_id = str(login_data.get("user_id", "unknown"))
                login = login_data.get("login", "unknown")
                role = login_data.get("role", "unknown")
            elif isinstance(login_data, str):
                # Для простого случая: логин — строка, типа "database"
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
            print(f"Failed to record Prometheus metric: {e}")


def setup_logger(name: str = "ok_service", log_file: str = "ok_service.log") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

        # Консоль
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Файл
        log_path = os.path.join(os.getcwd(), log_file)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Prometheus
        logger.addHandler(PrometheusHandler())

    return logger
