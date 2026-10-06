from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateSystemSettingCommand:
    system_setting_id: str
    value: str | None
    value_is_set: bool
    name: str | None
    name_is_set: bool
    modified_by: UUID
