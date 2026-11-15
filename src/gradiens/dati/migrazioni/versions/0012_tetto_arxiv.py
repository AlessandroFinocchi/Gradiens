"""Tetto arXiv a 30 (ADR 0010, decisione 9).

Con il pre-filtro che si ferma al tetto il tetto può salire. Passano a 30 il vecchio predefinito (50) e il
tetto usato fino a oggi (10); un tetto scelto diverso resta com'è.

Revisione: 0012
Precedente: 0011
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # La riga delle impostazioni esiste già (0001): conta il valore, non il predefinito della colonna.
    op.execute("UPDATE impostazioni SET tetto_arxiv = 30 WHERE tetto_arxiv IN (10, 50)")


def downgrade() -> None:
    pass  # il valore di prima (10 o 50) non è più noto: 30 resta un tetto valido
