from uuid import UUID
from marshmallow import ValidationError


def validate_user_exists(user_id_str):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице UserModel по заданному user_id (UUID в строковом виде).
    """

    try:
        user_id = UUID(user_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc
    from app.database.managers.user_manager import UserManager
    db = UserManager()
    user = db.get_record_by_id(user_id)
    if not user:
        raise ValidationError(f"User with id={user_id} does not exist")
    return user_id_str  # или user_id, если вам нужно вернуть уже сконвертированный UUID


def validate_work_exists(work_id_str):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице WorkModel по заданному work_id (UUID в строковом виде).
    """
    try:
        work_id = UUID(work_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc
    from app.database.managers.works_managers import WorksManager
    db = WorksManager()
    work = db.get_record_by_id(work_id)
    if not work:
        raise ValidationError(f"Work with id={work_id} does not exist")
    return work_id_str  # или user_id, если вам нужно вернуть уже сконвертированный UUID


def validate_object_exists(object_id_str):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице objectModel по заданному object_id (UUID в строковом виде).
    """
    try:
        object_id = UUID(object_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc
    from app.database.managers.objects_managers import ObjectsManager
    db = ObjectsManager()
    object = db.get_record_by_id(object_id)
    if not object:
        raise ValidationError(f"object with id={object_id} does not exist")
    return object_id_str  # или user_id, если вам нужно вернуть уже сконвертированный UUID


def validate_project_exists(project_id_str):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице projectModel по заданному project_id (UUID в строковом виде).
    """
    try:
        project_id = UUID(project_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc
    from app.database.managers.projects_managers import ProjectsManager
    db = ProjectsManager()
    project = db.get_record_by_id(project_id)
    if not project:
        raise ValidationError(f"project with id={project_id} does not exist")
    return project_id_str  # или user_id, если вам нужно вернуть уже сконвертированный UUID


def validate_object_status_exists(object_status_id):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице object_statusModel по заданному object_status_id .
    """
    from app.database.managers.objects_managers import ObjectStatusesManager
    db = ObjectStatusesManager()
    object_status = db.get_record_by_id(object_status_id)
    if not object_status:
        raise ValidationError(f"""object_status with id={
                              object_status_id} does not exist""")
    # или user_id, если вам нужно вернуть уже сконвертированный UUID
    return object_status_id


def validate_role_exists(role_id):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице roleModel по заданному role_id .
    """
    from app.database.managers.roles_managers import RolesManager
    db = RolesManager()
    role = db.get_record_by_id(role_id)
    if not role:
        raise ValidationError(f"""role with id={
                              role_id} does not exist""")
    # или user_id, если вам нужно вернуть уже сконвертированный UUID
    return role_id


def validate_shift_report_exists(shift_report_id_str):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице shift_reportModel по заданному shift_report_id (UUID в строковом виде).
    """
    try:
        shift_report_id = UUID(shift_report_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc
    from app.database.managers.shift_reports_managers import ShiftReportsManager
    db = ShiftReportsManager()
    shift_report = db.get_record_by_id(shift_report_id)
    if not shift_report:
        raise ValidationError(f"""shift_report with id={
                              shift_report_id} does not exist""")
    # или user_id, если вам нужно вернуть уже сконвертированный UUID
    return shift_report_id_str


def validate_work_category_exists(work_category_id_str):
    """
    Валидатор, который проверяет, существует ли запись
    в таблице work_categoryModel по заданному work_category_id (UUID в строковом виде).
    """
    try:
        work_category_id = UUID(work_category_id_str)
    except ValueError as exc:
        raise ValidationError("Invalid UUID format") from exc
    from app.database.managers.works_managers import WorkCategoriesManager
    db = WorkCategoriesManager()
    work_category = db.get_record_by_id(work_category_id)
    if not work_category:
        raise ValidationError(f"""work_category with id={
                              work_category_id} does not exist""")
    # или user_id, если вам нужно вернуть уже сконвертированный UUID
    return work_category_id_str
