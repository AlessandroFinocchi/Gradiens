"""Bot Telegram: nome del bot e chat autorizzata (TG-01, TG-02). Il token sta nel .env.

Revisione: 0008
Precedente: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.add_column(sa.Column("telegram_bot", sa.String(64), nullable=True))
        t.add_column(sa.Column("telegram_chat_id", sa.BigInteger, nullable=True))
        t.add_column(sa.Column("telegram_chat_nome", sa.String(200), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.drop_column("telegram_chat_nome")
        t.drop_column("telegram_chat_id")
        t.drop_column("telegram_bot")
