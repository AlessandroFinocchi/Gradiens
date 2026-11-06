"""Configurazione di avvio: percorsi, rete e segreti.

Tutto ciò che l'app salva sta dentro la cartella della repository (PRD PER-02, PER-03):
i segreti in `.env`, i dati in `.gradiens/`. Le impostazioni modificabili dalla dashboard
stanno invece nel database (tabella `impostazioni`).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/gradiens/app/configurazione.py -> radice della repository.
# Vale perché uv installa il progetto in modalità modificabile, quindi il codice resta qui.
RADICE = Path(__file__).resolve().parents[3]


class Configurazione(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GRADIENS_", env_file=RADICE / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    cartella_dati: Path = RADICE / ".gradiens"
    host: str = "127.0.0.1"
    porta: int = 8765
    # Nomi con cui si può raggiungere la dashboard (difesa dal DNS rebinding).
    host_consentiti: list[str] = ["127.0.0.1", "localhost"]

    @property
    def percorso_database(self) -> Path:
        return self.cartella_dati / "gradiens.db"

    @property
    def cartella_log(self) -> Path:
        return self.cartella_dati / "log"

    @property
    def indirizzo_locale(self) -> str:
        return f"http://127.0.0.1:{self.porta}"


@lru_cache
def configurazione() -> Configurazione:
    return Configurazione()
