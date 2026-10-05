from typing import Protocol
from uuid import UUID

from app.domain.system_settings import SystemSetting


class SystemSettingRepository(Protocol):
    def list_system_settings(self) -> list[SystemSetting]: ...

    def get_system_setting(self, system_setting_id: str) -> SystemSetting | None: ...

    def update_system_setting(
        self, system_setting_id: str, value: str | None, modified_by: UUID
    ) -> SystemSetting | None: ...
