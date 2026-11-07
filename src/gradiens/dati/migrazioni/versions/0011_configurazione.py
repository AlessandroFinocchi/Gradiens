"""Configurazione iniziale completata (UI-11, decisione 55).

Revisione: 0011
Precedente: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.add_column(sa.Column("configurazione_completata", sa.Boolean, nullable=False, server_default=sa.false()))
    # Un Gradiens già in uso, con almeno un interesse, non deve finire nella procedura guidata.
    op.execute("UPDATE impostazioni SET configurazione_completata = 1 WHERE EXISTS (SELECT 1 FROM interessi)")


def downgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.drop_column("configurazione_completata")
