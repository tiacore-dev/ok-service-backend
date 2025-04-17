from uuid import UUID
from marshmallow import ValidationError


def validate_user_exists(user_id_str):
    """
    Проверяет, существует ли user_id в таблице UserModel.
    """
    if not user_id_str:  # Если None или пустая строка, пропускаем
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc

    from app.database.managers.user_manager import UserManager
    db = UserManager()
    user = db.get_record_by_id(user_id)
    if not user:
        raise ValidationError(f"User with id={user_id} does not exist")

    return user_id_str  # Или user_id, если нужен UUID


def validate_object_exists(object_id_str):
    """
    Проверяет, существует ли object_id в таблице objectModel.
    """
    if not object_id_str:  # Если None или пустая строка, пропускаем
        return None

    try:
        object_id = UUID(object_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc

    from app.database.managers.objects_managers import ObjectsManager
    db = ObjectsManager()
    obj = db.get_record_by_id(object_id)
    if not obj:
        raise ValidationError(f"Object with id={object_id} does not exist")

    return object_id_str  # Или object_id, если нужен UUID


def validate_work_exists(work_id_str):
    """ Проверяет, существует ли запись в WorkModel по work_id (UUID). """
    if not work_id_str:
        return None

    try:
        work_id = UUID(work_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc

    from app.database.managers.works_managers import WorksManager
    db = WorksManager()
    work = db.get_record_by_id(work_id)
    if not work:
        raise ValidationError(f"Work with id={work_id} does not exist")

    return work_id_str


def validate_project_exists(project_id_str):
    """ Проверяет, существует ли запись в projectModel по project_id (UUID). """
    if not project_id_str:
        return None

    try:
        project_id = UUID(project_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc

    from app.database.managers.projects_managers import ProjectsManager
    db = ProjectsManager()
    project = db.get_record_by_id(project_id)
    if not project:
        raise ValidationError(f"Project with id={project_id} does not exist")

    return project_id_str


def validate_project_work_exists(project_work_id_str):
    """ Проверяет, существует ли запись в projectModel по project_id (UUID). """
    if not project_work_id_str:
        return None

    try:
        project_work_id = UUID(project_work_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc

    from app.database.managers.projects_managers import ProjectWorksManager
    db = ProjectWorksManager()
    project_work = db.get_record_by_id(project_work_id)
    if not project_work:
        raise ValidationError(
            f"Project Work with id={project_work_id} does not exist")

    return project_work_id_str


def validate_object_status_exists(object_status_id):
    """ Проверяет, существует ли запись в object_statusModel по object_status_id. """
    if not object_status_id:
        return None

    from app.database.managers.objects_managers import ObjectStatusesManager
    db = ObjectStatusesManager()
    object_status = db.get_record_by_id(object_status_id)
    if not object_status:
        raise ValidationError(
            f"Object status with id={object_status_id} does not exist")

    return object_status_id


def validate_role_exists(role_id):
    """ Проверяет, существует ли запись в roleModel по role_id. """
    if not role_id:
        return None

    from app.database.managers.roles_managers import RolesManager
    db = RolesManager()
    role = db.get_record_by_id(role_id)
    if not role:
        raise ValidationError(f"Role with id={role_id} does not exist")

    return role_id


def validate_shift_report_exists(shift_report_id_str):
    """ Проверяет, существует ли запись в shift_reportModel по shift_report_id (UUID). """
    if not shift_report_id_str:
        return None

    try:
        shift_report_id = UUID(shift_report_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc

    from app.database.managers.shift_reports_managers import ShiftReportsManager
    db = ShiftReportsManager()
    shift_report = db.get_record_by_id(shift_report_id)
    if not shift_report:
        raise ValidationError(
            f"Shift report with id={shift_report_id} does not exist")

    return shift_report_id_str


def validate_work_category_exists(work_category_id_str):
    """ Проверяет, существует ли запись в work_categoryModel по work_category_id (UUID). """
    if not work_category_id_str:
        return None

    try:
        work_category_id = UUID(work_category_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc

    from app.database.managers.works_managers import WorkCategoriesManager
    db = WorkCategoriesManager()
    work_category = db.get_record_by_id(work_category_id)
    if not work_category:
        raise ValidationError(
            f"Work category with id={work_category_id} does not exist")

    return work_category_id_str
