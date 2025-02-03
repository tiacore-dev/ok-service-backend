import logging
import os

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

    return logger
