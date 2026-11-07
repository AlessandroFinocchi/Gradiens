"""Esecuzione programmata ogni giorno (ESE-01), con recupero all'avvio, pausa (TG-10) e cancellazione
quotidiana delle notizie scadute (ESE-09).

Le ore sono quelle del PC, senza fuso (`datetime.now()`). Un controllo ogni 30 secondi, invece di
un'attesa lunga fino all'orario, regge cambi dell'ora legale e PC sospeso: conta solo se l'orario
è stato superato tra un controllo e il successivo.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.orm import Session, sessionmaker

from gradiens.dati import esecuzioni, impostazioni, notizie
from gradiens.esecuzione.esecutore import Esecutore, GiaInCorso

log = logging.getLogger(__name__)

INTERVALLO = 30  # secondi tra due controlli


def _scadenza(giorno: datetime, orario: str) -> datetime:
    return datetime.combine(giorno.date(), time.fromisoformat(orario))


class Programmatore:
    def __init__(self, sessioni: sessionmaker[Session], esecutore: Esecutore,
                 adesso: Callable[[], datetime] = datetime.now):
        self._sessioni = sessioni
        self._esecutore = esecutore
        self._adesso = adesso
        self._ultimo_controllo: datetime | None = None

    def prossima(self) -> datetime | None:
        """Prossima esecuzione programmata, oppure None se la programmazione è in pausa (CLI-03)."""
        with self._sessioni() as s:
            imp = impostazioni.leggi(s)
        if imp.programmazione_in_pausa:
            return None
        adesso = self._adesso()
        oggi = _scadenza(adesso, imp.orario_programmato)
        return oggi if oggi > adesso else _scadenza(adesso + timedelta(days=1), imp.orario_programmato)

    def controlla(self) -> None:
        adesso, ultimo = self._adesso(), self._ultimo_controllo
        with self._sessioni() as s:
            if ultimo is None or ultimo.date() != adesso.date():  # ESE-09: almeno una volta al giorno
                notizie.cancella_scadute(s)
            imp = impostazioni.leggi(s)
            scadenza = _scadenza(adesso, imp.orario_programmato)
            if ultimo is None:
                # All'avvio: si recupera l'esecuzione di oggi se l'orario è passato e da allora non ne è partita nessuna.
                da_avviare = adesso >= scadenza and not esecuzioni.avviate_dal(s, scadenza.astimezone(UTC).replace(tzinfo=None))
            else:
                da_avviare = ultimo < scadenza <= adesso
        self._ultimo_controllo = adesso
        if da_avviare and not imp.programmazione_in_pausa:
            try:
                self._esecutore.avvia("programmazione")
            except GiaInCorso:
                log.info("Esecuzione programmata saltata: un'altra è già in corso")

    async def gira(self) -> None:
        while True:
            try:
                self.controlla()
            except Exception:  # un errore (es. database occupato) non deve fermare la programmazione
                log.exception("Controllo della programmazione non riuscito")
            await asyncio.sleep(INTERVALLO)
