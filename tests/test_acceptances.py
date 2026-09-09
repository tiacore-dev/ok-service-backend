from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.acceptances import Acceptance, AcceptanceForbiddenError, AcceptanceStatus
from app.database.managers.materials_manager import AcceptancesManager
from app.database.models import Acceptances, Objects
from app.domain.work_acceptance_relations import (
    WorkAcceptanceRelation,
    WorkAcceptanceRelationValidationError,
)
from app.use_cases.acceptances import (
    AcceptanceActor,
    CreateAcceptanceCommand,
    CreateAcceptanceUseCase,
    UpdateAcceptanceCommand,
    UpdateAcceptanceUseCase,
)


def test_acceptance_status_and_timestamp_are_normalized():
    item = Acceptance(uuid4(), 1720000000000, uuid4(), AcceptanceStatus.PRESENTED)
    assert item.status is AcceptanceStatus.PRESENTED
    assert item.date == 1720000000000


def test_work_acceptance_relation_requires_positive_quantity():
    with pytest.raises(WorkAcceptanceRelationValidationError):
        WorkAcceptanceRelation(uuid4(), uuid4(), uuid4(), Decimal("0"))


def test_acceptance_mutation_is_allowed_for_manager():
    class Repository:
        def create_acceptance(self, acceptance):
            return acceptance

        def get_project_object_status(self, project_id): return "active"

        def get_acceptance(self, acceptance_id): return None
        def update_acceptance(self, acceptance): return acceptance
        def update_acceptance_with_status_history(self, acceptance, history): return acceptance
        def delete_acceptance(self, acceptance_id): return True
        def list_acceptances(self, query): return []
        def list_acceptance_history(self, query): return []

    item = CreateAcceptanceUseCase(Repository()).execute(
        CreateAcceptanceCommand(1, uuid4(), AcceptanceStatus.PRESENTED, None),
        AcceptanceActor("manager", uuid4()),
    )
    assert item.status is AcceptanceStatus.PRESENTED


def test_acceptance_mutation_is_forbidden_for_project_leader():
    class Repository:
        def create_acceptance(self, acceptance):
            return acceptance

        def get_project_object_status(self, project_id): return "active"

        def get_acceptance(self, acceptance_id): return None
        def update_acceptance(self, acceptance): return acceptance
        def update_acceptance_with_status_history(self, acceptance, history): return acceptance
        def delete_acceptance(self, acceptance_id): return True
        def list_acceptances(self, query): return []
        def list_acceptance_history(self, query): return []

    with pytest.raises(AcceptanceForbiddenError):
        CreateAcceptanceUseCase(Repository()).execute(
            CreateAcceptanceCommand(1, uuid4(), AcceptanceStatus.PRESENTED, None),
            AcceptanceActor("project-leader", uuid4()),
        )


def test_acceptance_mutation_is_blocked_for_waiting_object():
    class Repository:
        def get_project_object_status(self, project_id): return "waiting"

        def create_acceptance(self, acceptance): return acceptance
        def get_acceptance(self, acceptance_id): return None
        def update_acceptance(self, acceptance): return acceptance
        def update_acceptance_with_status_history(self, acceptance, history): return acceptance
        def delete_acceptance(self, acceptance_id): return True
        def list_acceptances(self, query): return []
        def list_acceptance_history(self, query): return []

    with pytest.raises(ValueError, match="object is waiting"):
        CreateAcceptanceUseCase(Repository()).execute(
            CreateAcceptanceCommand(1, uuid4(), AcceptanceStatus.PRESENTED, None),
            AcceptanceActor("manager", uuid4()),
        )


def test_acceptance_manager_clears_comment_when_explicitly_set_to_none():
    acceptance_id = uuid4()

    class Record:
        comment = "old comment"
        project_id = uuid4()

        def to_dict(self):
            return {"id": str(acceptance_id), "comment": self.comment}

    record = Record()

    class Query:
        def __init__(self, result): self.result = result
        def filter(self, *args): return self
        def join(self, *args): return self
        def first(self): return self.result
        def scalar(self): return "active"

    class Session:
        def query(self, model):
            return Query(record if model is Acceptances else "active")

        def flush(self): pass

    updated = AcceptancesManager(session=Session()).update(
        acceptance_id, comment=None
    )

    assert record.comment is None
    assert updated["comment"] is None


class HistoryRepository:
    def __init__(self, acceptance):
        self.acceptance = acceptance
        self.history = []
        self.status_history_calls = 0

    def get_acceptance(self, acceptance_id):
        return self.acceptance

    def update_acceptance(self, acceptance):
        self.acceptance = acceptance
        return acceptance

    def update_acceptance_with_status_history(self, acceptance, history):
        self.acceptance = acceptance
        self.history.append(history)
        return acceptance

    def create_acceptance(self, acceptance):
        return acceptance

    def delete_acceptance(self, acceptance_id):
        return True

    def list_acceptances(self, query):
        return []

    def list_acceptance_history(self, query):
        return self.history


def test_status_change_creates_history_record():
    acceptance_id = uuid4()
    actor_id = uuid4()
    repository = HistoryRepository(
        Acceptance(acceptance_id, 1, uuid4(), AcceptanceStatus.PRESENTED)
    )

    UpdateAcceptanceUseCase(repository).execute(
        UpdateAcceptanceCommand(
            id=acceptance_id, status=AcceptanceStatus.ACCEPTED_ON_SITE
        ),
        AcceptanceActor("manager", actor_id),
    )

    assert len(repository.history) == 1
    history = repository.history[0]
    assert history.acceptance_id == acceptance_id
    assert history.changed_by == actor_id
    assert history.from_status is AcceptanceStatus.PRESENTED
    assert history.to_status is AcceptanceStatus.ACCEPTED_ON_SITE


def test_same_status_does_not_create_history_record():
    acceptance_id = uuid4()
    repository = HistoryRepository(
        Acceptance(acceptance_id, 1, uuid4(), AcceptanceStatus.PRESENTED)
    )

    UpdateAcceptanceUseCase(repository).execute(
        UpdateAcceptanceCommand(id=acceptance_id, status=AcceptanceStatus.PRESENTED),
        AcceptanceActor("admin", uuid4()),
    )

    assert repository.history == []
