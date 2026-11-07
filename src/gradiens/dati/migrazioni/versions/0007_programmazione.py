"""Orario dell'esecuzione programmata (ESE-01) e sua pausa (TG-10).

Revisione: 0007
Precedente: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.add_column(sa.Column("orario_programmato", sa.String(5), nullable=False, server_default="07:00"))
        t.add_column(sa.Column("programmazione_in_pausa", sa.Boolean, nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.drop_column("programmazione_in_pausa")
        t.drop_column("orario_programmato")
