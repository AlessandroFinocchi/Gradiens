"""Nome facoltativo delle categorie arXiv, mostrato nei filtri al posto del codice (ARX-01).

Revisione: 0006
Precedente: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("categorie_arxiv") as t:
        t.add_column(sa.Column("nome", sa.String(100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("categorie_arxiv") as t:
        t.drop_column("nome")
