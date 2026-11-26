"""Soglia propria di ogni fonte (ESE-06, decisione 73).

Una colonna facoltativa in siti, canali YouTube e categorie arXiv: vuota vale la soglia generale. `ADD COLUMN` non
ricrea le tabelle, quindi non tocca i dati collegati.

Revisione: 0017
Precedente: 0016
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

TABELLE = ("siti", "canali_youtube", "categorie_arxiv")


def upgrade() -> None:
    for tabella in TABELLE:
        op.add_column(tabella, sa.Column("soglia", sa.Integer, nullable=True))


def downgrade() -> None:
    for tabella in TABELLE:
        with op.batch_alter_table(tabella) as t:
            t.drop_column("soglia")
