import os
from dotenv import load_dotenv
from multiprocessing import cpu_count

load_dotenv()

# Убедитесь, что порт задан с безопасным значением по умолчанию
port = os.getenv('FLASK_PORT', '8000')

# Количество CPU
cpu_cores = cpu_count()

bind = f"0.0.0.0:{port}"
workers = max(2, min(4, cpu_cores // 2))  # Баланс между ядрами и воркерами
timeout = 600  # Увеличенное время ожидания
threads = 4  # Увеличьте до 4 потоков на воркер

# Логи
loglevel = "info"
errorlog = "-"  # Логи ошибок выводятся в stderr
accesslog = "-"  # Логи доступа выводятся в stdout
capture_output = True  # Перехватывать вывод stdout/stderr из приложения

# Добавляем флаг для предзагрузки приложения
preload_app = True
