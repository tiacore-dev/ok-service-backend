import pandas as pd


def put_users_in_db(admin_id):
    # Загружаем новый файл с таблицей
    file_path = "processed_users.xlsx"

    # Читаем данные из Excel
    df_users = pd.read_excel(file_path)
    print(df_users.head())  # Посмотрим первые строки
    # Импортируем менеджер пользователей
    from app.database.managers.user_manager import UserManager

    user_manager = UserManager()
    created_by = admin_id
    # Добавляем пользователей в базу
    for _, row in df_users.iterrows():
        user_manager.add_user(
            login=row["Логин"],
            password=str(row["Пароль"]),
            name=row["ФИО"],
            role=row["Роль"],
            created_by=created_by,
            category=int(row["Категория"]) if pd.notna(
                row["Категория"]) else None  # Явная проверка
        )

    print("Пользователи успешно добавлены в базу данных!")
    # Сохраняем таблицу в Exceд
