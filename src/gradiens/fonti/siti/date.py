"""Date degli articoli: tutte in UTC senza fuso. Una data senza ora vale come mezzanotte (precisione al giorno)."""

import calendar
import re
from datetime import UTC, datetime, time, timedelta

from gradiens.fonti.siti.indirizzi import DATA_NEL_PERCORSO

MESI = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "gen": 1, "mag": 5, "giu": 6, "lug": 7, "ago": 8, "set": 9, "ott": 10, "dic": 12,
}
MESE = r"(gen|jan|feb|mar|apr|ma[gy]|giu|jun|lug|jul|ago|aug|set|sep|ott|oct|nov|dic|dec)[a-z]*\.?"
GIORNO_MESE_ANNO = re.compile(rf"\b(\d{{1,2}})\s+{MESE},?\s+(20\d\d)\b", re.I)
MESE_GIORNO_ANNO = re.compile(rf"\b{MESE}\s+(\d{{1,2}}),?\s+(20\d\d)\b", re.I)
ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
NUMERICA = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d\d|\d\d)\b(?:\D{1,3}(\d{1,2}):(\d\d)\b)?")  # 06/11/26 11:06
RELATIVA = re.compile(
    r"\b(\d+|un|una|uno|a|an|one)\s+(minut|or[ae]|hour|giorn|day|settiman|week|mes[ei]|month)\w*\s+(fa|ago)\b", re.I)
UNITA = {"minut": timedelta(minutes=1), "or": timedelta(hours=1), "hour": timedelta(hours=1), "giorn": timedelta(days=1),
         "day": timedelta(days=1), "settiman": timedelta(weeks=1), "week": timedelta(weeks=1),
         "mes": timedelta(days=30), "month": timedelta(days=30)}


def adesso() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def da_iso(testo: str | None) -> datetime | None:
    """"2026-11-05T10:00:00+01:00", "2026-11-05T09:00Z", "2026-11-05" e simili."""
    try:
        d = datetime.fromisoformat((testo or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.astimezone(UTC).replace(tzinfo=None) if d.tzinfo else d


def da_struct(t) -> datetime | None:
    """Le date di feedparser (`time.struct_time` in UTC)."""
    return datetime.fromtimestamp(calendar.timegm(t), UTC).replace(tzinfo=None) if t else None


def da_url(url: str) -> datetime | None:
    m = DATA_NEL_PERCORSO.search(url)
    return datetime(int(m[1]), int(m[2]), int(m[3])) if m else None


def da_testo(testo: str, ora: datetime) -> datetime | None:
    """Date scritte in un elenco, in italiano o inglese: "21 ottobre 2026", "Oct 21, 2026", "2 giorni fa"."""
    try:
        if m := GIORNO_MESE_ANNO.search(testo):
            return datetime(int(m[3]), MESI[m[2][:3].lower()], int(m[1]))
        if m := MESE_GIORNO_ANNO.search(testo):
            return datetime(int(m[3]), MESI[m[1][:3].lower()], int(m[2]))
        if m := ISO.search(testo):
            return datetime(int(m[1]), int(m[2]), int(m[3]))
        if m := NUMERICA.search(testo):
            return _numerica(m, ora)
    except ValueError:  # es. "31 febbraio"
        return None
    if m := RELATIVA.search(testo):
        quanti = int(m[1]) if m[1].isdigit() else 1
        unita = next(v for k, v in UNITA.items() if m[2].lower().startswith(k))
        return ora - quanti * unita
    t = testo.lower()
    if re.search(r"\b(ieri|yesterday)\b", t):
        return datetime.combine((ora - timedelta(days=1)).date(), time())
    if re.search(r"\b(oggi|today|poco fa|just now)\b", t):
        return datetime.combine(ora.date(), time())
    return None


def _numerica(m: re.Match, ora: datetime) -> datetime | None:
    """Giorno/mese all'europea; mese/giorno solo se l'altra lettura è impossibile o nel futuro.

    shortcut: l'ora scritta è quella locale del sito e si tratta come UTC; basta per una finestra in giorni.
    """
    anno = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
    ore, minuti = (int(m[4]), int(m[5])) if m[4] else (0, 0)
    for giorno, mese in ((int(m[1]), int(m[2])), (int(m[2]), int(m[1]))):
        try:
            d = datetime(anno, mese, giorno, ore, minuti)
        except ValueError:
            continue
        if d <= ora + timedelta(days=1):
            return d
    return None


def nella_finestra(data: datetime, dal: datetime) -> bool:
    """Una data al giorno (mezzanotte) vale per tutto il giorno: non si perde l'articolo di stamattina."""
    if data.time() == time():
        return data.date() >= dal.date()
    return data >= dal
