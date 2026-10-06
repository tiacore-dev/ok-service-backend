from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Protocol, cast


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic/versions/20261007090000_add_name_to_system_settings.py"
)


class SystemSettingsMigration(Protocol):
    revision: str
    down_revision: str


def _load_migration() -> SystemSettingsMigration:
    spec = spec_from_file_location("system_settings_name_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load migration module: {MIGRATION_PATH}")
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return cast(SystemSettingsMigration, migration)


def test_system_settings_name_migration_backfills_system_prompt_and_requires_name():
    migration = _load_migration()

    assert migration.revision == "20261007090000"
    assert migration.down_revision == "20261006000000"
    source = MIGRATION_PATH.read_text()
    assert 'sa.Column("name", sa.String(), nullable=True)' in source
    assert "SET name = 'Системный промпт'" in source
    assert 'op.alter_column("system_settings", "name", nullable=False)' in source
