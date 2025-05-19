import os
from dotenv import load_dotenv
from app import create_app


load_dotenv()

# Получаем порт из переменных окружения
port = 8000

# Создаем приложение
config_name = os.getenv('CONFIG_NAME', "development")
app = create_app(config_name)


# Запуск через Gunicorn будет автоматически управлять процессом запуска
if __name__ == '__main__':
    app.run(debug=True, port=port)
