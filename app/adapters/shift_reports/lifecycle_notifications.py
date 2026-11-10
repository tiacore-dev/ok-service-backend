"""Create shift lifecycle notifications in the caller's transaction."""
from app.adapters.notifications.sqlalchemy_repository import SQLAlchemyNotificationRepository
from app.database.models import Projects
from app.use_cases.notifications import CreateNotificationCommand, CreateNotificationUseCase

_CONTENT = {
    "created": ("Назначена смена", "Вам назначена смена №{number}."),
    "approved": ("Смена согласована", "Смена №{number} согласована."),
    "opened": ("Смена открыта", "Смена №{number} открыта."),
    "closed": ("Смена закрыта", "Смена №{number} закрыта."),
}


def notify_shift_event(session, report, event, actor_id, occurrence_id):
    if event in ("created", "approved"):
        recipient = report.user
    else:
        recipient = session.query(Projects.project_leader).filter(
            Projects.project_id == report.project
        ).scalar()
    # The notification use case requires at least one recipient. An unassigned
    # specification has no notification or delivery records, and no fallback.
    if recipient is None:
        return
    title, text = _CONTENT[event]
    CreateNotificationUseCase(SQLAlchemyNotificationRepository(session)).execute(
        CreateNotificationCommand(
            idempotency_key=f"shift_report.{event}:{occurrence_id}",
            notification_type=f"shift_report.{event}",
            title=title,
            text=text.format(number=report.number),
            recipient_user_ids=(recipient,),
            created_by=actor_id,
            related_entity_type="shift_report",
            related_entity_id=str(report.shift_report_id),
        )
    )
