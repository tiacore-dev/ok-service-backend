from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from .errors import WorkCategoryHierarchyError


def ensure_parent_keeps_tree_acyclic(
    work_category_id: UUID,
    parent_id: UUID,
    parent_lineage_ids: Iterable[UUID],
) -> None:
    """Reject a parent whose lineage (parent and its ancestors) contains the category.

    ``parent_lineage_ids`` must contain ``parent_id`` itself followed by all of
    its ancestors up to the root.
    """
    if parent_id == work_category_id:
        raise WorkCategoryHierarchyError("Work category cannot be its own parent.")
    if work_category_id in set(parent_lineage_ids):
        raise WorkCategoryHierarchyError(
            "Parent assignment would create a circular reference."
        )
