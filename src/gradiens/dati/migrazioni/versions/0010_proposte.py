"""Proposte di raffinamento e di nuovi interessi (INT-04, INT-06) e data del cuore.

Revisione: 0010
Precedente: 0009
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposte",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("interesse_id", sa.Integer, sa.ForeignKey("interessi.id", ondelete="CASCADE"), nullable=True),
        sa.Column("testo", sa.Text, nullable=False),
        sa.Column("nome", sa.String(80), nullable=True),
        sa.Column("notizie", sa.Integer, nullable=False),
        sa.Column("creata_il", sa.DateTime, nullable=False),
    )
    with op.batch_alter_table("notizie") as t:
        t.add_column(sa.Column("cuore_il", sa.DateTime, nullable=True))
    # I cuori messi prima di questa versione contano come messi alla scoperta della notizia.
    op.execute("UPDATE notizie SET cuore_il = scoperta_il WHERE cuore")
    with op.batch_alter_table("interessi") as t:
        t.add_column(sa.Column("ultima_proposta_il", sa.DateTime, nullable=True))
    with op.batch_alter_table("impostazioni") as t:
        t.add_column(sa.Column("ultima_proposta_interesse_il", sa.DateTime, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.drop_column("ultima_proposta_interesse_il")
    with op.batch_alter_table("interessi") as t:
        t.drop_column("ultima_proposta_il")
    with op.batch_alter_table("notizie") as t:
        t.drop_column("cuore_il")
    op.drop_table("proposte")
