"""Lettura dell'HTML delle pagine elenco: link, menu, piattaforma, pagine che richiedono JavaScript."""

import html
import re
from urllib.parse import urlsplit

import lxml.html
from lxml import etree

from gradiens.fonti.siti.indirizzi import di_servizio, host, normalizza, segmenti, sembra_articolo, stesso_dominio
from gradiens.fonti.siti.rete import Pagina

MENU = {"nav", "header", "footer", "aside"}


def albero(pagina: Pagina) -> lxml.html.HtmlElement | None:
    if not pagina.ok or not pagina.html or not pagina.dati.strip():
        return None
    try:
        return lxml.html.document_fromstring(pagina.testo)
    except (etree.ParserError, ValueError):
        return None


def collegamenti(doc: lxml.html.HtmlElement, base: str) -> list[tuple[str, lxml.html.HtmlElement]]:
    """Link http(s) normalizzati, con l'elemento <a> da cui vengono."""
    trovati = []
    for a in doc.iter("a"):
        if url := normalizza(a.get("href", ""), base):
            trovati.append((url, a))
    return trovati


def nel_menu(elemento: lxml.html.HtmlElement) -> bool:
    return any(e.tag in MENU or e.get("role") == "navigation" for e in elemento.iterancestors())


def spazi(testo: str) -> str:
    return " ".join(testo.split())


def testo_semplice(frammento: str) -> str:
    """Testo senza tag di titoli e sommari di feed e API, che contengono HTML."""
    return spazi(html.unescape(re.sub(r"<[^>]*>", " ", frammento or "")))


def piattaforma(pagina: Pagina) -> str:
    """Dal meta generator (un sito WordPress ne ha spesso più d'uno, es. Elementor) o da segni nel codice della pagina."""
    doc = albero(pagina)
    generatori = [g.strip().lower() for g in doc.xpath("//meta[@name='generator']/@content")] if doc is not None else []
    for nome in ("wordpress", "blogger", "substack", "ghost", "hugo", "hexo", "jekyll", "drupal", "joomla", "liferay"):
        if any(nome in g for g in generatori):
            return nome
    t = pagina.testo.lower()
    for segno, nome in (("/wp-content/", "wordpress"), ("/wp-includes/", "wordpress"), ("substackcdn.com", "substack"),
                        ("www.blogger.com/", "blogger"), ("/_next/", "next.js"), ("/o/liferay", "liferay")):
        if segno in t:
            return nome
    return generatori[0].split()[0] if generatori and generatori[0] else ""


def richiede_js(pagina: Pagina) -> bool:
    """Pagina quasi vuota senza script eseguiti: contenitore vuoto di un'app o invito ad attivare JavaScript."""
    doc = albero(pagina)
    if doc is None:
        return False
    for e in doc.xpath("//script|//style|//noscript"):
        e.drop_tree()
    visibile = spazi(doc.text_content())
    return len(visibile) < 300 or bool(re.search(r"enable javascript|attiva(re)? javascript", pagina.testo, re.I))


COMMERCIALE = re.compile(r"offert[ae]|deals?|coupons?|sconti|promo(zioni)?|shop(ping)?|store|sponsor\w*|advertis\w*|pubblicit\w*"
                         r"|black-?friday", re.I)
# Social network e servizi tecnici (feed, avatar, pagamenti): non sono siti di notizie da proporre (WEB-07).
SOCIAL = re.compile(r"(^|\.)(facebook|twitter|x|instagram|linkedin|youtube|youtu|t|telegram|tiktok|whatsapp|reddit|"
                    r"pinterest|github|google|apple|threads|bsky|mastodon|discord|spotify|flipboard|"
                    r"feedburner|feedly|gravatar|wordpress|wp|paypal|patreon|ko-fi|buymeacoffee|bit)\.\w+$")
SEZIONI_MASSIME = 8
COLLEGATI_MASSIMI = 10


def sezioni(doc: lxml.html.HtmlElement, base: str, profilo) -> list[str]:
    """Sezioni da esplorare: per una home le voci di menu del sito, per una sezione le sue sottosezioni."""
    trovate = []
    for url, a in collegamenti(doc, base):
        parti = segmenti(url)
        if profilo.sezione:
            buona = profilo.nel_perimetro(url) and len(parti) > len(segmenti(profilo.url))
        else:
            buona = nel_menu(a) and profilo.nel_perimetro(url) and 1 <= len(parti) <= 2
        # niente articoli, pagine di servizio, numeri di pagina, file (feed, immagini) o offerte
        file = re.search(r"\.(?!html?$|php$|aspx?$)\w{2,5}$", parti[-1]) if parti else None
        if buona and not file and not parti[-1].isdigit() and not sembra_articolo(url) and not di_servizio(url) \
                and not profilo.escluso(url) and not _commerciale(url, a):
            trovate.append(url)
    return list(dict.fromkeys(trovate))[:SEZIONI_MASSIME]


def _voce_commerciale(a) -> bool:
    """Voce di menu come "Offerte" o "Shop"."""
    parole = a.text_content().split()
    return bool(parole) and COMMERCIALE.fullmatch(parole[0]) is not None


def _commerciale(url: str, a) -> bool:
    return any(COMMERCIALE.fullmatch(s) for s in segmenti(url)) or _voce_commerciale(a)


def commerciali(doc: lxml.html.HtmlElement, base: str, profilo) -> list[str]:
    """Sezioni di offerte e pubblicità da proporre come escluse (WEB-21): il percorso fino al segmento commerciale."""
    trovate = []
    for url, a in collegamenti(doc, base):
        if not profilo.nel_perimetro(url):
            continue
        parti = segmenti(url)
        indice = next((i for i, s in enumerate(parti) if COMMERCIALE.fullmatch(s)), None)
        if indice is not None:
            trovate.append(f"https://{urlsplit(url).netloc}/{'/'.join(parti[:indice + 1])}/")
        elif COMMERCIALE.fullmatch(urlsplit(url).netloc.split(".")[0]):
            trovate.append(f"https://{urlsplit(url).netloc}/")  # es. offerte.sito.it
        elif nel_menu(a) and parti and _voce_commerciale(a):
            trovate.append(url)
    return list(dict.fromkeys(trovate))


def collegati(doc: lxml.html.HtmlElement, base: str, profilo) -> list[str]:
    """Domini esterni nei menu del sito (WEB-07), esclusi i social network."""
    trovati = []
    for url, a in collegamenti(doc, base):
        h = host(url)
        if nel_menu(a) and not stesso_dominio(h, profilo.dominio) and not SOCIAL.search(h):
            trovati.append(h)
    return list(dict.fromkeys(trovati))[:COLLEGATI_MASSIMI]
