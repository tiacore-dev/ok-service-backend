from uuid import UUID

from .errors import ProjectMaterialInUseError

ProjectMaterialIdentity = tuple[UUID, UUID, UUID | None]


def ensure_project_material_identity_unchanged(
    *,
    used: bool,
    current_identity: ProjectMaterialIdentity,
    target_identity: ProjectMaterialIdentity,
) -> None:
    if used and current_identity != target_identity:
        raise ProjectMaterialInUseError(
            "Cannot change project, material or project_work of a project material used by shift reports"
        )
