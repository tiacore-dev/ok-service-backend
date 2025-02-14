import random
import pandas as pd


def put_users_in_db(admin_id):
    # Загружаем новый файл с таблицей
    file_path = "users.xlsx"

    # Читаем данные из Excel
    df_users_raw = pd.read_excel(file_path)

    # Преобразуем таблицу в нужный формат, переименовав столбцы
    df_users_raw.columns = ["ФИО", "Должность"]

    # Убираем пустые строки, если они есть
    df_users_cleaned = df_users_raw.dropna().reset_index(drop=True)

    # Генерируем логины, пароли и роли
    df_users_cleaned["Логин"] = df_users_cleaned["ФИО"].apply(generate_login)
    df_users_cleaned["Пароль"] = df_users_cleaned["ФИО"].apply(
        lambda x: generate_password())
    df_users_cleaned["Роль"] = df_users_cleaned["Должность"].apply(
        determine_role)
    df_users_cleaned["Категория"] = df_users_cleaned["Должность"].apply(
        extract_category)

    # Импортируем менеджер пользователей
    from app.database.managers.user_manager import UserManager

    user_manager = UserManager()
    created_by = admin_id
    # Добавляем пользователей в базу
    for _, row in df_users_cleaned.iterrows():
        user_manager.add_user(
            login=row["Логин"],
            password=row["Пароль"],
            name=row["ФИО"],
            role=row["Роль"],
            created_by=created_by,
            category=row["Категория"]
        )
    print("Пользователи успешно добавлены в базу данных!")
    # Сохраняем таблицу в Excel
    output_path = "processed_users.xlsx"
    df_users_cleaned.to_excel(output_path, index=False)


# Используем собственную функцию транслитерации


def transliterate(text):
    # Словарь соответствий кириллических символов латинице
    translit_table = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
        "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
        "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"
    }

    return "".join(translit_table.get(char, char) for char in text.lower())

# Функция для генерации логина с транслитерацией


def generate_login(full_name):
    parts = full_name.split()
    if len(parts) >= 2:
        login = f"{parts[1][0]}{parts[0]}"  # Первая буква имени + фамилия
    else:
        login = full_name  # Если что-то пошло не так, просто используем ФИО

    return transliterate(login)  # Транслитерация в латиницу

# Функция для генерации пароля


def generate_password():
    return "".join([str(random.randint(0, 9)) for _ in range(6)])

# Функция для определения роли


def determine_role(position):
    if "монтажник" in position.lower():
        return "user"
    elif "прораб" in position.lower():
        return "project-leader"
    elif "директор" in position.lower() or "зам" in position.lower():
        return "manager"
    return "user"


# Функция для извлечения категории (разряда) из должности
def extract_category(position):
    parts = position.split()
    # Проверяем, есть ли разряд в конце строки
    if len(parts) > 1 and parts[-1].isdigit():
        return parts[-1]
    return None  # Если разряда нет, возвращаем None
