"""Normalizzazione degli indirizzi dei siti (struttura.md: sta in `siti/`, DUP-01)."""

import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

TRACCIAMENTO = re.compile(r"^(utm_\w+|fbclid|gclid|dclid|msclkid|mc_cid|mc_eid|_ga|ref|ref_src|cmpid|ncid|sr_share)$", re.I)
# Segmenti (o loro prima parola: "privacy-policy") di pagine che non sono né articoli né sezioni.
SERVIZIO = {
    "tag", "tags", "author", "autore", "authors", "autori", "page", "pagina", "search", "cerca", "login", "signin",
    "signup", "account", "privacy", "cookie", "cookies", "contatti", "contact", "about", "chi", "feed", "rss", "atom",
    "wp-content", "wp-admin", "wp-json", "newsletter", "subscribe", "abbonati", "user", "users", "profile", "cart", "shop",
    "copyright", "terms", "termini", "legal", "note", "support", "help", "faq", "sitemap", "redazione", "jobs", "careers",
}
TASSONOMIE = {"category", "categoria", "categorie", "categories", "topic", "topics", "archive", "archivio"}  # sezioni, non articoli
DATA_NEL_PERCORSO = re.compile(r"/(20\d\d)[/-](0[1-9]|1[0-2])[/-](0[1-9]|[12]\d|3[01])(?:/|-|$)")


def indirizzo_pubblico(host: str) -> bool:
    """Falso per localhost e per gli IP non pubblici (privati, loopback, link-local, Tailscale): un feed
    non deve poter far leggere all'app la rete di casa (SSRF)."""
    host = host.lower().rstrip(".").strip("[]")
    if host == "localhost" or host.endswith(".localhost"):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True  # un nome di dominio


def normalizza(href: str, base: str = "") -> str | None:
    """Indirizzo canonico https:// senza frammento né parametri di tracciamento; None se non è un indirizzo web.

    Gli indirizzi vengono da pagine non fidate e finiscono come link nella dashboard.
    """
    href = (href or "").strip()
    if not href or re.search(r"[\s<>\"'\\]", href):
        return None
    try:
        parti = urlsplit(urljoin(base, href))  # gestisce anche "//host/percorso" senza protocollo
        porta = parti.port
    except ValueError:
        return None
    if parti.scheme not in ("http", "https") or not parti.hostname or parti.username or parti.password:
        return None
    if not indirizzo_pubblico(parti.hostname):
        return None
    host = parti.hostname.lower().rstrip(".")
    if porta and porta not in (80, 443):
        host = f"{host}:{porta}"
    query = urlencode([(k, v) for k, v in parse_qsl(parti.query, keep_blank_values=True) if not TRACCIAMENTO.match(k)])
    return urlunsplit(("https", host, parti.path or "/", query, ""))


def host(url: str) -> str:
    """Host senza "www.": "https://www.nature.com/x" -> "nature.com"."""
    h = urlsplit(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def chiave(url: str) -> str:
    """Host senza "www." più percorso: serve a confrontare perimetro ed esclusioni ignorando protocollo e query."""
    return host(url) + (urlsplit(url).path or "/")


def dentro(url: str, prefisso: str) -> bool:
    """`url` sta sotto `prefisso` (indirizzo o chiave), rispettando i confini del percorso."""
    k, p = chiave(url), (chiave(prefisso) if "://" in prefisso else prefisso)
    return k == p or k.rstrip("/") == p.rstrip("/") or k.startswith(p.rstrip("/") + "/")


def stesso_dominio(h: str, dominio: str) -> bool:
    """`h` è `dominio` o un suo sottodominio."""
    return h == dominio or h.endswith("." + dominio)


def segmenti(url: str) -> list[str]:
    return [s for s in urlsplit(url).path.split("/") if s]


def di_servizio(url: str) -> bool:
    """Pagina di servizio (tag, autore, pagina successiva, privacy…): né articolo né sezione."""
    for p in segmenti(url):
        parole = p.lower().split("-")
        if p.lower() in SERVIZIO or len(parole) == 2 and parole[0] in SERVIZIO:  # "privacy-policy", non un titolo
            return True
    return False


def non_articolo(url: str) -> bool:
    parti = segmenti(url)
    return not parti or di_servizio(url) or any(p.lower() in TASSONOMIE for p in parti)


def sembra_articolo(url: str) -> bool:
    """Euristica sull'indirizzo: data nel percorso o titolo-slug lungo, e nessun segmento di servizio o tassonomia."""
    if non_articolo(url):
        return False
    if DATA_NEL_PERCORSO.search(urlsplit(url).path):
        return True
    ultimo = re.sub(r"\.\w{2,5}$", "", segmenti(url)[-1])
    parole = [p for p in re.split(r"[-_]", ultimo) if re.search(r"[^\W\d]", p)]
    return len(ultimo) >= 15 and len(parole) >= 3


def titolo_da_url(url: str) -> str:
    """Titolo provvisorio dallo slug, per le notizie che arrivano dalla sitemap senza titolo."""
    parti = segmenti(url)
    slug = re.sub(r"\.\w{2,5}$", "", parti[-1]) if parti else host(url)
    parole = re.sub(r"[-_]+", " ", slug).strip()
    return parole[:1].upper() + parole[1:]
