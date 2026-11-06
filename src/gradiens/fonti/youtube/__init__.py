"""Fonte YouTube (PRD YT-01..05).

- I video nuovi si leggono dal feed RSS del canale: ha date e descrizioni, ed è una sola richiesta.
- Il resto si scopre in `completa`, solo per i video che passano il pre-filtro:
  `yt-dlp` dice se è uno short o una diretta, `youtube-transcript-api` dà la trascrizione.
  (Il controllo con l'indirizzo /shorts/ non funziona dall'Europa: YouTube reindirizza al consenso cookie.)
"""

import asyncio
import calendar
import re
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import feedparser
import httpx
import yt_dlp
from youtube_transcript_api import (
    AgeRestricted,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    YouTubeTranscriptApi,
)

from gradiens.fonti import USER_AGENT, Candidata, ContenutoAssente, NonAncoraDisponibile

FEED = "https://www.youtube.com/feeds/videos.xml"
ID_CANALE = re.compile(r"^UC[\w-]{22}$")
ID_VIDEO = re.compile(r"^[\w-]{11}$")
DOMINI = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")
LINGUE = ("it", "en")  # trascrizioni preferite; altrimenti la prima disponibile (INT-03: il filtro è multilingue)
# cachedir False: yt-dlp altrimenti scrive in ~/.cache, fuori dalla cartella del progetto (PER-03).
OPZIONI_YTDLP = {"quiet": True, "no_warnings": True, "skip_download": True, "cachedir": False}
# YouTube blocca gli IP che fanno molte richieste ravvicinate: al massimo 2 video completati alla volta.
# Un semaforo per ciclo asyncio: un semaforo resta legato al primo ciclo che lo usa.
_limiti: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _limite() -> asyncio.Semaphore:
    ciclo = asyncio.get_running_loop()
    if ciclo not in _limiti:
        _limiti[ciclo] = asyncio.Semaphore(2)
    return _limiti[ciclo]


@dataclass
class Canale:
    id: str  # UC… (24 caratteri)
    nome: str


def indirizzo_canale(testo: str) -> str:
    """Da quello che incolla l'utente (YT-01) a un indirizzo di YouTube; rifiuta il resto."""
    testo = testo.strip()
    if testo.startswith("@"):
        return f"https://www.youtube.com/{testo}"
    if ID_CANALE.match(testo):
        return f"https://www.youtube.com/channel/{testo}"
    if not testo.startswith(("http://", "https://")):
        testo = "https://" + testo
    if urlparse(testo).hostname not in DOMINI:
        raise ValueError("Non è un indirizzo di YouTube: incolla @nome, /channel/… o il link di un video.")
    return testo


def _info(url: str, piatta: bool = False) -> dict:
    opzioni = {**OPZIONI_YTDLP, **({"extract_flat": True, "playlist_items": "0"} if piatta else {})}
    with yt_dlp.YoutubeDL(opzioni) as ydl:
        return ydl.extract_info(url, download=False, process=False) or {}


async def risolvi_canale(testo: str) -> Canale:
    """YT-01: l'utente incolla @nome, /channel/ID o il link di un video; si ricava il canale."""
    try:
        info = await asyncio.to_thread(_info, indirizzo_canale(testo), True)
    except yt_dlp.utils.DownloadError:
        raise ValueError("Canale non trovato: controlla l'indirizzo.") from None
    id, nome = info.get("channel_id") or "", info.get("channel") or info.get("uploader") or ""
    if not ID_CANALE.match(id) or not nome:
        raise ValueError("Canale non trovato: controlla l'indirizzo.")
    return Canale(id=id, nome=nome)


def interpreta(xml: str, canale: Canale) -> list[Candidata]:
    candidate = []
    for voce in feedparser.parse(xml).entries:
        id = voce.get("yt_videoid", "")
        if not ID_VIDEO.match(id) or "published_parsed" not in voce:
            continue
        candidate.append(Candidata(
            tipo="video",  # se è uno short lo scopre `completa`
            url=f"https://www.youtube.com/watch?v={id}",
            fonte=canale.nome,
            titolo=" ".join(voce.get("title", "").split()),
            sommario=voce.get("summary", "").strip(),
            contenuto="",
            pubblicata_il=datetime.fromtimestamp(calendar.timegm(voce.published_parsed), UTC).replace(tzinfo=None),
        ))
    return candidate


async def raccogli(client: httpx.AsyncClient, canale: Canale, dal: datetime) -> list[Candidata]:
    """Video del canale pubblicati da `dal`."""
    # shortcut: il feed RSS ha solo gli ultimi 15 video; per canali più prolifici leggere /videos con yt-dlp.
    risposta = await client.get(FEED, params={"channel_id": canale.id}, headers={"User-Agent": USER_AGENT}, timeout=30)
    risposta.raise_for_status()
    return [c for c in interpreta(risposta.text, canale) if c.pubblicata_il >= dal]


def _trascrizione(id_video: str) -> str:
    try:
        elenco = YouTubeTranscriptApi().list(id_video)
    except (TranscriptsDisabled, NoTranscriptFound):
        raise ContenutoAssente("trascrizione assente") from None
    except (VideoUnavailable, VideoUnplayable, AgeRestricted):
        raise ContenutoAssente("video non disponibile") from None
    try:
        scelta = elenco.find_transcript(LINGUE)  # preferisce quelle scritte a mano, poi le automatiche (YT-03)
    except NoTranscriptFound:
        scelta = next(iter(elenco), None)
    testo = " ".join(" ".join(s.text.split()) for s in scelta.fetch()) if scelta else ""
    if not testo.strip():
        raise ContenutoAssente("trascrizione assente")
    return testo


async def completa(client: httpx.AsyncClient, c: Candidata) -> Candidata:
    """Tipo (video o short), dirette non ancora concluse (YT-04) e trascrizione (YT-03, YT-05)."""
    async with _limite():
        info = await asyncio.to_thread(_info, c.url)
        if info.get("live_status") in ("is_upcoming", "is_live", "post_live"):
            raise NonAncoraDisponibile("diretta non ancora disponibile")
        c.tipo = "short" if info.get("media_type") == "short" else "video"
        c.contenuto = await asyncio.to_thread(_trascrizione, c.url.rsplit("v=", 1)[1])
    return c
