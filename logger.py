import logging
import os
from prometheus_client import Counter

error_counter = Counter('flask_errors_total', 'Total number of errors')
# Настройка логгера


def setup_logger():
    logger = logging.getLogger('ok_service')  # Используем именованный логгер
    logger.setLevel(logging.DEBUG)

    # Проверяем, был ли уже настроен логгер
    if not logger.handlers:
        # Добавляем обработчик для вывода логов в консоль
        console_handler = logging.StreamHandler()
        log_format = "%(asctime)s %(levelname)s: %(message)s"
        log_formatter = logging.Formatter(log_format)

        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

        # Добавляем обработчик для записи логов в файл
        log_file_path = os.path.join(os.getcwd(), "ok_service.log")
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

    def error_counter_handler(record):
        if record.levelno >= logging.ERROR:
            error_counter.inc()

    class PrometheusHandler(logging.Handler):
        def emit(self, record):
            error_counter_handler(record)

    logger.addHandler(PrometheusHandler())

    return logger
