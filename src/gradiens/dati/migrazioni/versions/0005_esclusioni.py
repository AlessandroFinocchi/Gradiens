"""Interruttori di esclusione (WEB-23), entrambi attivi di base.

Revisione: 0005
Precedente: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.add_column(sa.Column("escludi_sponsorizzati", sa.Boolean, nullable=False, server_default=sa.true()))
        t.add_column(sa.Column("escludi_pagamento", sa.Boolean, nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.drop_column("escludi_pagamento")
        t.drop_column("escludi_sponsorizzati")
