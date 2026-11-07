"""Connessione a SQLite e migrazioni Alembic (ADR 0004)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

CARTELLA_MIGRAZIONI = Path(__file__).parent / "migrazioni"


def crea_motore(percorso: Path) -> Engine:
    percorso.parent.mkdir(parents=True, exist_ok=True)
    motore = create_engine(f"sqlite:///{percorso}")

    @event.listens_for(motore, "connect")
    def _pragma(connessione, _):
        cursore = connessione.cursor()
        cursore.execute("PRAGMA foreign_keys = ON")
        cursore.close()

    return motore


def migra(motore: Engine) -> None:
    """Porta il database all'ultima versione senza perdere dati."""
    config = Config()
    config.set_main_option("script_location", str(CARTELLA_MIGRAZIONI))
    with motore.connect() as connessione:
        # SQLite ricrea le tabelle per quasi ogni ALTER: con le chiavi esterne attive il DROP della
        # vecchia tabella cancellerebbe a cascata le righe collegate. Il PRAGMA vale solo fuori transazione.
        connessione.exec_driver_sql("PRAGMA foreign_keys = OFF")
        connessione.commit()
        try:
            with connessione.begin():
                config.attributes["connection"] = connessione
                command.upgrade(config, "head")
        finally:
            connessione.exec_driver_sql("PRAGMA foreign_keys = ON")
            connessione.commit()


def fabbrica_sessioni(motore: Engine) -> sessionmaker[Session]:
    return sessionmaker(motore, expire_on_commit=False)
