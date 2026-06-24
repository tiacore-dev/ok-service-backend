from uuid import uuid4

from app.domain.work_categories import WorkCategory
from app.use_cases.work_categories import (
    CreateWorkCategoryCommand,
    CreateWorkCategoryUseCase,
    DeleteWorkCategoryUseCase,
    ListWorkCategoriesUseCase,
    UpdateWorkCategoryCommand,
    UpdateWorkCategoryUseCase,
    WorkCategoryListQuery,
)


class FakeWorkCategoryRepository:
    def __init__(self, work_category: WorkCategory | None = None):
        self.work_category = work_category
        self.created = None
        self.updated = None
        self.deleted = None
        self.listed_query = None

    def create_work_category(self, work_category: WorkCategory) -> WorkCategory:
        self.created = work_category
        self.work_category = work_category
        return work_category

    def get_work_category(self, work_category_id):
        if self.work_category and self.work_category.work_category_id == work_category_id:
            return self.work_category
        return None

    def update_work_category(self, work_category: WorkCategory):
        self.updated = work_category
        self.work_category = work_category
        return work_category

    def delete_work_category(self, work_category_id):
        self.deleted = work_category_id
        return self.work_category is not None and self.work_category.work_category_id == work_category_id

    def list_work_categories(self, query):
        self.listed_query = query
        return [self.work_category] if self.work_category is not None else []


def test_create_work_category_use_case():
    repository = FakeWorkCategoryRepository()
    command = CreateWorkCategoryCommand(name="Painting", created_by=uuid4())

    result = CreateWorkCategoryUseCase(repository=repository).execute(command)

    assert result == repository.created
    assert result.name == "Painting"
    assert result.deleted is False


def test_update_work_category_use_case():
    work_category = WorkCategory(
        work_category_id=uuid4(),
        name="Old name",
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeWorkCategoryRepository(work_category)

    result = UpdateWorkCategoryUseCase(repository=repository).execute(
        UpdateWorkCategoryCommand(
            work_category_id=work_category.work_category_id,
            name="New name",
            deleted=True,
        )
    )

    assert result.name == "New name"
    assert result.deleted is True
    assert repository.updated is not None


def test_list_work_categories_use_case_passes_query_through():
    work_category = WorkCategory(
        work_category_id=uuid4(),
        name="Painting",
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeWorkCategoryRepository(work_category)
    query = WorkCategoryListQuery(name="Paint")

    result = ListWorkCategoriesUseCase(repository=repository).execute(query)

    assert result == [work_category]
    assert repository.listed_query == query


def test_delete_work_category_use_case_returns_repository_result():
    work_category = WorkCategory(
        work_category_id=uuid4(),
        name="Painting",
        created_by=uuid4(),
        created_at=1,
    )
    repository = FakeWorkCategoryRepository(work_category)

    deleted = DeleteWorkCategoryUseCase(repository=repository).execute(
        work_category.work_category_id
    )

    assert deleted is True
    assert repository.deleted == work_category.work_category_id
