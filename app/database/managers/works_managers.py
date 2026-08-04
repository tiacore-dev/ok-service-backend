import logging
from sqlalchemy.orm import joinedload
from sqlalchemy import asc, desc
from app.database.models import Works, WorkPrices, WorkCategories, MeasurementUnits
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager

logger = logging.getLogger('ok_service')


class WorksManager(BaseDBManager):

    @property
    def model(self):
        return Works

    def get_all_filtered(self, offset=0, limit=None, sort_by=None, sort_order='asc', **filters):
        logger.debug("get_all_filtered вызывается с фильтрацией, сортировкой и пагинацией.",
                     extra={"login": "database"})

        with self.session_scope() as session:
            query = session.query(self.model).options(
                joinedload(self.model.work_category),  # 🔥 Категория
                joinedload(self.model.work_price)      # 🔥 Прайсы
            )

            # Применяем фильтры
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    column = getattr(self.model, key)
                    query = query.filter(column == value)
                    logger.debug(f"Применяем фильтр: {key} = {value}",
                                 extra={'login': 'database'})

            # Применяем сортировку
            if sort_by and hasattr(self.model, sort_by):
                order = desc if sort_order == 'desc' else asc  # Выбор функции сортировки
                query = query.order_by(order(getattr(self.model, sort_by)))
                logger.debug(f"Применяем сортировку: {sort_by} {sort_order}",
                             extra={"login": "database"})

            # Применяем пагинацию
            if offset:
                query = query.offset(offset)
                logger.debug(f"Применяем смещение: offset = {offset}",
                             extra={"login": "database"})
            if limit:
                query = query.limit(limit)
                logger.debug(f"Применяем лимит: limit = {limit}",
                             extra={"login": "database"})

            # Получаем записи
            records = query.all()
            logger.debug(f"Найдено записей: {len(records)}",
                         extra={"login": "database"})

            # Преобразуем записи в словари
            return [record.to_dict() for record in records]


class WorkPricesManager(BaseDBManager):

    @property
    def model(self):
        return WorkPrices


class WorkCategoriesManager(BaseDBManager):

    @property
    def model(self):
        return WorkCategories


class MeasurementUnitsManager(BaseDBManager):

    @property
    def model(self):
        return MeasurementUnits
