"""Accesso da fuori casa con Tailscale Serve (ADR 0013): interruttore e nome Tailscale del PC.

L'accesso parte spento. `ADD COLUMN` non ricrea la tabella, quindi non tocca la riga esistente.

Revisione: 0014
Precedente: 0013
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("impostazioni", sa.Column("accesso_remoto", sa.Boolean, nullable=False, server_default=sa.false()))
    op.add_column("impostazioni", sa.Column("indirizzo_remoto", sa.String(253), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.drop_column("indirizzo_remoto")
        t.drop_column("accesso_remoto")
