import logging

# Настройка логгера


def setup_logger():
    logger = logging.getLogger('ok_service')  # Используем именованный логгер
    logger.setLevel(logging.DEBUG)

    # Проверяем, был ли уже настроен логгер
    if not logger.handlers:
        # Добавляем обработчик для вывода логов в консоль
        console_handler = logging.StreamHandler()
        log_format = """%(asctime)s %(levelname)s: %(message)s
                    [in %(pathname)s:%(lineno)d]"""
        console_formatter = logging.Formatter(log_format)

        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Добавляем обработчик для записи логов в базу данных
        logger.addHandler(DatabaseLogHandler())

    return logger


class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        from app.database.managers.logs_manager import LogManager

        log_entry = self.format(record)
        db = LogManager()

        # Извлекаем user_id из дополнительных данных
        # Если user_id не установлен, использовать 'unknown'
        login = getattr(record, 'login', 'unknown')

        try:
            # Записываем лог в базу данных
            db.add_logs(login=login, action=record.levelname,
                        message=log_entry)
        except Exception as e:
            print(f"Ошибка при записи лога в базу данных: {e}")
