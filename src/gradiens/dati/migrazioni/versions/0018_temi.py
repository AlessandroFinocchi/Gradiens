"""Temi: argomenti marcati dall'utente perché raccolgano tutte le notizie su un soggetto ampio (ESE-08b, ADR 0015).

Due colonne sugli argomenti: il segno di tema, falso per quelli che ci sono già, e la descrizione facoltativa.
`ADD COLUMN` non ricrea la tabella, quindi non tocca le notizie collegate.

Revisione: 0018
Precedente: 0017
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("argomenti", sa.Column("tema", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("argomenti", sa.Column("descrizione", sa.Text, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("argomenti") as t:
        t.drop_column("descrizione")
        t.drop_column("tema")
