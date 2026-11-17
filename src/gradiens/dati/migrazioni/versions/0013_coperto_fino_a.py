"""Raccolta incrementale dei siti (ADR 0011): "coperto fino a" e l'impronta di finestra e profilo di allora.

Due colonne nuove e vuote: alla prima raccolta dopo l'aggiornamento ogni sito cerca nella finestra intera.
`ADD COLUMN` non ricrea la tabella, quindi non tocca le righe esistenti.

Revisione: 0013
Precedente: 0012
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("siti", sa.Column("coperto_fino_a", sa.DateTime, nullable=True))
    op.add_column("siti", sa.Column("coperto_con", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("siti") as t:
        t.drop_column("coperto_con")
        t.drop_column("coperto_fino_a")
