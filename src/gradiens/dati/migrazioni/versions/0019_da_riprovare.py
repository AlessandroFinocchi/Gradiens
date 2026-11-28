"""Notizie da riprovare: i video rimandati perché YouTube ha limitato le richieste.

Revisione: 0019
Precedente: 0018
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notizie_da_riprovare",
        sa.Column("url", sa.String(1000), primary_key=True),
        sa.Column("tipo", sa.String(6), nullable=False),
        sa.Column("fonte", sa.String(200), nullable=False),
        sa.Column("titolo", sa.Text, nullable=False),
        sa.Column("sommario", sa.Text, nullable=False),
        sa.Column("pubblicata_il", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notizie_da_riprovare")
