from decimal import Decimal
from uuid import uuid4

from app.domain.work_material_relations import WorkMaterialRelation
from app.use_cases.work_material_relations import (
    CreateWorkMaterialRelationCommand,
    CreateWorkMaterialRelationUseCase,
    DeleteWorkMaterialRelationUseCase,
    ListWorkMaterialRelationsUseCase,
    UpdateWorkMaterialRelationCommand,
    UpdateWorkMaterialRelationUseCase,
    WorkMaterialRelationListQuery,
)


class FakeWorkMaterialRelationRepository:
    def __init__(self, relation: WorkMaterialRelation | None = None):
        self.relation = relation
        self.created = None
        self.updated = None
        self.deleted = None
        self.listed_query = None

    def create_work_material_relation(
        self, work_material_relation: WorkMaterialRelation
    ) -> WorkMaterialRelation:
        self.created = work_material_relation
        self.relation = work_material_relation
        return work_material_relation

    def get_work_material_relation(self, work_material_relation_id):
        if self.relation and self.relation.work_material_relation_id == work_material_relation_id:
            return self.relation
        return None

    def update_work_material_relation(
        self, work_material_relation: WorkMaterialRelation
    ):
        self.updated = work_material_relation
        self.relation = work_material_relation
        return work_material_relation

    def delete_work_material_relation(self, work_material_relation_id):
        self.deleted = work_material_relation_id
        return self.relation is not None and self.relation.work_material_relation_id == work_material_relation_id

    def list_work_material_relations(self, query):
        self.listed_query = query
        return [self.relation] if self.relation is not None else []


def test_create_work_material_relation_use_case():
    repository = FakeWorkMaterialRelationRepository()
    command = CreateWorkMaterialRelationCommand(
        work=uuid4(),
        material=uuid4(),
        quantity=Decimal("3.25"),
        created_by=uuid4(),
    )

    result = CreateWorkMaterialRelationUseCase(repository=repository).execute(command)

    assert result == repository.created
    assert result.quantity == Decimal("3.25")


def test_update_work_material_relation_use_case():
    relation = WorkMaterialRelation(
        work_material_relation_id=uuid4(),
        work=uuid4(),
        material=uuid4(),
        quantity=Decimal("1.00"),
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeWorkMaterialRelationRepository(relation)

    result = UpdateWorkMaterialRelationUseCase(repository=repository).execute(
        UpdateWorkMaterialRelationCommand(
            work_material_relation_id=relation.work_material_relation_id,
            quantity=Decimal("2.50"),
        )
    )

    assert result.quantity == Decimal("2.50")
    assert repository.updated is not None


def test_list_work_material_relations_use_case_passes_query_through():
    relation = WorkMaterialRelation(
        work_material_relation_id=uuid4(),
        work=uuid4(),
        material=uuid4(),
        quantity=Decimal("1.00"),
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeWorkMaterialRelationRepository(relation)
    query = WorkMaterialRelationListQuery(work=relation.work)

    result = ListWorkMaterialRelationsUseCase(repository=repository).execute(query)

    assert result == [relation]
    assert repository.listed_query == query


def test_delete_work_material_relation_use_case_returns_repository_result():
    relation = WorkMaterialRelation(
        work_material_relation_id=uuid4(),
        work=uuid4(),
        material=uuid4(),
        quantity=Decimal("1.00"),
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeWorkMaterialRelationRepository(relation)

    deleted = DeleteWorkMaterialRelationUseCase(repository=repository).execute(
        relation.work_material_relation_id
    )

    assert deleted is True
    assert repository.deleted == relation.work_material_relation_id
