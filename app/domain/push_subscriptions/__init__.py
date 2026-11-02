from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PushSubscription:
    subscription_id: UUID
    user_id: UUID
    browser_id: UUID
    platform: str
    token: str
    active: bool
    created_at: int
    updated_at: int
    revoked_at: int | None


class PushSubscriptionValidationError(ValueError):
    """Invalid subscription data."""
