from dataclasses import dataclass

from app.domain.system_settings import SystemSetting

from .dto import UpdateSystemSettingCommand
from .ports import SystemSettingRepository


@dataclass(slots=True)
class UpdateSystemSettingUseCase:
    repository: SystemSettingRepository

    def execute(self, command: UpdateSystemSettingCommand) -> SystemSetting | None:
        return self.repository.update_system_setting(
            command.system_setting_id, command.value, command.modified_by
        )
