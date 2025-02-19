import logging
import uuid
from uuid import UUID
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, asc, desc
from app.database.models import Projects, ProjectSchedules, ProjectWorks, Objects
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager

logger = logging.getLogger('ok_service')

EXACT_MATCH_FIELDS = {"status"}


class ProjectsManager(BaseDBManager):

    @property
    def model(self):
        return Projects

    def get_all_filtered_with_status(self, user, offset=0, limit=None, sort_by=None, sort_order='asc', **filters):
        logger.debug("get_all_filtered_with_status вызывается с фильтрацией, сортировкой и проверкой статуса объекта.",
                     extra={"login": "database"})

        with self.session_scope() as session:
            query = session.query(self.model).options(joinedload(
                Projects.objects))  # Используем joinload для оптимизации

            # Если пользователь — обычный "user", фильтруем проекты по статусу объекта
            if user['role'] == "user":
                query = query.join(Objects, Projects.object == Objects.object_id).filter(
                    Objects.status == "active")
                logger.debug("Фильтрация: только проекты с объектами в статусе 'active'.",
                             extra={"login": "database"})
            # Применяем стандартные фильтры из filters
            filter_conditions = []
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    column = getattr(self.model, key)

                    # Проверяем, является ли значение UUID (обычно 36 символов)
                    if isinstance(value, uuid.UUID) or (isinstance(value, str) and len(value) == 36 and '-' in value):
                        filter_conditions.append(column == value)
                        logger.debug(f"Применяем точный UUID-фильтр: {key} = {value}",
                                     extra={'login': 'database'})

                    # Поля, требующие точного сравнения
                    elif key in EXACT_MATCH_FIELDS:
                        filter_conditions.append(column == value)
                        logger.debug(f"Применяем точный фильтр для {key}: {key} = {value}",
                                     extra={'login': 'database'})

                    elif isinstance(value, str):
                        value = value.strip()  # Убираем лишние пробелы

                        if "%" not in value:
                            # Добавляем wildcard для частичного поиска
                            value = f"%{value}%"

                        filter_conditions.append(column.ilike(value))
                        logger.debug(f"Применяем ILIKE-фильтр: {key} LIKE {value}",
                                     extra={'login': 'database'})

                    else:
                        filter_conditions.append(column == value)
                        logger.debug(f"Применяем фильтр: {key} = {value}",
                                     extra={'login': 'database'})

            # Добавляем фильтры в запрос
            if filter_conditions:
                query = query.filter(and_(*filter_conditions))

            # Применяем сортировку
            if sort_by and hasattr(self.model, sort_by):
                order = desc if sort_order == 'desc' else asc
                query = query.order_by(order(getattr(self.model, sort_by)))
                logger.debug(f"Применяем сортировку: {sort_by} {sort_order}",
                             extra={"login": "database"})

            # Применяем пагинацию
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            records = query.all()
            logger.debug(f"Найдено записей: {len(records)}",
                         extra={"login": "database"})

            return [record.to_dict() for record in records]


class ProjectSchedulesManager(BaseDBManager):

    @property
    def model(self):
        return ProjectSchedules

    def get_schedule_ids_by_project_leader(self, user_id):
        """
        Возвращает ID всех ProjectWorks, где пользователь является project_leader.
        """
        with self.session_scope() as session:
            schedule_ids = session.query(ProjectSchedules.project_schedule_id).join(
                Projects, ProjectSchedules.project == Projects.project_id
            ).filter(
                Projects.project_leader == UUID(user_id)
            ).all()

            # ✅ Достаём первый элемент из tuple
            result = [str(schedule_id[0]) for schedule_id in schedule_ids]
            logger.debug(f"Найдено {len(result)} работ для project_leader={user_id}",
                         extra={"login": "database"})
            return result


class ProjectWorksManager(BaseDBManager):

    @property
    def model(self):
        return ProjectWorks

    def get_work_ids_by_project_leader(self, user_id):
        """
        Возвращает ID всех ProjectWorks, где пользователь является project_leader.
        """
        with self.session_scope() as session:
            work_ids = session.query(ProjectWorks.project_work_id).join(
                Projects, ProjectWorks.project == Projects.project_id
            ).filter(
                Projects.project_leader == UUID(user_id)
            ).all()

            # ✅ Достаём первый элемент из tuple
            result = [str(work_id[0]) for work_id in work_ids]
            logger.debug(f"Найдено {len(result)} работ для project_leader={user_id}",
                         extra={"login": "database"})
            return result

    def get_manager(self, project):
        """Получение ID менеджера проекта по project_work_id"""
        try:
            logger.debug(f"Получение manager ID для project_work_id: {project}", extra={
                         "login": "database"})

            with self.session_scope() as session:
                project_work = session.query(self.model).options(
                    joinedload(self.model.projects).joinedload(
                        Projects.objects)
                ).filter(self.model.project == project).first()

                if not project_work or not project_work.projects or not project_work.projects.objects:
                    logger.warning(
                        f"ProjectWork с ID {project} или его проект/объект не найден", extra={"login": "database"})
                    return None

                manager_id = project_work.projects.objects.manager
                if not manager_id:
                    logger.warning(f"У объекта проекта ProjectWork нет менеджера", extra={
                                   "login": "database"})
                    return None

                logger.info(f"Найден manager ID {manager_id} для project_work_id", extra={
                            "login": "database"})
                return str(manager_id)  # Приводим UUID к строке

        except Exception as e:
            logger.error(f"Ошибка при получении manager ID: {e}", extra={
                         "login": "database"})
            raise

    def get_project_leader(self, project_work_id):
        """Получение ID руководителя проекта по project_work_id"""
        try:
            logger.debug(f"Получение project_leader ID для project_work_id: {project_work_id}", extra={
                         "login": "database"})

            with self.session_scope() as session:
                project_work = session.query(self.model).options(
                    joinedload(self.model.projects)
                ).filter(self.model.project_work_id == project_work_id).first()

                if not project_work or not project_work.projects:
                    logger.warning(f"ProjectWork с ID {project_work_id} или его проект не найден", extra={
                                   "login": "database"})
                    return None

                project_leader = project_work.projects.project_leader
                if not project_leader:
                    logger.warning(f"У проекта ProjectWork {project_work_id} нет руководителя", extra={
                                   "login": "database"})
                    return None

                logger.info(f"Найден project_leader ID {project_leader} для project_work_id {project_work_id}", extra={
                            "login": "database"})
                return str(project_leader)  # Приводим UUID к строке

        except Exception as e:
            logger.error(f"Ошибка при получении project_leader ID: {e}", extra={
                         "login": "database"})
            raise
