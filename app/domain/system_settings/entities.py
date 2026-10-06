from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SystemSetting:
    system_setting_id: str
    name: str
    value: str | None
    modified_at: int | None = None
    modified_by: UUID | None = None
