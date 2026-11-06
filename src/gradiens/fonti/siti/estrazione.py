"""Estrazione di testo e metadati di un articolo (WEB-14, WEB-15). Gli estrattori sono intercambiabili:
il primo di `ESTRATTORI` che restituisce un risultato vince.
"""

import asyncio
import re
from dataclasses import dataclass, replace
from datetime import datetime

import httpx
import trafilatura

from gradiens.fonti import Candidata, ContenutoAssente
from gradiens.fonti.siti.date import da_iso
from gradiens.fonti.siti.indirizzi import titolo_da_url
from gradiens.fonti.siti.rete import VIETATA, Navigatore, Pagina

# Marcature standard dei contenuti a pagamento: schema.org (usata anche da Google) e Open Graph.
PAYWALL = re.compile(r"\"isAccessibleForFree\"\s*:\s*\"?false|article:content_tier\"[^>]*content=\"(locked|metered)", re.I)
DATE = {"outputformat": "%Y-%m-%dT%H:%M:%S%z", "original_date": True, "extensive_search": False}


@dataclass
class Estratto:
    testo: str  # testo pulito, senza HTML
    titolo: str
    descrizione: str
    data: datetime | None


def con_trafilatura(pagina: Pagina) -> Estratto | None:
    doc = trafilatura.bare_extraction(pagina.testo, url=pagina.url, with_metadata=True, include_comments=False,
                                      date_extraction_params=DATE)
    if doc is None:
        return None
    return Estratto(doc.text or "", doc.title or "", doc.description or "", da_iso(doc.date))


ESTRATTORI = [con_trafilatura]


def estrai(pagina: Pagina) -> Estratto | None:
    if not pagina.ok or not pagina.html:
        return None
    return next((e for estrattore in ESTRATTORI if (e := estrattore(pagina))), None)


async def completa(client: httpx.AsyncClient, candidata: Candidata) -> Candidata:
    """Scarica l'articolo: testo pulito, data dai metadati se era incerta, stato del paywall (WEB-20, WEB-23)."""
    pagina = await Navigatore(client).leggi(candidata.url)
    if pagina.bloccata:
        raise ContenutoAssente("accesso bloccato")
    if pagina.codice == VIETATA:
        raise ContenutoAssente("vietato da robots.txt")
    estratto = await asyncio.to_thread(estrai, pagina)  # trafilatura è lenta: non blocca la dashboard
    if not estratto or not estratto.testo.strip():
        raise ContenutoAssente("errore di estrazione")
    nuova = replace(candidata, contenuto=estratto.testo, sommario=candidata.sommario or estratto.descrizione)
    if estratto.titolo and candidata.titolo in ("", titolo_da_url(candidata.url)):
        nuova.titolo = estratto.titolo
    if candidata.data_incerta and estratto.data:
        nuova.pubblicata_il, nuova.data_incerta = estratto.data, False
    if PAYWALL.search(pagina.testo):
        nuova.stato = "contenuto parziale (paywall)"
    return nuova
