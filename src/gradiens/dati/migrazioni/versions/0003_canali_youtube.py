"""Fetta 2: canali YouTube.

Revisione: 0003
Precedente: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canali_youtube",
        sa.Column("id", sa.String(24), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("canali_youtube")
