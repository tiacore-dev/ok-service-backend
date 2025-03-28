from dotenv import load_dotenv
from app import create_app


load_dotenv()

# Получаем порт из переменных окружения
port = 8000

# Создаем приложение
app = create_app(config_name="development")


# Запуск через Gunicorn будет автоматически управлять процессом запуска
if __name__ == '__main__':
    app.run(debug=True, port=port)
