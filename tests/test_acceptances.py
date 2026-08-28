from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.acceptances import Acceptance, AcceptanceForbiddenError, AcceptanceStatus
from app.domain.work_acceptance_relations import (
    WorkAcceptanceRelation,
    WorkAcceptanceRelationValidationError,
)
from app.use_cases.acceptances import (
    AcceptanceActor,
    CreateAcceptanceCommand,
    CreateAcceptanceUseCase,
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

        def get_acceptance(self, acceptance_id): return None
        def update_acceptance(self, acceptance): return acceptance
        def delete_acceptance(self, acceptance_id): return True
        def list_acceptances(self, query): return []

    item = CreateAcceptanceUseCase(Repository()).execute(
        CreateAcceptanceCommand(1, uuid4(), AcceptanceStatus.PRESENTED, None),
        AcceptanceActor("manager"),
    )
    assert item.status is AcceptanceStatus.PRESENTED


def test_acceptance_mutation_is_forbidden_for_project_leader():
    class Repository:
        def create_acceptance(self, acceptance):
            return acceptance

        def get_acceptance(self, acceptance_id): return None
        def update_acceptance(self, acceptance): return acceptance
        def delete_acceptance(self, acceptance_id): return True
        def list_acceptances(self, query): return []

    with pytest.raises(AcceptanceForbiddenError):
        CreateAcceptanceUseCase(Repository()).execute(
            CreateAcceptanceCommand(1, uuid4(), AcceptanceStatus.PRESENTED, None),
            AcceptanceActor("project-leader"),
        )
