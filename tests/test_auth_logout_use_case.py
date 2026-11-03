from uuid import uuid4

from app.use_cases.auth_sessions import LogoutAuthSession
from app.use_cases.auth_sessions.ports import AuthSessionRevoker


class Repository(AuthSessionRevoker):
    def revoke_session(self, session_id, user_id, revoked_at):
        self.args = session_id, user_id, revoked_at
        return True


def test_logout_uses_trusted_session_and_user_identity():
    repository = Repository()
    session_id, user_id = uuid4(), uuid4()

    assert LogoutAuthSession(repository).execute(session_id, user_id)
    assert repository.args[:2] == (session_id, user_id)
    assert repository.args[2] > 0
