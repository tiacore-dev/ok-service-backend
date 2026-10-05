from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateSystemSettingCommand:
    system_setting_id: str
    value: str | None
    modified_by: UUID
