from uuid import UUID, uuid4

import pytest

from app.domain.work_categories import (
    WorkCategory,
    WorkCategoryHierarchyError,
    WorkCategoryValidationError,
    ensure_parent_keeps_tree_acyclic,
)
from app.use_cases.work_categories import (
    CreateWorkCategoryCommand,
    CreateWorkCategoryUseCase,
    UpdateWorkCategoryCommand,
    UpdateWorkCategoryUseCase,
)


class InMemoryWorkCategoryRepository:
    def __init__(self, *categories: WorkCategory):
        self.items: dict[UUID, WorkCategory] = {
            item.work_category_id: item for item in categories
        }
        self.updated: WorkCategory | None = None

    def create_work_category(self, work_category: WorkCategory) -> WorkCategory:
        self.items[work_category.work_category_id] = work_category
        return work_category

    def get_work_category(self, work_category_id: UUID) -> WorkCategory | None:
        return self.items.get(work_category_id)

    def update_work_category(self, work_category: WorkCategory) -> WorkCategory | None:
        self.updated = work_category
        self.items[work_category.work_category_id] = work_category
        return work_category

    def delete_work_category(self, work_category_id: UUID) -> bool:
        return self.items.pop(work_category_id, None) is not None

    def list_work_categories(self, query) -> list[WorkCategory]:
        return list(self.items.values())

    def get_lineage_ids(self, work_category_id: UUID) -> list[UUID]:
        lineage: list[UUID] = []
        current = self.items.get(work_category_id)
        while current is not None and current.work_category_id not in lineage:
            lineage.append(current.work_category_id)
            current = (
                self.items.get(current.parent_id) if current.parent_id else None
            )
        return lineage


def _category(name: str, parent: WorkCategory | None = None, **kwargs) -> WorkCategory:
    return WorkCategory(
        work_category_id=uuid4(),
        name=name,
        created_by=uuid4(),
        created_at=1,
        parent_id=parent.work_category_id if parent else None,
        **kwargs,
    )


def _chain() -> tuple[WorkCategory, WorkCategory, WorkCategory]:
    a = _category("A")
    b = _category("B", a)
    c = _category("C", b)
    return a, b, c


# --- domain -----------------------------------------------------------------


def test_entity_defaults_to_root():
    assert _category("Root").parent_id is None


def test_entity_rejects_self_parent():
    category_id = uuid4()
    with pytest.raises(WorkCategoryHierarchyError):
        WorkCategory(
            work_category_id=category_id,
            name="Loop",
            created_by=uuid4(),
            created_at=1,
            parent_id=category_id,
        )


def test_hierarchy_error_is_validation_error():
    assert issubclass(WorkCategoryHierarchyError, WorkCategoryValidationError)


def test_policy_rejects_category_in_parent_lineage():
    a, b, c = uuid4(), uuid4(), uuid4()
    with pytest.raises(WorkCategoryHierarchyError):
        ensure_parent_keeps_tree_acyclic(a, c, [c, b, a])


def test_policy_accepts_unrelated_parent():
    ensure_parent_keeps_tree_acyclic(uuid4(), uuid4(), [uuid4()])


# --- create -----------------------------------------------------------------


def test_create_root_category_without_parent():
    repository = InMemoryWorkCategoryRepository()

    result = CreateWorkCategoryUseCase(repository=repository).execute(
        CreateWorkCategoryCommand(name="Root", created_by=uuid4())
    )

    assert result.parent_id is None


def test_create_nested_category():
    a, b, _ = _chain()
    repository = InMemoryWorkCategoryRepository(a, b)

    result = CreateWorkCategoryUseCase(repository=repository).execute(
        CreateWorkCategoryCommand(
            name="Child", created_by=uuid4(), parent_id=b.work_category_id
        )
    )

    assert result.parent_id == b.work_category_id


def test_create_rejects_unknown_parent():
    repository = InMemoryWorkCategoryRepository()

    with pytest.raises(WorkCategoryValidationError, match="not found"):
        CreateWorkCategoryUseCase(repository=repository).execute(
            CreateWorkCategoryCommand(name="X", created_by=uuid4(), parent_id=uuid4())
        )


def test_create_rejects_deleted_parent():
    parent = _category("Deleted", deleted=True)
    repository = InMemoryWorkCategoryRepository(parent)

    with pytest.raises(WorkCategoryValidationError, match="deleted"):
        CreateWorkCategoryUseCase(repository=repository).execute(
            CreateWorkCategoryCommand(
                name="X", created_by=uuid4(), parent_id=parent.work_category_id
            )
        )


# --- update -----------------------------------------------------------------


def test_update_sets_parent():
    a = _category("A")
    b = _category("B")
    repository = InMemoryWorkCategoryRepository(a, b)

    result = UpdateWorkCategoryUseCase(repository=repository).execute(
        UpdateWorkCategoryCommand(
            work_category_id=b.work_category_id,
            parent_id=a.work_category_id,
            parent_id_is_set=True,
        )
    )

    assert result.parent_id == a.work_category_id


def test_update_moves_category_to_root():
    a, b, _ = _chain()
    repository = InMemoryWorkCategoryRepository(a, b)

    result = UpdateWorkCategoryUseCase(repository=repository).execute(
        UpdateWorkCategoryCommand(
            work_category_id=b.work_category_id, parent_id=None, parent_id_is_set=True
        )
    )

    assert result.parent_id is None


def test_update_without_parent_field_keeps_parent():
    a, b, _ = _chain()
    repository = InMemoryWorkCategoryRepository(a, b)

    result = UpdateWorkCategoryUseCase(repository=repository).execute(
        UpdateWorkCategoryCommand(work_category_id=b.work_category_id, name="Renamed")
    )

    assert result.name == "Renamed"
    assert result.parent_id == a.work_category_id


def test_update_rejects_self_parent():
    a = _category("A")
    repository = InMemoryWorkCategoryRepository(a)

    with pytest.raises(WorkCategoryHierarchyError):
        UpdateWorkCategoryUseCase(repository=repository).execute(
            UpdateWorkCategoryCommand(
                work_category_id=a.work_category_id,
                parent_id=a.work_category_id,
                parent_id_is_set=True,
            )
        )
    assert repository.updated is None


def test_update_rejects_direct_cycle():
    a, b, _ = _chain()
    repository = InMemoryWorkCategoryRepository(a, b)

    with pytest.raises(WorkCategoryHierarchyError, match="circular"):
        UpdateWorkCategoryUseCase(repository=repository).execute(
            UpdateWorkCategoryCommand(
                work_category_id=a.work_category_id,
                parent_id=b.work_category_id,
                parent_id_is_set=True,
            )
        )
    assert repository.updated is None


def test_update_rejects_indirect_cycle():
    a, b, c = _chain()
    repository = InMemoryWorkCategoryRepository(a, b, c)

    with pytest.raises(WorkCategoryHierarchyError, match="circular"):
        UpdateWorkCategoryUseCase(repository=repository).execute(
            UpdateWorkCategoryCommand(
                work_category_id=a.work_category_id,
                parent_id=c.work_category_id,
                parent_id_is_set=True,
            )
        )
    assert repository.updated is None


def test_update_rejects_unknown_parent():
    a = _category("A")
    repository = InMemoryWorkCategoryRepository(a)

    with pytest.raises(WorkCategoryValidationError, match="not found"):
        UpdateWorkCategoryUseCase(repository=repository).execute(
            UpdateWorkCategoryCommand(
                work_category_id=a.work_category_id,
                parent_id=uuid4(),
                parent_id_is_set=True,
            )
        )
