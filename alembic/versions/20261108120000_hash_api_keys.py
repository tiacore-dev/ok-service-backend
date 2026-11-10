"""Store API keys as SHA-256 hashes instead of plaintext.

Revision ID: 20261108120000
Revises: 20261107120000

Existing keys are hashed inside PostgreSQL with the built-in ``sha256()``
(PostgreSQL 11+), so plaintext values never pass through Python, alembic
output or bound parameters. The SQL digest is identical to
``app.domain.api_keys.hash_api_key``, so every existing integration keeps
authenticating with its original key.

The plaintext cannot be reconstructed, therefore the downgrade is refused.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261108120000"
down_revision = "20261107120000"
branch_labels = None
depends_on = None

HASH_SQL = "encode(sha256(convert_to(token, 'UTF8')), 'hex')"


def upgrade() -> None:
    op.add_column(
        "api_keys", sa.Column("api_key_hashed", sa.String(64), nullable=True)
    )
    # Pure SQL backfill: no plaintext values are selected or logged.
    op.execute(f"UPDATE api_keys SET api_key_hashed = {HASH_SQL}")
    op.alter_column("api_keys", "api_key_hashed", nullable=False)
    op.create_unique_constraint(
        "uq_api_keys_api_key_hashed", "api_keys", ["api_key_hashed"]
    )
    op.drop_constraint("uq_api_keys_token", "api_keys", type_="unique")
    op.drop_column("api_keys", "token")


def downgrade() -> None:
    raise RuntimeError(
        "Revision 20261108120000 is irreversible: plaintext API keys were "
        "replaced by SHA-256 hashes and cannot be restored. Restore the "
        "api_keys table from a backup taken before the upgrade instead."
    )
