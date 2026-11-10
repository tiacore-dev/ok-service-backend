from __future__ import annotations

from uuid import UUID

from app.domain.work_categories import (
    WorkCategoryValidationError,
    ensure_parent_keeps_tree_acyclic,
)

from .ports import WorkCategoryRepository


def ensure_valid_parent(
    repository: WorkCategoryRepository,
    work_category_id: UUID,
    parent_id: UUID,
) -> None:
    """Check that ``parent_id`` can become the parent of ``work_category_id``."""
    if parent_id == work_category_id:
        ensure_parent_keeps_tree_acyclic(work_category_id, parent_id, ())
    parent = repository.get_work_category(parent_id)
    if parent is None:
        raise WorkCategoryValidationError("Parent work category not found.")
    if parent.deleted:
        raise WorkCategoryValidationError("Parent work category is deleted.")
    ensure_parent_keeps_tree_acyclic(
        work_category_id, parent_id, repository.get_lineage_ids(parent_id)
    )
