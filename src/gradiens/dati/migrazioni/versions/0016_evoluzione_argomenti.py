"""Riassunto dell'evoluzione di un argomento, chiesto dall'utente (UI-09, decisione 72).

Tre colonne facoltative: il testo, quando è stato scritto e su quante notizie. `ADD COLUMN` non ricrea la tabella,
quindi non tocca le notizie collegate.

Revisione: 0016
Precedente: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("argomenti", sa.Column("evoluzione", sa.Text, nullable=True))
    op.add_column("argomenti", sa.Column("evoluzione_il", sa.DateTime, nullable=True))
    op.add_column("argomenti", sa.Column("evoluzione_notizie", sa.Integer, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("argomenti") as t:
        t.drop_column("evoluzione_notizie")
        t.drop_column("evoluzione_il")
        t.drop_column("evoluzione")
