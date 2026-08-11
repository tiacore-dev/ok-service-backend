from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Protocol, cast

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260804_measurement_units_reference.py"
)


class MeasurementUnitsMigration(Protocol):
    SUPPORTED_MEASUREMENT_UNIT_VALUES: set[str]


def _load_migration() -> MeasurementUnitsMigration:
    spec = spec_from_file_location("measurement_units_migration", MIGRATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load migration module: {MIGRATION_PATH}")
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    return cast(MeasurementUnitsMigration, migration)


def test_migration_accepts_legacy_measurement_unit_values():
    migration = _load_migration()

    assert "шт" in migration.SUPPORTED_MEASUREMENT_UNIT_VALUES
    assert "шт." in migration.SUPPORTED_MEASUREMENT_UNIT_VALUES
    assert "м2" in migration.SUPPORTED_MEASUREMENT_UNIT_VALUES

    source = MIGRATION_PATH.read_text()
    assert "WHEN 'шт' THEN :piece" in source
    assert "WHEN 'м2' THEN :square_meter" in source
