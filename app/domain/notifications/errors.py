class NotificationRecipientsRequiredError(ValueError):
    """A notification must have at least one recipient."""


class NotificationIdempotencyConflictError(Exception):
    """An idempotency key was already used with different input."""


class NotificationQueryValidationError(ValueError):
    """Notification pagination arguments are outside the supported range."""


class NotificationValidationError(ValueError):
    """Notification content violates application-level field constraints."""
