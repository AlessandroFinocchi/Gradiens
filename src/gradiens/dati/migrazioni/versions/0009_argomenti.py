"""Argomenti (ESE-08, UI-09): tabella e argomento di ogni notizia.

Revisione: 0009
Precedente: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "argomenti",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("creato_il", sa.DateTime, nullable=False),
    )
    with op.batch_alter_table("notizie") as t:
        t.add_column(sa.Column("argomento_id", sa.Integer, nullable=True))
        t.create_foreign_key("fk_notizie_argomento", "argomenti", ["argomento_id"], ["id"], ondelete="SET NULL")
        t.create_index("ix_notizie_argomento_id", ["argomento_id"])


def downgrade() -> None:
    with op.batch_alter_table("notizie") as t:
        t.drop_index("ix_notizie_argomento_id")
        t.drop_constraint("fk_notizie_argomento", type_="foreignkey")
        t.drop_column("argomento_id")
    op.drop_table("argomenti")
