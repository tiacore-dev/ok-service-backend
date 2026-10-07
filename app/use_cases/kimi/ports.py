from typing import Protocol

from app.domain.system_settings import SystemSetting


class KimiFileContentClient(Protocol):
    def extract_file_content(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str: ...


class KimiCompletionClient(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str: ...


class SystemPromptRepository(Protocol):
    def get_system_setting(self, system_setting_id: str) -> SystemSetting | None: ...


class KimiClient(KimiFileContentClient, KimiCompletionClient, Protocol):
    pass
