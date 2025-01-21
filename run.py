from app import create_app
import os
from dotenv import load_dotenv

load_dotenv()

# Получаем порт из переменных окружения
port = os.getenv('FLASK_PORT', '5000')

# Создаем приложение
app = create_app(config_name="development")


# Запуск через Gunicorn будет автоматически управлять процессом запуска
if __name__ == '__main__':
    app.run(debug=True, port=port)
