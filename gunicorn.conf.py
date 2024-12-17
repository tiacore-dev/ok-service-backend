import os
from dotenv import load_dotenv
from multiprocessing import cpu_count

load_dotenv()

port = os.getenv('FLASK_PORT', '8000')  # Убедитесь, что порт задан с безопасным значением по умолчанию

bind = f"0.0.0.0:{port}"
workers = cpu_count() * 2 + 1  # Динамическое определение количества воркеров
timeout = 600  # Увеличенное время ожидания

# Логи
loglevel = "info"
errorlog = "-"  # Логи ошибок выводятся в stderr
accesslog = "-"  # Логи доступа выводятся в stdout
capture_output = True  # Перехватывать вывод stdout/stderr из приложения

# Добавляем флаг для предзагрузки приложения
preload_app = True
