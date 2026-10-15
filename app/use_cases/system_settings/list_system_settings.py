from dataclasses import dataclass

from app.domain.system_settings import SystemSetting

from .ports import SystemSettingRepository


@dataclass(slots=True)
class ListSystemSettingsUseCase:
    repository: SystemSettingRepository

    def execute(self) -> list[SystemSetting]:
        return self.repository.list_system_settings()
