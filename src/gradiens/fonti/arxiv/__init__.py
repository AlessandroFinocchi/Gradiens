"""Fonte arXiv tramite l'API ufficiale, che restituisce un feed Atom (PRD ARX-01..04)."""

import asyncio
import calendar
import logging
import re
from datetime import UTC, datetime

import feedparser
import httpx

from gradiens.fonti import USER_AGENT, Candidata

API = "https://export.arxiv.org/api/query"
PER_PAGINA = 200
PAGINE_MASSIME = 20  # 4000 paper: oltre è quasi certamente un errore di configurazione
PAUSA = 3.0  # secondi tra due richieste, come chiede arXiv
ATTESE = (10.0, 30.0, 90.0)  # secondi prima di ogni nuovo tentativo dopo un 429 (troppe richieste) o un 5xx
ATTESA_MASSIMA = 300.0  # tetto al Retry-After di arXiv: l'esecuzione non resta ferma per ore
VERSIONE = re.compile(r"v\d+$")

log = logging.getLogger(__name__)


def _spazi(testo: str) -> str:
    return " ".join(testo.split())


def interpreta(atom: str, categorie: list[str]) -> list[Candidata]:
    """Notizie candidate da una risposta Atom dell'API di arXiv. La fonte è la categoria seguita che ha
    fatto trovare il paper: quella primaria può essere un'altra, se il paper è anche nelle seguite (ARX-01)."""
    candidate = []
    for voce in feedparser.parse(atom).entries:
        if "published_parsed" not in voce or not voce.get("id"):
            continue
        url = VERSIONE.sub("", voce.id.replace("http://", "https://"))  # 2411.01234v2 -> 2411.01234
        if not url.startswith("https://arxiv.org/abs/"):  # dato esterno: finisce in un link della dashboard
            continue
        abstract = _spazi(voce.get("summary", ""))
        primaria = voce.get("arxiv_primary_category", {}).get("term", "arXiv")
        categoria = next(
            (c for c in [primaria, *(tag.term for tag in voce.get("tags", []))] if c in categorie), primaria
        )
        candidate.append(
            Candidata(
                tipo="arxiv",
                url=url,
                fonte=categoria,
                titolo=_spazi(voce.get("title", "")),
                sommario=abstract,
                contenuto=abstract,
                pubblicata_il=datetime.fromtimestamp(calendar.timegm(voce.published_parsed), UTC).replace(tzinfo=None),
            )
        )
    return candidate


async def _scarica(client: httpx.AsyncClient, params: dict) -> httpx.Response:
    """Una pagina dell'API. Se arXiv chiede di rallentare (429), ha un guasto (5xx) o non risponde in tempo
    si aspetta e si riprova: un rifiuto passeggero non deve far perdere i paper di un giorno."""
    for attesa in (*ATTESE, None):
        try:
            risposta = await client.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
        except httpx.TransportError as errore:  # es. ReadTimeout dopo un 429 (26 nov): passeggero come un 5xx
            if attesa is None:
                raise
            log.info("arXiv non ha risposto (%s): riprovo tra %.0f s", type(errore).__name__, attesa)
            await asyncio.sleep(attesa)
            continue
        if attesa is None or (risposta.status_code != 429 and risposta.status_code < 500):
            break
        try:
            attesa = min(max(float(risposta.headers["Retry-After"]), 0.0), ATTESA_MASSIMA)
        except KeyError, ValueError:
            pass  # assente o in forma di data: vale l'attesa prevista
        log.info("arXiv ha risposto %s: riprovo tra %.0f s", risposta.status_code, attesa)
        await asyncio.sleep(attesa)
    risposta.raise_for_status()
    return risposta


async def raccogli(client: httpx.AsyncClient, categorie: list[str], dal: datetime) -> list[Candidata]:
    """Paper delle categorie pubblicati da `dal` in poi, dal più recente."""
    if not categorie:
        return []
    query = " OR ".join(f"cat:{c}" for c in categorie)
    trovate: list[Candidata] = []
    for pagina in range(PAGINE_MASSIME):
        if pagina:
            await asyncio.sleep(PAUSA)
        risposta = await _scarica(
            client,
            {
                "search_query": query,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "start": pagina * PER_PAGINA,
                "max_results": PER_PAGINA,
            },
        )
        blocco = interpreta(risposta.text, categorie)
        trovate += [c for c in blocco if c.pubblicata_il >= dal]
        if len(blocco) < PER_PAGINA or blocco[-1].pubblicata_il < dal:
            break
    return trovate
