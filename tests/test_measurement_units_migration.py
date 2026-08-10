from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260804_measurement_units_reference.py"
)


def _load_migration():
    spec = spec_from_file_location("measurement_units_migration", MIGRATION_PATH)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_migration_accepts_legacy_measurement_unit_values():
    migration = _load_migration()

    assert "шт" in migration.SUPPORTED_MEASUREMENT_UNIT_VALUES
    assert "шт." in migration.SUPPORTED_MEASUREMENT_UNIT_VALUES
    assert "м2" in migration.SUPPORTED_MEASUREMENT_UNIT_VALUES

    source = MIGRATION_PATH.read_text()
    assert "WHEN 'шт' THEN :piece" in source
    assert "WHEN 'м2' THEN :square_meter" in source
