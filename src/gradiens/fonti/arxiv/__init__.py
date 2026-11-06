"""Fonte arXiv tramite l'API ufficiale, che restituisce un feed Atom (PRD ARX-01..04)."""

import asyncio
import calendar
import re
from datetime import UTC, datetime

import feedparser
import httpx

from gradiens.fonti import USER_AGENT, Candidata

API = "https://export.arxiv.org/api/query"
PER_PAGINA = 200
PAGINE_MASSIME = 20  # 4000 paper: oltre è quasi certamente un errore di configurazione
PAUSA = 3.0  # secondi tra due richieste, come chiede arXiv
VERSIONE = re.compile(r"v\d+$")


def _spazi(testo: str) -> str:
    return " ".join(testo.split())


def interpreta(atom: str) -> list[Candidata]:
    """Notizie candidate da una risposta Atom dell'API di arXiv."""
    candidate = []
    for voce in feedparser.parse(atom).entries:
        if "published_parsed" not in voce or not voce.get("id"):
            continue
        url = VERSIONE.sub("", voce.id.replace("http://", "https://"))  # 2411.01234v2 -> 2411.01234
        if not url.startswith("https://arxiv.org/abs/"):  # dato esterno: finisce in un link della dashboard
            continue
        abstract = _spazi(voce.get("summary", ""))
        categoria = voce.get("arxiv_primary_category", {}).get("term", "arXiv")
        candidate.append(Candidata(
            tipo="arxiv",
            url=url,
            fonte=categoria,
            titolo=_spazi(voce.get("title", "")),
            sommario=abstract,
            contenuto=abstract,
            pubblicata_il=datetime.fromtimestamp(calendar.timegm(voce.published_parsed), UTC).replace(tzinfo=None),
        ))
    return candidate


async def raccogli(client: httpx.AsyncClient, categorie: list[str], dal: datetime) -> list[Candidata]:
    """Paper delle categorie pubblicati da `dal` in poi, dal più recente."""
    if not categorie:
        return []
    query = " OR ".join(f"cat:{c}" for c in categorie)
    trovate: list[Candidata] = []
    for pagina in range(PAGINE_MASSIME):
        if pagina:
            await asyncio.sleep(PAUSA)
        risposta = await client.get(API, params={
            "search_query": query, "sortBy": "submittedDate", "sortOrder": "descending",
            "start": pagina * PER_PAGINA, "max_results": PER_PAGINA,
        }, headers={"User-Agent": USER_AGENT}, timeout=60)
        risposta.raise_for_status()
        blocco = interpreta(risposta.text)
        trovate += [c for c in blocco if c.pubblicata_il >= dal]
        if len(blocco) < PER_PAGINA or blocco[-1].pubblicata_il < dal:
            break
    return trovate
