"""Dedicated process for durable Firebase push delivery (no Celery/Redis queue)."""

from __future__ import annotations

import logging
import os
import random
import signal
import socket
from collections import defaultdict
from threading import Event
from uuid import uuid4

from app.adapters.push_deliveries import ClaimedPushDelivery, SQLAlchemyPushDeliveryRepository
from app.adapters.push_notifications import build_push_provider
from app.domain.push_notifications import PushDelivery, PushDeliveryStatus, PushNotification, PushTarget
from app.use_cases.push_notifications import PushProviderConfigurationError

logger = logging.getLogger(__name__)


def retry_delay_ms(attempt: int, base_seconds: int, max_seconds: int) -> int:
    """Bounded exponential delay with jitter; attempt is already incremented."""
    if base_seconds < 1 or max_seconds < 1:
        raise ValueError("retry delays must be positive")
    nominal = min(max_seconds, base_seconds * (2 ** max(0, attempt - 1)))
    return max(1, min(max_seconds * 1000, int(nominal * random.uniform(0.5, 1.5) * 1000)))


class PushWorker:
    def __init__(self, app, provider=None, repository=None, worker_id: str | None = None):
        self.app = app
        self.provider = provider or build_push_provider(app.config)
        self.repository = repository or SQLAlchemyPushDeliveryRepository()
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid4()}"
        self.stop_requested = Event()

    def request_stop(self, *_args) -> None:
        self.stop_requested.set()

    def run_once(self) -> int:
        config = self.app.config
        claimed = self.repository.claim_ready(
            self.worker_id,
            int(config["PUSH_WORKER_BATCH_SIZE"]),
            int(config["PUSH_WORKER_LEASE_SECONDS"]) * 1000,
            int(config["PUSH_WORKER_MAX_ATTEMPTS"]),
        )
        if not claimed:
            return 0
        ready = []
        for delivery in claimed:
            if self.stop_requested.is_set():
                break
            if self.repository.is_eligible(delivery):
                ready.append(delivery)
            else:
                self.repository.mark_ineligible(delivery)
        for group in self._groups(ready):
            if self.stop_requested.is_set():
                break
            self._deliver_group(group)
        return len(claimed)

    @staticmethod
    def _groups(deliveries: list[ClaimedPushDelivery]):
        groups: dict[tuple[object, str, str, str], list[ClaimedPushDelivery]] = defaultdict(list)
        for delivery in deliveries:
            groups[(delivery.notification_id, delivery.title, delivery.body, delivery.route)].append(delivery)
        return groups.values()

    def _deliver_group(self, deliveries: list[ClaimedPushDelivery]) -> None:
        first = deliveries[0]
        notification = PushNotification(
            first.notification_id, first.title, first.body, first.route
        )
        try:
            results = self.provider.send(
                notification,
                [PushTarget(item.subscription_id, item.token) for item in deliveries],
            )
        except PushProviderConfigurationError:
            results = [
                PushDelivery(item.subscription_id, PushDeliveryStatus.CONFIGURATION_ERROR,
                             error_code="provider_configuration_error")
                for item in deliveries
            ]
        except Exception as exc:  # external adapter failure is retryable
            logger.warning("Push provider call failed: %s", type(exc).__name__)
            results = [
                PushDelivery(item.subscription_id, PushDeliveryStatus.TEMPORARY_FAILURE,
                             error_code=type(exc).__name__)
                for item in deliveries
            ]
        by_subscription = {result.subscription_id: result for result in results}
        for delivery in deliveries:
            result = by_subscription.get(delivery.subscription_id)
            if result is None:
                result = PushDelivery(
                    delivery.subscription_id,
                    PushDeliveryStatus.TEMPORARY_FAILURE,
                    error_code="provider_result_missing",
                )
            recorded = self.repository.record_result(
                delivery,
                result.status,
                provider_message_id=result.provider_message_id,
                error_code=result.error_code,
                max_attempts=int(self.app.config["PUSH_WORKER_MAX_ATTEMPTS"]),
                retry_delay_ms=retry_delay_ms(
                    delivery.attempts,
                    int(self.app.config["PUSH_WORKER_RETRY_BASE_SECONDS"]),
                    int(self.app.config["PUSH_WORKER_RETRY_MAX_SECONDS"]),
                ),
            )
            if not recorded:
                logger.warning("Push result discarded: lease is no longer valid")

    def run_forever(self) -> None:
        interval = float(self.app.config["PUSH_WORKER_POLL_INTERVAL_SECONDS"])
        while not self.stop_requested.is_set():
            count = self.run_once()
            if count == 0:
                self.stop_requested.wait(interval)


def main() -> None:
    from app import create_app

    config_name = os.getenv("CONFIG_NAME", "development")
    app = create_app(config_name, start_background_tasks=False)
    worker = PushWorker(app)
    signal.signal(signal.SIGTERM, worker.request_stop)
    signal.signal(signal.SIGINT, worker.request_stop)
    with app.app_context():
        worker.run_forever()


if __name__ == "__main__":
    main()
