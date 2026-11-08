"""Richieste rispettose ai siti (WEB-17..20): robots.txt prima di tutto, pause per dominio, un nuovo
tentativo, cache HTTP, tetto di pagine. Le protezioni (paywall, captcha, anti-bot) non si aggirano: si riconoscono.
"""

import asyncio
import re
import time
import zlib
from dataclasses import dataclass
from functools import cached_property
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from gradiens.fonti import USER_AGENT
from gradiens.fonti.siti.indirizzi import indirizzo_pubblico

PAUSA = 1.0  # secondi tra due richieste allo stesso dominio
PAUSA_MASSIMA = 10.0  # tetto al Crawl-delay chiesto dal sito
TIMEOUT = 20.0
DIMENSIONE_MASSIMA = 15_000_000  # byte: oltre è quasi certamente un errore, non un feed o una pagina
REDIRECT_MASSIMI = 5
DURATA_ROBOTS = 3600.0
VOCI_CACHE = 500

# Codici speciali di `Pagina.codice` (quelli veri sono 100-599).
ERRORE_RETE, VIETATA, TETTO = 0, -1, -2

# Stato condiviso dal processo: le esecuzioni periodiche girano nello stesso processo dell'app.
_robots: dict[str, tuple[float, RobotFileParser | None, bool]] = {}  # origine -> (scadenza, regole, tutto vietato)
_prossima: dict[str, float] = {}  # host -> primo istante libero per una richiesta
_cache: dict[str, tuple[dict[str, str], "Pagina"]] = {}  # url -> (intestazioni di convalida, pagina)


@dataclass
class Pagina:
    url: str  # indirizzo finale, dopo i redirect
    codice: int
    dati: bytes = b""
    tipo: str = ""  # Content-Type
    redirect: str = ""  # Location, per i 3xx

    @property
    def ok(self) -> bool:
        return 200 <= self.codice < 300

    @property
    def bloccata(self) -> bool:
        """Il sito rifiuta i client automatici (WEB-20): si segnala, non si aggira."""
        if self.codice in (401, 403, 429):
            return True
        return self.codice == 503 and re.search(rb"captcha|challenge|cf-chl", self.dati[:20000], re.I) is not None

    @property
    def html(self) -> bool:
        """Conta il contenuto prima del Content-Type: alcuni server mandano i feed come text/html."""
        inizio = self.dati.lstrip(b"\xef\xbb\xbf \t\r\n")[:200].lower()
        if inizio.startswith((b"<rss", b"<feed", b"<urlset", b"<sitemapindex")) or (
                inizio.startswith(b"<?xml") and b"<html" not in self.dati[:1000].lower()):  # l'XHTML resta HTML
            return False
        return "html" in self.tipo.lower() or inizio.startswith((b"<!doctype html", b"<html"))

    @cached_property
    def testo(self) -> str:
        """Testo decodificato qualunque sia la codifica (WEB-16): intestazione, poi <meta charset>, poi UTF-8 o cp1252."""
        dichiarate = re.findall(r"charset=[\"']?([\w-]+)", self.tipo, re.I)
        dichiarate += [m.decode() for m in re.findall(rb"<meta[^>]+charset=[\"']?([\w-]+)", self.dati[:4096], re.I)]
        for codifica in dichiarate + ["utf-8"]:
            try:
                return self.dati.decode(codifica)
            except (LookupError, UnicodeDecodeError):
                continue
        return self.dati.decode("cp1252", errors="replace")


def _origine(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


class Navigatore:
    """Legge le pagine di un sito per conto di una singola analisi, raccolta o estrazione."""

    def __init__(self, client: httpx.AsyncClient, pagine_massime: int = 40):
        self.client = client
        self.pagine_massime = pagine_massime
        self.letture = 0
        self._senza_rete: set[str] = set()  # origini il cui robots.txt non ha risposto per un errore di rete

    async def consentito(self, url: str) -> bool:
        """robots.txt (RFC 9309): 4xx = tutto permesso, 5xx o rete irraggiungibile = tutto vietato."""
        regole, vietato = await self._regole(_origine(url))
        return not vietato and (regole is None or regole.can_fetch(USER_AGENT, url))

    async def sitemap_dichiarate(self, url: str) -> list[str]:
        regole, _ = await self._regole(_origine(url))
        return (regole.site_maps() or []) if regole else []

    async def _regole(self, origine: str) -> tuple[RobotFileParser | None, bool]:
        scadenza, regole, vietato = _robots.get(origine, (0.0, None, False))
        if scadenza > time.monotonic():
            return regole, vietato
        regole, vietato = None, False
        risposta = await self._scarica(origine + "/robots.txt", seguendo_redirect=True)
        if risposta.codice == ERRORE_RETE:
            # Rete assente (es. PC appena acceso): non si legge niente, ma non è un divieto del sito
            # e non si ricorda, così appena torna la rete il sito si legge di nuovo.
            self._senza_rete.add(origine)
            return None, True
        if risposta.ok:
            regole = RobotFileParser()
            regole.parse(risposta.testo.splitlines())
        elif risposta.codice >= 500 or risposta.codice == 429:
            vietato = True
        _robots[origine] = (time.monotonic() + DURATA_ROBOTS, regole, vietato)
        return regole, vietato

    async def leggi(self, url: str) -> Pagina:
        """GET con robots.txt controllato per ogni dominio toccato, redirect compresi (WEB-17)."""
        for _ in range(REDIRECT_MASSIMI + 1):
            if self.letture >= self.pagine_massime:
                return Pagina(url, TETTO)
            if not await self.consentito(url):
                return Pagina(url, ERRORE_RETE if _origine(url) in self._senza_rete else VIETATA)
            self.letture += 1
            pagina = await self._scarica(url)
            if pagina.codice not in (301, 302, 303, 307, 308):
                return pagina
            destinazione = urljoin(url, pagina.redirect)
            parti = urlsplit(destinazione)
            if parti.scheme not in ("http", "https") or not indirizzo_pubblico(parti.hostname or ""):
                return Pagina(url, ERRORE_RETE)  # anche un redirect verso la rete di casa si rifiuta
            url = destinazione
        return Pagina(url, ERRORE_RETE)

    async def _scarica(self, url: str, seguendo_redirect: bool = False) -> Pagina:
        """Una richiesta con pausa per dominio e un nuovo tentativo. Senza redirect: `leggi` li segue controllando robots."""
        in_cache = _cache.get(url)
        intestazioni = {"User-Agent": USER_AGENT, **(in_cache[0] if in_cache else {})}
        pagina = Pagina(url, ERRORE_RETE)
        for tentativo in range(2):
            await self._attendi_turno(url)
            try:
                async with self.client.stream("GET", url, headers=intestazioni, timeout=TIMEOUT,
                                              follow_redirects=seguendo_redirect) as r:
                    if r.status_code == 304 and in_cache:
                        return in_cache[1]
                    dati = bytearray()
                    async for blocco in r.aiter_bytes():
                        dati += blocco
                        if len(dati) > DIMENSIONE_MASSIMA:
                            return Pagina(url, ERRORE_RETE)
                    if r.is_redirect and not seguendo_redirect:
                        return Pagina(url, r.status_code, redirect=r.headers.get("location", ""))
                    pagina = Pagina(str(r.url), r.status_code, _decomprimi(bytes(dati)), r.headers.get("content-type", ""))
                    convalida = {k: r.headers[v] for k, v in (("If-None-Match", "etag"), ("If-Modified-Since", "last-modified"))
                                 if v in r.headers}
            except httpx.HTTPError:
                pagina = Pagina(url, ERRORE_RETE)
                continue
            if tentativo == 0 and (pagina.codice == 429 or pagina.codice >= 500 and not pagina.bloccata):
                continue
            if pagina.ok and convalida and not pagina.html:  # feed e sitemap si rileggono a ogni esecuzione, gli articoli no
                if len(_cache) >= VOCI_CACHE:
                    _cache.pop(next(iter(_cache)))
                _cache[url] = (convalida, pagina)
            return pagina
        return pagina

    async def _attendi_turno(self, url: str) -> None:
        """Riserva il prossimo turno libero del dominio senza await in mezzo, così vale anche con richieste concorrenti."""
        h = urlsplit(url).netloc
        regole, _ = _robots.get(_origine(url), (0.0, None, False))[1:]
        ritardo = regole.crawl_delay(USER_AGENT) if regole else None
        pausa = max(PAUSA, min(float(ritardo or 0), PAUSA_MASSIMA))
        ora = time.monotonic()
        turno = max(ora, _prossima.get(h, 0.0))
        _prossima[h] = turno + pausa
        if turno > ora:
            await asyncio.sleep(turno - ora)


def _decomprimi(dati: bytes) -> bytes:
    """Le sitemap .xml.gz arrivano compresse anche senza Content-Encoding; il limite evita le bombe gzip."""
    if dati[:2] == b"\x1f\x8b":
        try:
            return zlib.decompressobj(wbits=31).decompress(dati, DIMENSIONE_MASSIMA)
        except zlib.error:
            return b""
    return dati
