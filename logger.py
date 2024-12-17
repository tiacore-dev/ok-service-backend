import logging

# Настройка логгера
def setup_logger():
    logger = logging.getLogger('ok_service')  # Используем именованный логгер
    logger.setLevel(logging.DEBUG)

    # Проверяем, был ли уже настроен логгер (чтобы не добавлять обработчики повторно)
    if not logger.handlers:
        # Добавляем обработчик для вывода логов в консоль
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)


    return logger

