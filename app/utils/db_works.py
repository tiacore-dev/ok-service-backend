import pandas as pd


def put_to_db(data, admin_id):
    from app.database.managers.works_managers import WorksManager, WorkCategoriesManager, WorkPricesManager
    work_manager = WorksManager()
    category_manager = WorkCategoriesManager()
    price_manager = WorkPricesManager()
    for work in data:
        if not category_manager.exists(name=work['work_category']):
            category = category_manager.add(
                name=work['work_category'], created_by=admin_id)
        else:
            category = category_manager.filter_one_by_dict(
                name=work['work_category'])
        work_added = work_manager.add(
            name=work['work'], created_by=admin_id, category=category['work_category_id'], measurement_unit='шт.')
        for i in range(1, 5):
            price = work.get(f'price_{i}')  # Берем цену

            if price is not None:  # Добавляем только если цена есть
                price_manager.add(work=work_added['work_id'], created_by=admin_id,
                                  category=i, price=price)


def put_works_in_db(admin_id):
    # 1. Загружаем Excel-файл
    print(admin_id)
    file_path = "works.xlsx"
    xls = pd.ExcelFile(file_path)

    # 2. Проверяем, какие листы есть в файле
    print("Доступные листы:", xls.sheet_names)

    # 3. Загружаем данные с нужного листа
    df = pd.read_excel(xls, sheet_name='Расценки СМР монтаж')

    # 4. Убираем лишние пробелы из названий колонок
    df.columns = df.columns.str.strip()

    # 5. Переименовываем столбцы для удобства
    df = df.rename(columns={
        "Наименование оборудования": "work_category",
        "Unnamed: 1": "work",
        "1 разряд": "price_1",
        "2 разряд": "price_2",
        "3 разряд": "price_3",
        "4 разряд": "price_4",
    })

    # 6. Удаляем строки, где нет названия работы
    df = df.dropna(subset=["work_category"])

    # 7. Преобразуем в словарь перед вставкой в базу
    work_prices_data = df.to_dict(orient="records")

    # 8. Выводим первые 10 записей
    print(work_prices_data[:10])  # Теперь правильно!

    put_to_db(work_prices_data, admin_id)
