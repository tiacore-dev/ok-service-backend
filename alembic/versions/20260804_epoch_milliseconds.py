"""Normalize persisted Unix timestamps to milliseconds.

Revision ID: 20260804_epoch_milliseconds
Revises: 20260804_measurement_units
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_epoch_milliseconds"
down_revision: Union[str, None] = "20260804_measurement_units"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MS_DEFAULT = sa.text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)")
_SECONDS_DEFAULT = sa.text("EXTRACT(EPOCH FROM NOW())")

# Every BigInteger temporal field in the current schema. Values below 10^11
# are Unix seconds; values at or above it are already milliseconds.
_TIMESTAMP_COLUMNS = {
    "api_keys": ("expires_at", "created_at"),
    "cities": ("created_at",),
    "leaves": ("start_date", "end_date", "created_at", "updated_at"),
    "materials": ("created_at",),
    "measurement_units": ("created_at",),
    "objects": ("created_at",),
    "positions": ("created_at",),
    "project_materials": ("created_at",),
    "project_schedules": ("date", "created_at"),
    "project_works": ("created_at",),
    "projects": ("created_at",),
    "shift_report_details": ("created_at",),
    "shift_report_materials": ("created_at",),
    "shift_reports": (
        "date",
        "date_start",
        "date_end",
        "created_at",
        "signed_at",
        "updated_at",
    ),
    "users": ("created_at",),
    "work_categories": ("created_at",),
    "work_material_relations": ("created_at",),
    "work_prices": ("created_at",),
    "works": ("created_at",),
}


def _set_defaults(server_default: sa.TextClause) -> None:
    for table, columns in _TIMESTAMP_COLUMNS.items():
        for column in columns:
            if column == "created_at":
                op.alter_column(
                    table,
                    column,
                    existing_type=sa.BigInteger(),
                    server_default=server_default,
                )


def upgrade() -> None:
    bind = op.get_bind()

    for table, columns in _TIMESTAMP_COLUMNS.items():
        for column in columns:
            bind.execute(
                sa.text(
                    f'UPDATE "{table}" '
                    f'SET "{column}" = "{column}" * 1000 '
                    f'WHERE "{column}" IS NOT NULL AND "{column}" < 100000000000'
                )
            )

    _set_defaults(_MS_DEFAULT)


def downgrade() -> None:
    bind = op.get_bind()

    for table, columns in _TIMESTAMP_COLUMNS.items():
        for column in columns:
            bind.execute(
                sa.text(
                    f'UPDATE "{table}" '
                    f'SET "{column}" = "{column}" / 1000 '
                    f'WHERE "{column}" IS NOT NULL AND "{column}" >= 100000000000'
                )
            )

    _set_defaults(_SECONDS_DEFAULT)
