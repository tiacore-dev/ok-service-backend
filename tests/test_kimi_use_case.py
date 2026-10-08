from dataclasses import dataclass

import pytest

from app.domain.kimi import SystemPromptMissingError
from app.domain.system_settings import SystemSetting
from app.use_cases.kimi import AskKimiUseCase


@dataclass
class _SettingsRepository:
    setting: SystemSetting | None

    def get_system_setting(self, system_setting_id: str) -> SystemSetting | None:
        assert system_setting_id == "system_prompt"
        return self.setting


class _KimiClient:
    def __init__(self) -> None:
        self.received: tuple[str, str] | None = None

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        developer_prompt: str | None = None,
    ) -> str:
        self.received = (system_prompt, user_prompt)
        return "Answer"


def test_ask_kimi_uses_system_prompt_from_system_settings():
    client = _KimiClient()
    use_case = AskKimiUseCase(
        client=client,
        system_settings=_SettingsRepository(
            SystemSetting("system_prompt", "Системный промпт", "Be helpful")
        ),
    )

    assert use_case.execute("Question") == "Answer"
    assert client.received == ("Be helpful", "Question")


@pytest.mark.parametrize("value", [None, "", "   "])
def test_ask_kimi_rejects_missing_system_prompt(value: str | None):
    use_case = AskKimiUseCase(
        client=_KimiClient(),
        system_settings=_SettingsRepository(
            SystemSetting("system_prompt", "Системный промпт", value)
        ),
    )

    with pytest.raises(SystemPromptMissingError, match="Отсутствует системный промпт"):
        use_case.execute("Question")
