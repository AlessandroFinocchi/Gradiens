"""Tabella delle impostazioni, con la sua unica riga.

Revisione: 0001
Precedente:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    tabella = op.create_table(
        "impostazioni",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tema", sa.String(5), nullable=False, server_default="auto"),
        sa.CheckConstraint("tema IN ('auto', 'light', 'dark')", name="tema_valido"),
    )
    op.bulk_insert(tabella, [{"id": 1, "tema": "auto"}])


def downgrade() -> None:
    op.drop_table("impostazioni")
