from dataclasses import dataclass
from uuid import UUID

from app.use_cases.auth_sessions.ports import AuthSessionRepository
from app.use_cases.time_utils import utc_epoch_milliseconds


@dataclass(slots=True)
class LogoutAuthSession:
    repository: AuthSessionRepository

    def execute(self, session_id: UUID, user_id: UUID) -> bool:
        return self.repository.revoke_session(
            session_id, user_id, utc_epoch_milliseconds()
        )
