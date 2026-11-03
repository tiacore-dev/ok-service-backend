from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app.adapters.push_deliveries import ClaimedPushDelivery
from app.domain.push_notifications import PushDelivery, PushDeliveryStatus
from app.push_worker import PushWorker, retry_delay_ms


def _delivery(*, attempts=1):
    return ClaimedPushDelivery(
        uuid4(), uuid4(), uuid4(), "not-logged-token", "Title", "Body",
        "/notifications/1", uuid4(), attempts,
    )


class _Repository:
    def __init__(self, claimed):
        self.claimed = claimed
        self.ineligible = []
        self.ineligible_set = set()
        self.results = []

    def claim_ready(self, _worker, batch_size, *_args):
        assert batch_size == 1
        result, self.claimed = self.claimed[:batch_size], self.claimed[batch_size:]
        return result

    def is_eligible(self, delivery):
        return delivery not in self.ineligible_set

    def mark_ineligible(self, delivery):
        self.ineligible.append(delivery)
        return True

    def record_result(self, delivery, status, **kwargs) -> bool:
        self.results.append((delivery, status, kwargs))
        return True


class _Provider:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def send(self, notification, targets):
        self.calls.append((notification, targets))
        ids = {target.subscription_id for target in targets}
        return [item for item in self.results if item.subscription_id in ids]


def _app():
    return SimpleNamespace(config={
        "PUSH_WORKER_BATCH_SIZE": 10,
        "PUSH_WORKER_LEASE_SECONDS": 60,
        "PUSH_WORKER_MAX_ATTEMPTS": 3,
        "PUSH_WORKER_RETRY_BASE_SECONDS": 2,
        "PUSH_WORKER_RETRY_MAX_SECONDS": 30,
        "PUSH_WORKER_POLL_INTERVAL_SECONDS": 0.01,
    })


def test_worker_records_partial_results_per_delivery_without_logging_tokens():
    first, second = _delivery(), _delivery()
    # Deliveries for the same notification are still claimed independently.
    second = ClaimedPushDelivery(
        second.delivery_id, first.notification_id, second.subscription_id,
        second.token, first.title, first.body, first.route, second.lease_token,
        second.attempts,
    )
    repo = _Repository([first, second])
    provider = _Provider([
        PushDelivery(first.subscription_id, PushDeliveryStatus.SENT, "firebase-id"),
        PushDelivery(second.subscription_id, PushDeliveryStatus.INVALID_TOKEN, error_code="UnregisteredError"),
    ])

    assert PushWorker(_app(), provider, repo, "test-worker").run_once() == 2

    assert len(provider.calls) == 2
    assert [(item[1], item[2]["provider_message_id"]) for item in repo.results] == [
        (PushDeliveryStatus.SENT, "firebase-id"),
        (PushDeliveryStatus.INVALID_TOKEN, None),
    ]
    assert repo.results[1][2]["error_code"] == "UnregisteredError"


def test_worker_does_not_send_revoked_subscription_after_claim():
    delivery = _delivery()
    repo = _Repository([delivery])
    repo.ineligible_set.add(delivery)
    provider = _Provider([])

    PushWorker(_app(), provider, repo).run_once()

    assert provider.calls == []
    assert repo.ineligible == [delivery]
    assert repo.results == []


def test_eligibility_database_error_never_calls_provider_or_marks_ineligible():
    delivery = _delivery()
    class BrokenRepository(_Repository):
        def is_eligible(self, _delivery):
            raise OperationalError('select', {}, Exception('unavailable'))

    repo = BrokenRepository([delivery])
    provider = _Provider([])
    with pytest.raises(OperationalError):
        PushWorker(_app(), provider, repo).run_once()
    assert provider.calls == []
    assert repo.ineligible == []
    assert repo.results == []


def test_worker_loop_recovers_after_database_error():
    worker = PushWorker(_app(), _Provider([]), _Repository([]))
    calls = []
    def run_once():
        calls.append(1)
        if len(calls) == 1:
            raise OperationalError('select', {}, Exception('unavailable'))
        worker.request_stop()
        return 0
    worker.run_once = run_once
    worker.run_forever()
    assert len(calls) == 2


def test_graceful_stop_does_not_claim_new_work():
    delivery = _delivery()
    repo = _Repository([delivery])
    provider = _Provider([])
    worker = PushWorker(_app(), provider, repo)
    worker.request_stop()

    assert worker.run_once() == 0
    assert provider.calls == []
    assert repo.results == []


def test_retry_delay_is_bounded_and_grows_before_cap(monkeypatch):
    monkeypatch.setattr("app.push_worker.random.uniform", lambda _a, _b: 1.0)
    assert retry_delay_ms(1, 2, 30) == 2_000
    assert retry_delay_ms(3, 2, 30) == 8_000
    assert retry_delay_ms(20, 2, 30) == 30_000
    with pytest.raises(ValueError):
        retry_delay_ms(1, 2, 0)
    monkeypatch.setattr("app.push_worker.random.uniform", lambda _a, _b: 0.5)
    assert retry_delay_ms(1, 2, 30) == 1_000
    assert retry_delay_ms(20, 2, 30) == 15_000
    monkeypatch.setattr("app.push_worker.random.uniform", lambda _a, _b: 1.5)
    assert retry_delay_ms(1, 2, 30) == 3_000
    assert retry_delay_ms(20, 2, 30) == 30_000


def test_worker_reports_rejected_result_without_token(caplog):
    delivery = _delivery()
    assert delivery.token not in repr(delivery)
    class RejectingRepository(_Repository):
        def record_result(self, delivery, status, **kwargs) -> bool:
            return False

    repo = RejectingRepository([delivery])
    provider = _Provider([PushDelivery(delivery.subscription_id, PushDeliveryStatus.INVALID_TOKEN)])
    assert PushWorker(_app(), provider, repo).run_once() == 1
    assert "lease is no longer valid" in caplog.text
    assert delivery.token not in caplog.text
