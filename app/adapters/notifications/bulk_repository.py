from sqlalchemy import select

from app.adapters.notifications.sqlalchemy_repository import SQLAlchemyNotificationRepository
from app.database.models import Users
from app.use_cases.notifications.bulk import BulkForbiddenError, BulkRecipientsError


class BulkNotificationRepository(SQLAlchemyNotificationRepository):
    def __init__(self, actor_id):
        super().__init__()
        self.actor_id = actor_id

    def _validate_creation(self, session, recipient_user_ids):
        ids = set(recipient_user_ids) | {self.actor_id}
        users = session.scalars(
            select(Users).where(Users.user_id.in_(ids)).order_by(Users.user_id).with_for_update()
        ).all()
        by_id = {user.user_id: user for user in users}
        actor = by_id.get(self.actor_id)
        if actor is None or actor.deleted or not actor.is_active or actor.role != "admin":
            raise BulkForbiddenError()
        if any(uid not in by_id or by_id[uid].deleted or not by_id[uid].is_active
               for uid in recipient_user_ids):
            raise BulkRecipientsError()
