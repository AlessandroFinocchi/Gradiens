"""Feed RSS/Atom: dai tag rel="alternate", dai link nella pagina (anche su altri domini) e dai percorsi comuni."""

import io
import re
from urllib.parse import urljoin, urlsplit

import feedparser

from gradiens.fonti import Candidata
from gradiens.fonti.siti.date import adesso, da_struct, nella_finestra
from gradiens.fonti.siti.indirizzi import normalizza, titolo_da_url
from gradiens.fonti.siti.pagine import albero, collegamenti, testo_semplice
from gradiens.fonti.siti.rete import Navigatore, Pagina
from gradiens.fonti.siti.strategie.raccolta import Raccolta

PERCORSI_COMUNI = ["feed/", "rss/", "rss.xml", "atom.xml", "feed.xml", "index.xml", "feeds/posts/default"]
SEMBRA_FEED = re.compile(r"(^|[/._-])(rss|atom|feeds?)([/._-]|$)", re.I)
DA_PROVARE = 8
MASSIMI = 5


def interpreta(pagina: Pagina) -> feedparser.FeedParserDict | None:
    """Il feed, oppure None se la risposta non è un feed (es. un 200 con la home in HTML)."""
    if not pagina.ok or pagina.html:
        return None
    f = feedparser.parse(io.BytesIO(pagina.dati))  # da un flusso: feedparser non tratta il testo come un indirizzo
    return f if f.version else None


def candidate(f: feedparser.FeedParserDict, base: str, fonte: str) -> list[Candidata]:
    trovate = []
    for voce in f.entries:
        url = normalizza(voce.get("link", ""), base)
        if not url:
            continue
        data = da_struct(voce.get("published_parsed") or voce.get("updated_parsed"))
        trovate.append(Candidata(
            tipo="sito", url=url, fonte=fonte,
            titolo=testo_semplice(voce.get("title", "")) or titolo_da_url(url),
            sommario=testo_semplice(voce.get("summary", "")), contenuto="",
            pubblicata_il=data or adesso(), data_incerta=data is None,
        ))
    return trovate


def _indirizzi_nella_pagina(doc, base: str) -> list[str]:
    trovati = [normalizza(l.get("href", ""), base)
               for l in doc.xpath("//link[contains(@rel, 'alternate')][contains(@type, 'rss') or contains(@type, 'atom')]")]
    trovati += [u for u, _ in collegamenti(doc, base) if SEMBRA_FEED.search(urlsplit(u).netloc + urlsplit(u).path)]
    return [u for u in dict.fromkeys(trovati) if u and "comment" not in u.lower()]


async def analizza(nav: Navigatore, profilo, pagina: Pagina | None) -> str | None:
    doc = albero(pagina) if pagina else None
    dalla_pagina = _indirizzi_nella_pagina(doc, pagina.url)[:DA_PROVARE] if doc is not None else []
    elencati = {u for u, _ in collegamenti(doc, pagina.url)} if doc is not None else set()
    comuni = [urljoin(profilo.url.rstrip("/") + "/", p) for p in PERCORSI_COMUNI]
    if profilo.sezione:
        comuni += [urljoin(profilo.url, "/" + p) for p in PERCORSI_COMUNI]
    visti: set[str] = set()

    async def valido(url: str) -> bool:
        letta = await nav.leggi(url)
        f = interpreta(letta)
        if f is None or letta.url in visti:
            return False
        visti.add(letta.url)
        voci = candidate(f, letta.url, profilo.dominio)
        # In una sezione si tiene il feed della sezione, non quello di tutto il sito (WEB-09).
        della_sezione = [c for c in voci if profilo.nel_perimetro(c.url) or c.url in elencati]
        return bool(voci) and (not profilo.sezione or len(della_sezione) * 2 >= len(voci))

    for url in dalla_pagina:
        if len(profilo.feed) < MASSIMI and await valido(url):
            profilo.feed.append(url)
    for url in ([] if profilo.feed else dict.fromkeys(comuni)):
        if await valido(url):
            profilo.feed.append(url)
            break  # dai percorsi comuni basta il primo
    return "feed" if profilo.feed else None


async def raccogli(nav: Navigatore, profilo, dal) -> Raccolta:
    r = Raccolta()
    coperti = []
    for url in profilo.feed:
        if profilo.escluso(url):
            continue
        letta = await nav.leggi(url)
        if not letta.ok:
            r.errore(letta, "il feed")
            continue
        f = interpreta(letta)
        if f is None:
            r.guasti.append(f"il feed {url} non è un feed: risponde con " + ("una pagina HTML" if letta.html else "un formato sconosciuto"))
            continue
        r.riuscita = True
        vecchie = False
        for c in candidate(f, letta.url, profilo.dominio):  # le voci possono non essere in ordine di data (ACN)
            if c.data_incerta or nella_finestra(c.pubblicata_il, dal):
                r.candidate.append(c)
            else:
                vecchie = True
        coperti.append(vecchie)
    r.copre = bool(coperti) and all(coperti)
    return r
