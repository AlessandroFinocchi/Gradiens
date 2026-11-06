"""Notizie, pertinenze, cuore e registro delle notizie viste."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from gradiens.dati.modelli import TIPI_NOTIZIA, Notizia, NotiziaVista, Pertinenza

GIORNI_CONSERVAZIONE = 7  # ESE-09


def adesso() -> datetime:
    """Ora in UTC senza fuso, come le date nel database."""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class Filtri:
    """Filtri e ordinamento della pagina Notizie e dell'Archivio (UI-06, UI-07, UI-08)."""

    archivio: bool = False
    tipi: list[str] = field(default_factory=list)  # vuoto = tutti
    interesse_id: int | None = None
    fonte: str | None = None
    giorni: int | None = None  # solo le notizie pubblicate negli ultimi N giorni
    solo_cuore: bool = False
    ordine: str = "pertinenza"  # oppure "data"
    crescente: bool = False


def elenca(sessione: Session, filtri: Filtri, soglia: int) -> list[Notizia]:
    if filtri.interesse_id is None:
        punteggio = (
            select(func.max(Pertinenza.punteggio)).where(Pertinenza.notizia_id == Notizia.id).scalar_subquery()
        )
    else:  # UI-07: con un interesse filtrato conta il suo punteggio
        punteggio = (
            select(Pertinenza.punteggio)
            .where(Pertinenza.notizia_id == Notizia.id, Pertinenza.interesse_id == filtri.interesse_id)
            .scalar_subquery()
        )

    query = select(Notizia).options(selectinload(Notizia.pertinenze).selectinload(Pertinenza.interesse))
    if filtri.archivio:
        query = query.where(Notizia.cuore)
        if filtri.interesse_id is not None:
            query = query.where(punteggio.is_not(None))
    else:  # UI-04: ultimi 7 giorni, almeno un punteggio sopra la soglia (ESE-06)
        query = query.where(
            Notizia.pubblicata_il >= adesso() - timedelta(days=GIORNI_CONSERVAZIONE), punteggio >= soglia
        )
    if filtri.tipi:
        query = query.where(Notizia.tipo.in_([t for t in filtri.tipi if t in TIPI_NOTIZIA]))
    if filtri.fonte:
        query = query.where(Notizia.fonte == filtri.fonte)
    if filtri.giorni:
        query = query.where(Notizia.pubblicata_il >= adesso() - timedelta(days=filtri.giorni))
    if filtri.solo_cuore:
        query = query.where(Notizia.cuore)

    chiave = punteggio if filtri.ordine == "pertinenza" else Notizia.pubblicata_il
    query = query.order_by(chiave.asc() if filtri.crescente else chiave.desc(), Notizia.pubblicata_il.desc())
    return list(sessione.scalars(query))


def fonti(sessione: Session) -> list[str]:
    return list(sessione.scalars(select(Notizia.fonte).distinct().order_by(Notizia.fonte)))


def dettaglio(sessione: Session, id: int) -> Notizia | None:
    query = (
        select(Notizia)
        .where(Notizia.id == id)
        .options(selectinload(Notizia.pertinenze).selectinload(Pertinenza.interesse))
    )
    return sessione.scalars(query).first()


def imposta_cuore(sessione: Session, id: int, cuore: bool) -> Notizia:
    notizia = sessione.get_one(Notizia, id)
    notizia.cuore = cuore
    sessione.commit()
    return notizia


def gia_viste(sessione: Session, urls: list[str]) -> set[str]:
    if not urls:
        return set()
    return set(sessione.scalars(select(NotiziaVista.url).where(NotiziaVista.url.in_(urls))))


def segna_viste(sessione: Session, urls: list[str]) -> None:
    quando = adesso()
    for url in set(urls) - gia_viste(sessione, urls):
        sessione.add(NotiziaVista(url=url, vista_il=quando))
