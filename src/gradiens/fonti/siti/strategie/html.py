"""Esplorazione controllata dell'HTML statico: pagina indicata, sezioni e pagine successive, con profondità
limitata, fermandosi quando gli articoli diventano più vecchi della finestra (WEB-10).
"""

import re
from datetime import datetime

from gradiens.fonti import Candidata
from gradiens.fonti.siti.date import adesso, da_iso, da_testo, da_url, nella_finestra
from gradiens.fonti.siti.indirizzi import host, non_articolo, normalizza, sembra_articolo, titolo_da_url
from gradiens.fonti.siti.pagine import albero, collegamenti, nel_menu, spazi
from gradiens.fonti.siti.rete import Navigatore, Pagina
from gradiens.fonti.siti.strategie.raccolta import Raccolta

PAGINE_PER_ELENCO = 5
ARTICOLI_MINIMI = 3  # sotto questa soglia i link "a forma di articolo" sono probabilmente pagine di servizio
NUMERO_PAGINA = re.compile(r"(/page/|[?&](?:page|paged|p)=)(\d+)", re.I)
PAGINA_IN_FONDO = re.compile(r"(/)(\d{1,3})/?$")
LIVELLI = 5  # quanto risalire dal link per cercarne la data


def articoli(pagina: Pagina, profilo, ora: datetime) -> list[Candidata]:
    """Gli articoli elencati in una pagina: link con l'aspetto di un articolo o con una data accanto."""
    doc = albero(pagina)
    if doc is None:
        return []
    ancore: dict[str, list] = {}
    for url, a in collegamenti(doc, pagina.url):
        # WEB-09: gli articoli elencati da una sezione valgono anche fuori dal suo percorso, ma sullo stesso sito.
        dentro = profilo.nel_perimetro(url) or profilo.sezione and host(url) == profilo.dominio
        if dentro and not nel_menu(a) and not non_articolo(url) and not profilo.escluso(url) and url != pagina.url:
            ancore.setdefault(url, []).append(a)
    trovate = []
    for url, gruppo in ancore.items():
        vicino, testuale = _date_vicine(gruppo[0], pagina.url, ancore.keys(), ora)
        if not (vicino or testuale or sembra_articolo(url)):
            continue  # né data né indirizzo da articolo: è un'altra pagina del sito
        data = vicino or da_url(url) or testuale
        titoli = [spazi(a.xpath("string(.//*[self::h1 or self::h2 or self::h3 or self::h4])") or a.text_content())
                  or a.get("title", "") for a in gruppo]
        trovate.append(Candidata(
            tipo="sito", url=url, fonte=profilo.dominio, titolo=max(titoli, key=len)[:300] or titolo_da_url(url),
            sommario="", contenuto="", pubblicata_il=data or ora, data_incerta=data is None,
        ))
    return trovate


def _date_vicine(a, base: str, articoli, ora: datetime) -> tuple[datetime | None, datetime | None]:
    """Risale dal link finché il contenitore riguarda solo quell'articolo: (data di <time>, data scritta nel testo)."""
    for livello, contenitore in enumerate([a, *a.iterancestors()]):  # spesso il link avvolge tutta la scheda
        link = {normalizza(x.get("href", ""), base) for x in contenitore.iter("a")}
        if livello >= LIVELLI or len(link & articoli) > 1:
            break
        for t in contenitore.iter("time"):
            if d := da_iso(t.get("datetime")):
                return d, None
        testo = " ".join(contenitore.xpath(".//text()[not(ancestor::script) and not(ancestor::style)]"))
        if d := da_testo(spazi(testo)[:400], ora):
            return None, d
    return None, None


def successiva(pagina: Pagina) -> str | None:
    """La pagina successiva dell'elenco: rel="next" o il numero di pagina che segue quello attuale."""
    doc = albero(pagina)
    if doc is None:
        return None
    for href in doc.xpath("//link[@rel='next']/@href | //a[@rel='next']/@href"):
        if url := normalizza(href, pagina.url):
            return url
    base, attuale = _numero(pagina.url)
    for url, _ in collegamenti(doc, pagina.url):
        if _numero(url) == (base, attuale + 1):
            return url
    return None


def _numero(url: str) -> tuple[str, int]:
    """(indirizzo senza il numero di pagina, numero): /page/3, ?page=3 o /sezione/3/; 1 se manca."""
    for schema in (NUMERO_PAGINA, PAGINA_IN_FONDO):
        if m := schema.search(url):
            return (url[:m.start()] + url[m.end():]).rstrip("/"), int(m[2])
    return url.rstrip("/"), 1


async def analizza(nav: Navigatore, profilo, pagina: Pagina | None) -> str | None:
    trovate = articoli(pagina, profilo, adesso()) if pagina else []
    if len(trovate) < ARTICOLI_MINIMI:
        return None
    return "elenco della pagina" if any(not c.data_incerta for c in trovate) else "pagina dell'articolo"


async def raccogli(nav: Navigatore, profilo, dal: datetime) -> Raccolta:
    r = Raccolta()
    ora = adesso()
    visti: set[str] = set()
    for inizio in [profilo.url] + [s for s in profilo.sezioni if not profilo.escluso(s)]:
        url = inizio
        for _ in range(PAGINE_PER_ELENCO):
            if url in visti:
                break
            visti.add(url)
            letta = await nav.leggi(url)
            if not letta.ok:
                r.errore(letta, "la pagina")
                break
            r.riuscita = True
            trovate = articoli(letta, profilo, ora)
            recenti = [c for c in trovate if c.data_incerta or nella_finestra(c.pubblicata_il, dal)]
            r.candidate += recenti
            if len(recenti) < len(trovate):
                r.copre = True
                break  # gli articoli sono diventati più vecchi della finestra
            if not any(not c.data_incerta for c in trovate) or not (url := successiva(letta)):
                break  # senza date non si sa quando fermarsi: niente pagine successive
    return r
