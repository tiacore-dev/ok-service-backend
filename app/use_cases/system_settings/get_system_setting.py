from dataclasses import dataclass

from app.domain.system_settings import SystemSetting

from .ports import SystemSettingRepository


@dataclass(slots=True)
class GetSystemSettingUseCase:
    repository: SystemSettingRepository

    def execute(self, system_setting_id: str) -> SystemSetting | None:
        return self.repository.get_system_setting(system_setting_id)
