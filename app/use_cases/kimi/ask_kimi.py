from dataclasses import dataclass

from app.domain.kimi import SystemPromptMissingError

from .ports import KimiCompletionClient, SystemPromptRepository


@dataclass(slots=True)
class AskKimiUseCase:
    client: KimiCompletionClient
    system_settings: SystemPromptRepository

    def execute(self, user_prompt: str) -> str:
        setting = self.system_settings.get_system_setting("system_prompt")
        if setting is None or setting.value is None or not setting.value.strip():
            raise SystemPromptMissingError("Отсутствует системный промпт")
        return self.client.complete(
            system_prompt=setting.value,
            user_prompt=user_prompt,
        )
