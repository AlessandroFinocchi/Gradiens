"""Fetta 1: interessi, categorie arXiv, notizie, pertinenze, notizie viste, esecuzioni.

Revisione: 0002
Precedente: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("impostazioni") as t:
        t.add_column(sa.Column("soglia", sa.Integer, nullable=False, server_default="60"))
        t.add_column(sa.Column("finestra_giorni", sa.Integer, nullable=False, server_default="7"))
        t.add_column(sa.Column("tetto_arxiv", sa.Integer, nullable=False, server_default="50"))
        t.add_column(sa.Column("provider_prefiltro", sa.String(20), nullable=False, server_default="claude-code"))
        t.add_column(sa.Column("modello_prefiltro", sa.String(60), nullable=False, server_default="haiku"))
        t.add_column(sa.Column("provider_elaborazione", sa.String(20), nullable=False, server_default="claude-code"))
        t.add_column(sa.Column("modello_elaborazione", sa.String(60), nullable=False, server_default="haiku"))

    op.create_table(
        "interessi",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nome", sa.String(80), nullable=False, unique=True),
        sa.Column("descrizione", sa.Text, nullable=False),
        sa.Column("raffinamento", sa.Text),
    )
    op.create_table("categorie_arxiv", sa.Column("codice", sa.String(32), primary_key=True))
    op.create_table(
        "esecuzioni",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("avviata_il", sa.DateTime, nullable=False),
        sa.Column("finita_il", sa.DateTime),
        sa.Column("avviata_da", sa.String(20), nullable=False),
        sa.Column("stato", sa.String(10), nullable=False),
        sa.Column("motivo", sa.Text),
        sa.Column("metriche", sa.Text),
    )
    op.create_table(
        "notizie",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tipo", sa.String(6), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False, unique=True),
        sa.Column("fonte", sa.String(200), nullable=False),
        sa.Column("titolo", sa.Text, nullable=False),
        sa.Column("titolo_it", sa.Text),
        sa.Column("sommario", sa.Text),
        sa.Column("riassunto", sa.Text, nullable=False),
        sa.Column("pubblicata_il", sa.DateTime, nullable=False),
        sa.Column("data_incerta", sa.Boolean, nullable=False),
        sa.Column("scoperta_il", sa.DateTime, nullable=False),
        sa.Column("stato", sa.String(40)),
        sa.Column("cuore", sa.Boolean, nullable=False),
        sa.Column("esecuzione_id", sa.Integer, sa.ForeignKey("esecuzioni.id", ondelete="SET NULL")),
    )
    op.create_index("ix_notizie_cuore", "notizie", ["cuore"])
    op.create_table(
        "pertinenze",
        sa.Column("notizia_id", sa.Integer, sa.ForeignKey("notizie.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("interesse_id", sa.Integer, sa.ForeignKey("interessi.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("punteggio", sa.Integer, nullable=False),
    )
    op.create_table(
        "notizie_viste",
        sa.Column("url", sa.String(1000), primary_key=True),
        sa.Column("vista_il", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    for tabella in ("notizie_viste", "pertinenze", "notizie", "esecuzioni", "categorie_arxiv", "interessi"):
        op.drop_table(tabella)
    with op.batch_alter_table("impostazioni") as t:
        for colonna in ("soglia", "finestra_giorni", "tetto_arxiv", "provider_prefiltro", "modello_prefiltro",
                        "provider_elaborazione", "modello_elaborazione"):
            t.drop_column(colonna)
