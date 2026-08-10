"""Create measurement unit reference and migrate work/material values.

Revision ID: 20260804_measurement_units
Revises: 20260722_shift_report_audit
"""

from typing import Sequence, Union
from uuid import UUID as PythonUUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.elements import TextClause

from alembic import op

revision: str = "20260804_measurement_units"
down_revision: Union[str, None] = "20260722_shift_report_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

METER_ID = PythonUUID("00000000-0000-0000-0000-000000000001")
PIECE_ID = PythonUUID("00000000-0000-0000-0000-000000000002")
TENTH_METER_ID = PythonUUID("00000000-0000-0000-0000-000000000003")
SQUARE_METER_ID = PythonUUID("00000000-0000-0000-0000-000000000004")

SUPPORTED_MEASUREMENT_UNIT_VALUES = {
    "м.",
    "м",
    "шт.",
    "шт",
    "0.1 м (10 см)",
    "м2",
}


def _unit_bindparams(statement: TextClause) -> TextClause:
    return statement.bindparams(
        sa.bindparam("meter", value=METER_ID, type_=UUID(as_uuid=True)),
        sa.bindparam("piece", value=PIECE_ID, type_=UUID(as_uuid=True)),
        sa.bindparam("tenth_meter", value=TENTH_METER_ID, type_=UUID(as_uuid=True)),
        sa.bindparam("square_meter", value=SQUARE_METER_ID, type_=UUID(as_uuid=True)),
    )


def upgrade() -> None:
    op.create_table(
        "measurement_units",
        sa.Column(
            "measurement_unit_id", UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.user_id"),
            nullable=True,
        ),
    )
    op.execute(
        _unit_bindparams(sa.text(
            """
            INSERT INTO measurement_units (measurement_unit_id, name)
            VALUES
                (:meter, 'м'),
                (:piece, 'шт.'),
                (:tenth_meter, '0.1 м (10 см)'),
                (:square_meter, 'м2')
            """
        ))
    )

    for table in ("works", "materials"):
        op.add_column(
            table, sa.Column("measurement_unit_id", UUID(as_uuid=True), nullable=True)
        )
        op.execute(
            _unit_bindparams(sa.text(
                f"""
                UPDATE {table}
                SET measurement_unit_id = CASE trim(measurement_unit)
                    WHEN 'м.' THEN :meter
                    WHEN 'м' THEN :meter
                    WHEN 'шт.' THEN :piece
                    WHEN 'шт' THEN :piece
                    WHEN '0.1 м (10 см)' THEN :tenth_meter
                    WHEN 'м2' THEN :square_meter
                    ELSE NULL
                END
                WHERE measurement_unit IS NOT NULL
                """
            ))
        )
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM {table}
                        WHERE measurement_unit IS NOT NULL
                          AND trim(measurement_unit) NOT IN (
                              'м.', 'м', 'шт.', 'шт', '0.1 м (10 см)', 'м2'
                          )
                    ) THEN
                        RAISE EXCEPTION 'Unsupported measurement_unit value in {table}';
                    END IF;
                END $$;
                """
            )
        )
        op.drop_column(table, "measurement_unit")
        op.alter_column(
            table, "measurement_unit_id", new_column_name="measurement_unit"
        )
        op.create_foreign_key(
            f"{table}_measurement_unit_fkey",
            table,
            "measurement_units",
            ["measurement_unit"],
            ["measurement_unit_id"],
        )


def downgrade() -> None:
    for table in ("works", "materials"):
        op.add_column(
            table, sa.Column("measurement_unit_text", sa.String(), nullable=True)
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {table} AS target
                SET measurement_unit_text = CASE units.name
                    WHEN 'м' THEN 'м.'
                    ELSE units.name
                END
                FROM measurement_units AS units
                WHERE target.measurement_unit = units.measurement_unit_id
                """
            )
        )
        op.drop_constraint(f"{table}_measurement_unit_fkey", table, type_="foreignkey")
        op.drop_column(table, "measurement_unit")
        op.alter_column(
            table, "measurement_unit_text", new_column_name="measurement_unit"
        )
    op.drop_table("measurement_units")
