import time
import threading
from sqlalchemy import text
from config import Config

conf = Config()


def vacuum_database():
    from app.database.db_globals import engine
    """Фоновая задача для VACUUM ANALYZE"""
    while True:
        try:
            with engine.connect() as connection:  # Открываем чистое соединение
                connection = connection.execution_options(
                    isolation_level="AUTOCOMMIT")  # ✅ Отключаем транзакцию
                connection.execute(text("VACUUM ANALYZE;")
                                   )  # ✅ Теперь сработает
                connection.execute(
                    text(f"REINDEX DATABASE {conf.DATABASE_NAME};"))
                print("[INFO] VACUUM выполнен")
        except Exception as e:
            print(f"[ERROR] Ошибка при VACUUM: {e}")
        time.sleep(86400)  # Раз в сутки
        # time.sleep(10)  # Раз в сутки

# Запуск в фоне через поток


def start_background_task():
    thread = threading.Thread(target=vacuum_database, daemon=True)
    thread.start()
