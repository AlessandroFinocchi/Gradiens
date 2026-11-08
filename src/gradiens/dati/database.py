"""Connessione a SQLite e migrazioni Alembic (ADR 0004)."""

import sqlite3
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
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
        attuale = MigrationContext.configure(connessione).get_current_revision()
        connessione.commit()  # chiude la lettura: la migrazione apre la sua transazione
        if attuale is not None and attuale != ScriptDirectory.from_config(config).get_current_head():
            copia_di_sicurezza(motore, "migrazione", tenute=3)  # il 7 nov una migrazione ha perso dati
        try:
            with connessione.begin():
                config.attributes["connection"] = connessione
                command.upgrade(config, "head")
        finally:
            connessione.exec_driver_sql("PRAGMA foreign_keys = ON")
            connessione.commit()


def fabbrica_sessioni(motore: Engine) -> sessionmaker[Session]:
    return sessionmaker(motore, expire_on_commit=False)


def copia_di_sicurezza(motore: Engine, motivo: str, tenute: int) -> Path:
    """Copia del database in `.gradiens/backup/`, coerente anche mentre l'app scrive (API di backup di SQLite).
    Delle copie con lo stesso motivo ("migrazione", "giornaliera") restano le ultime `tenute`."""
    percorso = Path(motore.url.database)
    cartella = percorso.parent / "backup"
    cartella.mkdir(exist_ok=True)
    copia = cartella / f"gradiens-{datetime.now():%Y%m%d-%H%M%S}-{motivo}.db"
    sorgente, destinazione = sqlite3.connect(percorso), sqlite3.connect(copia)
    try:
        sorgente.backup(destinazione)
    finally:
        sorgente.close()
        destinazione.close()
    for vecchia in sorted(cartella.glob(f"gradiens-*-{motivo}.db"))[:-tenute]:
        vecchia.unlink()
    return copia


def copia_giornaliera(motore: Engine) -> Path | None:
    """Una copia al giorno, anche se Gradiens si riavvia più volte; se ne tengono 7."""
    if list((Path(motore.url.database).parent / "backup").glob(f"gradiens-{datetime.now():%Y%m%d}-*-giornaliera.db")):
        return None
    return copia_di_sicurezza(motore, "giornaliera", tenute=7)
