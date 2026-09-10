from decimal import Decimal
from threading import Barrier, Thread
from uuid import UUID, uuid4

import pytest

from app.domain.acceptances import Acceptance, AcceptanceForbiddenError, AcceptanceStatus
from app.database.managers.materials_manager import (
    AcceptancesManager,
    WorkAcceptanceRelationsManager,
)
from app.database.models import Acceptances, Objects, ProjectWorks, WorkAcceptanceRelations
from app.domain.work_acceptance_relations import (
    WorkAcceptanceRelation,
    WorkAcceptanceQuantityExceededError,
    WorkAcceptanceRelationValidationError,
)
from app.use_cases.acceptances import (
    AcceptanceActor,
    CreateAcceptanceCommand,
    CreateAcceptanceUseCase,
    UpdateAcceptanceCommand,
    UpdateAcceptanceUseCase,
)
from app.use_cases.work_acceptance_relations import (
    CreateWorkAcceptanceRelationCommand,
    CreateWorkAcceptanceRelationUseCase,
    UpdateWorkAcceptanceRelationCommand,
    UpdateWorkAcceptanceRelationUseCase,
)


def test_acceptance_status_and_timestamp_are_normalized():
    item = Acceptance(uuid4(), 1720000000000, uuid4(), AcceptanceStatus.PRESENTED)
    assert item.status is AcceptanceStatus.PRESENTED
    assert item.date == 1720000000000


def test_work_acceptance_relation_requires_positive_quantity():
    with pytest.raises(WorkAcceptanceRelationValidationError):
        WorkAcceptanceRelation(uuid4(), uuid4(), uuid4(), Decimal("0"))


class RelationRepository:
    def __init__(self, relation=None, specification_quantity=Decimal("10"), accepted_quantity=Decimal("0")):
        self.relation = relation
        self.specification_quantity = specification_quantity
        self.accepted_quantity = accepted_quantity
        self.excluded_relation_id = None
        self.created = None
        self.updated = None

    def _ensure_quantity_available(self, relation, exclude_relation_id=None):
        self.excluded_relation_id = exclude_relation_id
        accepted_quantity = self.accepted_quantity
        if exclude_relation_id is not None and self.relation is not None:
            accepted_quantity -= self.relation.quantity
        if accepted_quantity + relation.quantity > self.specification_quantity:
            raise WorkAcceptanceQuantityExceededError("quantity exceeded")

    def create_work_acceptance_relation(self, relation):
        self._ensure_quantity_available(relation)
        self.created = relation
        return relation

    def get_work_acceptance_relation(self, relation_id):
        return self.relation

    def update_work_acceptance_relation(self, relation):
        self._ensure_quantity_available(relation, exclude_relation_id=relation.id)
        self.updated = relation
        return relation

    def delete_work_acceptance_relation(self, relation_id):
        return True

    def list_work_acceptance_relations(self, query):
        return []


def test_work_acceptance_relation_creation_rejects_quantity_above_work_limit():
    repository = RelationRepository(accepted_quantity=Decimal("8"))

    with pytest.raises(WorkAcceptanceQuantityExceededError):
        CreateWorkAcceptanceRelationUseCase(repository).execute(
            CreateWorkAcceptanceRelationCommand(uuid4(), uuid4(), Decimal("3"))
        )

    assert repository.created is None


def test_work_acceptance_relation_creation_allows_quantity_within_work_limit():
    repository = RelationRepository(accepted_quantity=Decimal("8"))

    created = CreateWorkAcceptanceRelationUseCase(repository).execute(
        CreateWorkAcceptanceRelationCommand(uuid4(), uuid4(), Decimal("2"))
    )

    assert created.quantity == Decimal("2")
    assert repository.created == created


def test_work_acceptance_relation_update_excludes_current_quantity_from_total():
    relation = WorkAcceptanceRelation(uuid4(), uuid4(), uuid4(), Decimal("8"))
    repository = RelationRepository(relation=relation, accepted_quantity=Decimal("8"))

    updated = UpdateWorkAcceptanceRelationUseCase(repository).execute(
        UpdateWorkAcceptanceRelationCommand(id=relation.id, quantity=Decimal("10"))
    )

    assert updated.quantity == Decimal("10")
    assert repository.excluded_relation_id == relation.id
    assert repository.updated == updated


def test_work_acceptance_relation_update_rejects_new_total_above_work_limit():
    relation = WorkAcceptanceRelation(uuid4(), uuid4(), uuid4(), Decimal("8"))
    repository = RelationRepository(relation=relation, accepted_quantity=Decimal("8"))

    with pytest.raises(WorkAcceptanceQuantityExceededError):
        UpdateWorkAcceptanceRelationUseCase(repository).execute(
            UpdateWorkAcceptanceRelationCommand(id=relation.id, quantity=Decimal("11"))
        )

    assert repository.updated is None


def test_concurrent_work_acceptance_creation_cannot_exceed_specification(
    db_session, seed_project, seed_work, seed_user
):
    project_id = UUID(seed_project["project_id"])
    work_id = UUID(seed_work["work_id"])
    user_id = UUID(seed_user["user_id"])
    db_session.add(
        ProjectWorks(
            project_work_id=uuid4(),
            project_work_name="Concurrent work",
            work=work_id,
            project=project_id,
            quantity=2,
            created_by=user_id,
        )
    )
    acceptance = Acceptances(
        id=uuid4(), date=20260910, project_id=project_id, status="presented"
    )
    db_session.add(acceptance)
    db_session.commit()
    acceptance_id = UUID(str(acceptance.id))

    barrier = Barrier(2)
    outcomes = []

    def create_relation():
        relation = WorkAcceptanceRelation(uuid4(), acceptance_id, work_id, Decimal("2"))
        barrier.wait()
        try:
            WorkAcceptanceRelationsManager().add_with_quantity_check(
                id=relation.id,
                acceptance_id=relation.acceptance_id,
                work_id=relation.work_id,
                quantity=relation.quantity,
            )
        except WorkAcceptanceQuantityExceededError:
            outcomes.append("rejected")
        else:
            outcomes.append("created")

    threads = [Thread(target=create_relation) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["created", "rejected"]
    assert (
        db_session.query(WorkAcceptanceRelations)
        .filter_by(acceptance_id=acceptance_id, work_id=work_id)
        .with_entities(WorkAcceptanceRelations.quantity)
        .all()
    ) == [(Decimal("2"),)]


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
    assert updated is not None
    assert updated["comment"] is None


def test_only_admin_can_edit_signed_documents_acceptance():
    acceptance = Acceptance(
        uuid4(), 1, uuid4(), AcceptanceStatus.DOCUMENTS_SIGNED, "comment"
    )

    with pytest.raises(AcceptanceForbiddenError, match="Only admin"):
        UpdateAcceptanceUseCase(HistoryRepository(acceptance)).execute(
            UpdateAcceptanceCommand(
                id=acceptance.id, comment="new comment", comment_provided=True
            ),
            AcceptanceActor("manager", uuid4()),
        )


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
