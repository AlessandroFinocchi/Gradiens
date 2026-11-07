"""Configurazione di avvio: percorsi, rete e segreti.

Tutto ciò che l'app salva sta dentro la cartella della repository (PRD PER-02, PER-03):
i segreti in `.env`, i dati in `.gradiens/`. Le impostazioni modificabili dalla dashboard
stanno invece nel database (tabella `impostazioni`).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
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
    file_env: Path = RADICE / ".env"  # dove `salva_segreto` scrive i segreti inseriti dalla dashboard
    telegram_token: SecretStr | None = None  # TG-01; SecretStr non compare in repr e log (PER-04)

    @property
    def percorso_database(self) -> Path:
        return self.cartella_dati / "gradiens.db"

    @property
    def cartella_log(self) -> Path:
        return self.cartella_dati / "log"

    @property
    def indirizzo_locale(self) -> str:
        return f"http://127.0.0.1:{self.porta}"


def salva_segreto(conf: Configurazione, nome: str, valore: str) -> None:
    """Scrive `GRADIENS_<NOME>=valore` nel `.env` lasciando le altre righe (PER-02) e aggiorna `conf`.
    Il valore va validato prima: non deve contenere a capo."""
    if "\n" in valore or "\r" in valore:
        raise ValueError("Valore non valido per il .env")
    chiave = f"GRADIENS_{nome.upper()}="
    righe = conf.file_env.read_text(encoding="utf-8").splitlines() if conf.file_env.exists() else []
    righe = [r for r in righe if not r.startswith(chiave)] + [chiave + valore]
    conf.file_env.write_text("\n".join(righe) + "\n", encoding="utf-8")
    conf.file_env.chmod(0o600)  # solo l'utente del PC lo legge (su Windows lascia il file scrivibile)
    setattr(conf, nome, SecretStr(valore))


@lru_cache
def configurazione() -> Configurazione:
    return Configurazione()
