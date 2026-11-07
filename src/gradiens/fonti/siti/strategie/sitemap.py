"""Sitemap XML, da robots.txt e dai percorsi comuni, news sitemap comprese. Servono solo le voci con una data."""

import re
from collections import Counter
from datetime import datetime
from urllib.parse import urljoin

from lxml import etree

from gradiens.fonti import Candidata
from gradiens.fonti.siti.date import da_iso, da_url, nella_finestra
from gradiens.fonti.siti.indirizzi import non_articolo, normalizza, segmenti, sembra_articolo, titolo_da_url
from gradiens.fonti.siti.rete import Navigatore, Pagina
from gradiens.fonti.siti.strategie.raccolta import Raccolta

PERCORSI_COMUNI = ["sitemap_index.xml", "sitemap.xml", "news-sitemap.xml", "sitemap-news.xml"]
# Sitemap figlie di pagine statiche, tassonomie e autori (Yoast, Rank Math, WordPress, Ghost…): niente articoli.
NON_ARTICOLI = re.compile(r"(^|[-_])(pages?|categor\w*|post_tag|tags?|authors?|users?|attachment|taxonomies|products?|labels?)([-_.]|$)", re.I)
DA_PROVARE = 6
MASSIME = 4
FIGLIE_MASSIME = 5
# Niente entità né rete: le sitemap sono dati non fidati.
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, recover=True, huge_tree=False)


def interpreta(pagina: Pagina) -> tuple[str, list[tuple[str, datetime | None, str, bool]]] | None:
    """("indice" | "elenco", [(indirizzo, data, titolo, è una notizia)]), oppure None se non è una sitemap XML."""
    if not pagina.ok or pagina.html or not pagina.dati.strip():
        return None
    try:
        radice = etree.fromstring(pagina.dati, PARSER)
    except etree.XMLSyntaxError:
        return None
    if radice is None or etree.QName(radice).localname not in ("sitemapindex", "urlset"):
        return None
    modifiche = Counter(el.xpath("string(*[local-name()='lastmod'])") for el in radice)
    # Se quasi tutte le voci hanno lo stesso lastmod, la sitemap è stata solo rigenerata: quelle date non dicono nulla.
    frequente, quante = modifiche.most_common(1)[0] if modifiche else ("", 0)
    lastmod_inutile = bool(frequente) and quante >= 10 and quante * 2 >= len(radice)
    voci = []
    for el in radice:
        url = normalizza(el.xpath("string(*[local-name()='loc'])"), pagina.url)
        if not url:
            continue
        notizia = da_iso(el.xpath("string(*[local-name()='news']/*[local-name()='publication_date'])"))
        modifica = None if lastmod_inutile else da_iso(el.xpath("string(*[local-name()='lastmod'])"))
        # lastmod è l'ultima modifica: se l'indirizzo ha la data di pubblicazione, vale quella.
        data = notizia or da_url(url) or modifica
        # Alcuni siti lasciano un ">" del markup in fondo al titolo (redhotcyber.com: "... Bing>").
        titolo = el.xpath("string(*[local-name()='news']/*[local-name()='title'])").strip().rstrip(">").rstrip()
        voci.append((url, data, titolo, notizia is not None))
    return ("indice" if etree.QName(radice).localname == "sitemapindex" else "elenco"), voci


def _non_articoli(url: str) -> bool:
    nome = segmenti(url)[-1] if segmenti(url) else ""
    return NON_ARTICOLI.search(nome) is not None


async def analizza(nav: Navigatore, profilo, pagina: Pagina | None) -> str | None:
    candidati = [u for s in await nav.sitemap_dichiarate(profilo.url)
                 if (u := normalizza(s)) and not u.endswith(".txt") and not _non_articoli(u)]
    if not candidati:
        candidati = [urljoin(profilo.url, "/" + p) for p in PERCORSI_COMUNI]
    if profilo.sezione:
        # Una sitemap di tutto il sito coprirebbe la finestra senza vedere ciò che la sezione elenca (WEB-09).
        candidati = [profilo.url.rstrip("/") + "/sitemap.xml"] + [u for u in candidati if profilo.nel_perimetro(u)]
    candidati.sort(key=lambda u: "news" not in u.lower())  # le news sitemap hanno la data di pubblicazione
    for url in list(dict.fromkeys(candidati))[:DA_PROVARE]:
        if len(profilo.sitemap) >= MASSIME:
            break
        letta = interpreta(await nav.leggi(url))
        if letta and (letta[0] == "indice" and letta[1] or any(v[1] for v in letta[1])):
            profilo.sitemap.append(url)
    return "sitemap" if profilo.sitemap else None


async def raccogli(nav: Navigatore, profilo, dal: datetime) -> Raccolta:
    r = Raccolta()
    for url in profilo.sitemap:
        if not profilo.escluso(url):
            await _leggi(nav, profilo, url, dal, r, figlia=False)
    return r


async def _leggi(nav: Navigatore, profilo, url: str, dal: datetime, r: Raccolta, figlia: bool) -> None:
    pagina = await nav.leggi(url)
    letta = interpreta(pagina)
    if letta is None:
        if pagina.ok:
            r.guasti.append(f"la sitemap {url} non è una sitemap XML")
        else:
            r.errore(pagina, "la sitemap")
        return
    r.riuscita = True
    tipo, voci = letta
    if tipo == "indice":
        if figlia:
            return  # un livello di indici basta
        figlie = [(u, d) for u, d, _, _ in voci if not _non_articoli(u)]
        r.copre |= any(d and not nella_finestra(d, dal) for _, d in figlie)
        recenti = sorted(((u, d) for u, d in figlie if d and nella_finestra(d, dal)), key=lambda f: f[1], reverse=True)
        senza_data = [(u, d) for u, d in figlie if not d][::-1]  # di solito numerate dalla più vecchia: si parte dall'ultima
        for u, _ in (recenti + senza_data)[:FIGLIE_MASSIME]:
            await _leggi(nav, profilo, u, dal, r, figlia=True)
        return
    for u, d, titolo, notizia in voci:
        if d is None:
            continue
        if not nella_finestra(d, dal):
            r.copre = True
        # senza la data di una news sitemap, l'indirizzo deve avere l'aspetto di un articolo (non annunci, pagine…)
        elif profilo.nel_perimetro(u) and (sembra_articolo(u) if not notizia else not non_articolo(u)):
            r.candidate.append(Candidata(
                tipo="sito", url=u, fonte=profilo.dominio, titolo=titolo or titolo_da_url(u),
                sommario="", contenuto="", pubblicata_il=d,
            ))
