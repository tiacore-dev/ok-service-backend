from app.database.managers.system_settings_manager import SystemSettingsManager
from app.utils.db_setting_tables import set_system_settings


def test_system_settings_bootstrap_adds_system_prompt(monkeypatch):
    records = []

    monkeypatch.setattr(
        SystemSettingsManager,
        "ensure_system_prompt",
        lambda self: records.append("ensured"),
    )

    set_system_settings()

    assert records == ["ensured"]


def test_system_settings_bootstrap_does_not_overwrite_existing_value(monkeypatch):
    records = []

    monkeypatch.setattr(
        SystemSettingsManager,
        "ensure_system_prompt",
        lambda self: records.append("ensured"),
    )

    set_system_settings()

    assert records == ["ensured"]
