"""Un'esecuzione: raccolta, pre-filtro, tetto, valutazione, salvataggio, metriche (PRD sezione 5).

Gira dentro il processo del servizio, una sola alla volta (ESE-02). Ogni notizia si salva appena
valutata, così un'interruzione (spegnimento, quota esaurita) non perde il lavoro già fatto (ESE-12, LLM-06).
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta

import httpx
from sqlalchemy.orm import Session, sessionmaker

from gradiens.dati import esecuzioni, impostazioni, interessi, notizie
from gradiens.dati.modelli import Notizia, Pertinenza
from gradiens.esecuzione import prompt
from gradiens.fonti import Candidata, arxiv
from gradiens.llm import crea_provider
from gradiens.llm.base import ErroreLLM, Provider, QuotaEsaurita

log = logging.getLogger(__name__)

BLOCCO_PREFILTRO = 30  # notizie per chiamata di pre-filtro (ADR 0006)

Raccolta = Callable[[httpx.AsyncClient, list[str], object], Awaitable[list[Candidata]]]


class GiaInCorso(Exception):
    """ESE-02: un'altra esecuzione è in corso."""


@dataclass
class Avanzamento:
    esecuzione_id: int
    fase: str = "raccolta"
    fatti: int = 0
    totale: int = 0


@dataclass
class Metriche:
    """ESE-11, per un tipo di fonte, più i token per ruolo."""

    esaminate: int = 0
    scartate_prefiltro: int = 0
    oltre_tetto: int = 0
    scartate_valutazione: int = 0
    mostrate: int = 0
    errori: int = 0
    token: dict = field(default_factory=lambda: {r: {"ingresso": 0, "uscita": 0} for r in ("prefiltro", "elaborazione")})

    def conta_token(self, ruolo: str, risposta) -> None:
        self.token[ruolo]["ingresso"] += risposta.token_ingresso
        self.token[ruolo]["uscita"] += risposta.token_uscita


class Esecutore:
    def __init__(
        self,
        sessioni: sessionmaker[Session],
        fabbrica_provider: Callable[[str], Provider] = crea_provider,
        raccogli_arxiv: Raccolta = arxiv.raccogli,
    ):
        self._sessioni = sessioni
        self._fabbrica_provider = fabbrica_provider
        self._raccogli_arxiv = raccogli_arxiv
        self.avanzamento: Avanzamento | None = None
        self._compito: asyncio.Task | None = None

    def avvia(self, avviata_da: str) -> int:
        """Crea l'esecuzione e la fa partire in sottofondo. Nessun `await` prima del controllo:
        nel ciclo asyncio controllo e prenotazione sono quindi atomici."""
        if self.avanzamento is not None:
            raise GiaInCorso("Esecuzione già in corso.")
        with self._sessioni() as s:
            id = esecuzioni.inizia(s, avviata_da).id
        self.avanzamento = Avanzamento(esecuzione_id=id)
        self._compito = asyncio.create_task(self._esegui(id))
        return id

    async def attendi(self) -> None:
        if self._compito is not None:
            await self._compito

    async def ferma(self) -> None:
        """Allo spegnimento: interrompe l'esecuzione in corso e la registra come interrotta (ESE-12)."""
        if self._compito is not None and not self._compito.done():
            self._compito.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._compito

    async def _esegui(self, id: int) -> None:
        inizio = time.monotonic()
        metriche = Metriche()
        stato, motivo = "completata", None
        try:
            with self._sessioni() as s:
                await self._pipeline(s, metriche)
        except QuotaEsaurita as errore:
            stato, motivo = "interrotta", str(errore)
        except asyncio.CancelledError:
            stato, motivo = "interrotta", "Gradiens è stato spento durante l'esecuzione."
            raise
        except Exception as errore:  # l'esecuzione fallisce, ma va sempre chiusa con il suo motivo (ESE-13)
            log.exception("Esecuzione %s fallita", id)
            stato, motivo = "fallita", str(errore) or type(errore).__name__
        finally:
            dati = {
                "durata_s": round(time.monotonic() - inizio, 1),
                "arxiv": {k: v for k, v in vars(metriche).items() if k != "token"},
                "token": metriche.token,
            }
            with self._sessioni() as s:
                esecuzioni.termina(s, id, stato, dati, motivo)
            self.avanzamento = None
            log.info("Esecuzione %s %s %s", id, stato, motivo or "")

    async def _pipeline(self, s: Session, m: Metriche) -> None:
        imp = impostazioni.leggi(s)
        elenco_interessi = interessi.elenca(s)
        categorie = impostazioni.categorie_arxiv(s)
        if not elenco_interessi or not categorie:
            raise ValueError("Servono almeno un interesse e una categoria arXiv (Impostazioni).")
        prefiltro = self._fabbrica_provider(imp.provider_prefiltro)
        elaborazione = self._fabbrica_provider(imp.provider_elaborazione)

        # Raccolta (ESE-03): solo la finestra, senza le notizie già viste (ESE-07) né i doppioni.
        dal = notizie.adesso() - timedelta(days=imp.finestra_giorni)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            trovate = await self._raccogli_arxiv(client, categorie, dal)
        viste = notizie.gia_viste(s, [c.url for c in trovate])
        nuove = list({c.url: c for c in trovate if c.url not in viste}.values())
        m.esaminate = len(nuove)

        # Pre-filtro a blocchi (ESE-04, ARX-02).
        blocchi = [nuove[i:i + BLOCCO_PREFILTRO] for i in range(0, len(nuove), BLOCCO_PREFILTRO)]
        self._fase("pre-filtro", len(blocchi))
        sistema = prompt.sistema_prefiltro(elenco_interessi)

        async def filtra(blocco: list[Candidata]) -> list[Candidata]:
            try:
                risposta = await prefiltro.chiedi(sistema=sistema, messaggio=prompt.messaggio_prefiltro(blocco),
                                                  schema=prompt.SCHEMA_PREFILTRO, modello=imp.modello_prefiltro)
            except QuotaEsaurita:
                raise
            except ErroreLLM as errore:  # il blocco non si segna come visto: ci si riprova la volta dopo
                log.warning("Pre-filtro fallito per un blocco di %s notizie: %s", len(blocco), errore)
                m.errori += 1
                return []
            finally:
                self.avanzamento.fatti += 1
            m.conta_token("prefiltro", risposta)
            indici = {i for i in risposta.dati.get("pertinenti", []) if isinstance(i, int) and 0 <= i < len(blocco)}
            scartate = [c.url for n, c in enumerate(blocco) if n not in indici]
            notizie.segna_viste(s, scartate)
            s.commit()
            m.scartate_prefiltro += len(scartate)
            return [blocco[i] for i in sorted(indici)]

        passate = [c for blocco in await _tutti(filtra(b) for b in blocchi) for c in blocco]

        # Tetto arXiv (ARX-03): si elaborano i più recenti; gli altri si considerano visti.
        passate.sort(key=lambda c: c.pubblicata_il, reverse=True)
        oltre = passate[imp.tetto_arxiv:]
        passate = passate[:imp.tetto_arxiv]
        m.oltre_tetto = len(oltre)
        notizie.segna_viste(s, [c.url for c in oltre])
        s.commit()

        # Valutazione completa (ESE-05): ogni notizia si salva appena valutata.
        self._fase("valutazione", len(passate))
        sistema = prompt.sistema_valutazione(elenco_interessi)
        ids_validi = {i.id for i in elenco_interessi}

        async def valuta(c: Candidata) -> None:
            try:
                risposta = await elaborazione.chiedi(sistema=sistema, messaggio=prompt.messaggio_valutazione(c),
                                                     schema=prompt.SCHEMA_VALUTAZIONE, modello=imp.modello_elaborazione)
            except QuotaEsaurita:
                raise
            except ErroreLLM as errore:  # la notizia non si segna come vista: ci si riprova la volta dopo
                log.warning("Valutazione fallita per %s: %s", c.url, errore)
                m.errori += 1
                return
            finally:
                self.avanzamento.fatti += 1
            m.conta_token("elaborazione", risposta)
            self._salva(s, c, risposta.dati, ids_validi, imp.soglia, m)

        await _tutti(valuta(c) for c in passate)

    def _fase(self, fase: str, totale: int) -> None:
        self.avanzamento.fase, self.avanzamento.fatti, self.avanzamento.totale = fase, 0, totale

    @staticmethod
    def _salva(s: Session, c: Candidata, dati: dict, ids_validi: set[int], soglia: int, m: Metriche) -> None:
        # La risposta dell'LLM è dato esterno: si tengono solo interessi esistenti e punteggi 0-100.
        punteggi: dict[int, int] = {}
        for p in dati.get("punteggi", []):
            interesse, valore = p.get("interesse"), p.get("pertinenza")
            if interesse in ids_validi and isinstance(valore, int):
                punteggi[interesse] = max(0, min(100, valore))
        notizie.segna_viste(s, [c.url])
        if not punteggi or max(punteggi.values()) < soglia:  # ESE-06
            m.scartate_valutazione += 1
            s.commit()
            return
        titolo_it = (dati.get("titolo_it") or "").strip()
        s.add(Notizia(
            tipo=c.tipo, url=c.url, fonte=c.fonte, titolo=c.titolo,
            titolo_it=titolo_it if titolo_it and titolo_it != c.titolo else None,
            sommario=c.sommario, riassunto=str(dati.get("riassunto", "")).strip(),
            pubblicata_il=c.pubblicata_il, data_incerta=c.data_incerta, scoperta_il=notizie.adesso(), stato=c.stato,
            pertinenze=[Pertinenza(interesse_id=i, punteggio=v) for i, v in punteggi.items() if v > 0],
        ))
        s.commit()
        m.mostrate += 1


async def _tutti(coroutine) -> list:
    """Esegue in parallelo; al primo errore ferma le altre (la sessione del database è condivisa).
    La quota esaurita esce come tale, non dentro un gruppo di eccezioni."""
    try:
        async with asyncio.TaskGroup() as gruppo:
            compiti = [gruppo.create_task(c) for c in coroutine]
    except* QuotaEsaurita as gruppo:
        raise gruppo.exceptions[0] from None
    return [c.result() for c in compiti]
