"""Sidebar fissata con un clic sul simbolo di Gradiens (UI-01, decisione 68).

Parte non fissata. `ADD COLUMN` non ricrea la tabella, quindi non tocca la riga esistente.

Revisione: 0015
Precedente: 0014
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("impostazioni", sa.Column("sidebar_fissa", sa.Boolean, nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.drop_column("sidebar_fissa")
