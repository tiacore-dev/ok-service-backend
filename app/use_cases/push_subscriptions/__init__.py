from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.push_subscriptions import PushSubscription, PushSubscriptionValidationError
from app.use_cases.time_utils import utc_epoch_milliseconds


class PushSubscriptionRepository(Protocol):
    def register(self, subscription: PushSubscription) -> PushSubscription: ...
    def revoke(self, subscription_id: UUID, user_id: UUID, now: int) -> PushSubscription | None: ...
    def list_for_user(self, user_id: UUID, offset: int, limit: int) -> list[PushSubscription]: ...


@dataclass(slots=True)
class ListPushSubscriptions:
    repository: PushSubscriptionRepository

    def execute(self, user_id: UUID, offset: int, limit: int) -> list[PushSubscription]:
        if offset < 0 or not 1 <= limit <= 100:
            raise PushSubscriptionValidationError("Invalid pagination")
        return self.repository.list_for_user(user_id, offset, limit)


@dataclass(slots=True)
class RegisterPushSubscription:
    repository: PushSubscriptionRepository

    def execute(
        self,
        user_id: UUID,
        browser_id: UUID,
        auth_session_id: UUID,
        platform: str,
        token: str,
    ) -> PushSubscription:
        if platform != "web":
            raise PushSubscriptionValidationError("Only web platform is supported")
        if not token or token != token.strip() or len(token.encode("utf-8")) > 1024:
            raise PushSubscriptionValidationError("Invalid FCM token")
        now = utc_epoch_milliseconds()
        return self.repository.register(
            PushSubscription(
                uuid4(), user_id, browser_id, auth_session_id, platform, token,
                True, now, now, None,
            )
        )


@dataclass(slots=True)
class RevokePushSubscription:
    repository: PushSubscriptionRepository

    def execute(self, subscription_id: UUID, current_user_id: UUID) -> PushSubscription | None:
        return self.repository.revoke(subscription_id, current_user_id, utc_epoch_milliseconds())
