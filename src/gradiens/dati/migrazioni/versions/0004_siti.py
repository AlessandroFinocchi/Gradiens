"""Fetta 3: siti web con il loro profilo.

Revisione: 0004
Precedente: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "siti",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("url", sa.String(1000), nullable=False, unique=True),
        sa.Column("profilo", sa.Text, nullable=False),
        sa.Column("profilo_precedente", sa.Text),
        sa.Column("stato", sa.String(40)),
        sa.Column("dettaglio", sa.Text),
        sa.Column("guasti_consecutivi", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("siti")
