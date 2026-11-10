from uuid import UUID, uuid4

import pytest

from app.domain.push_subscriptions import PushSubscription, PushSubscriptionValidationError
from app.use_cases.push_subscriptions import RegisterPushSubscription, RevokePushSubscription


class Repository:
    def list_for_user(self, user_id: UUID, offset: int, limit: int) -> list[PushSubscription]:
        return []

    def register(self, subscription):
        self.subscription = subscription
        return subscription

    def revoke(self, subscription_id, user_id, now):
        self.revoke_args = subscription_id, user_id, now
        return None


def test_register_and_revoke_pass_server_identity():
    repo = Repository()
    user, browser, auth_session = uuid4(), uuid4(), uuid4()
    result = RegisterPushSubscription(repo).execute(
        user, browser, auth_session, "web", "token"
    )
    assert (result.user_id, result.browser_id, result.auth_session_id, result.active, result.revoked_at) == (user, browser, auth_session, True, None)
    assert result.created_at == result.updated_at > 0
    assert RevokePushSubscription(repo).execute(result.subscription_id, user) is None
    assert repo.revoke_args[:2] == (result.subscription_id, user)


@pytest.mark.parametrize("platform,token", [("android", "token"), ("web", ""), ("web", " token"), ("web", "x" * 1025)])
def test_invalid_registration(platform, token):
    with pytest.raises(PushSubscriptionValidationError):
        RegisterPushSubscription(Repository()).execute(
            uuid4(), uuid4(), uuid4(), platform, token
        )
