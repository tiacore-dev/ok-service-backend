"""merge heads: 7f1d5c3f1bf2 + c1e3f4ab2f1d

Revision ID: 5ea2fe712409
Revises: 7f1d5c3f1bf2, c1e3f4ab2f1d
Create Date: 2025-11-05 23:36:16.146221

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "5ea2fe712409"
down_revision: Union[str, None] = ("7f1d5c3f1bf2", "c1e3f4ab2f1d")  # type: ignore
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
