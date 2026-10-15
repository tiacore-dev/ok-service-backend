from dataclasses import dataclass

from app.domain.system_settings import SystemSetting

from .dto import UpdateSystemSettingCommand
from .ports import SystemSettingRepository


@dataclass(slots=True)
class UpdateSystemSettingUseCase:
    repository: SystemSettingRepository

    def execute(self, command: UpdateSystemSettingCommand) -> SystemSetting | None:
        return self.repository.update_system_setting(
            command.system_setting_id,
            value=command.value,
            value_is_set=command.value_is_set,
            name=command.name,
            name_is_set=command.name_is_set,
            modified_by=command.modified_by,
        )
