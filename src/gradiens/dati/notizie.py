"""Notizie, pertinenze, cuore e registro delle notizie viste."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from gradiens.dati.modelli import TIPI_NOTIZIA, Argomento, Notizia, NotiziaVista, Pertinenza

GIORNI_CONSERVAZIONE = 7  # ESE-09
GRUPPI_EVIDENZA = {"sito": "siti", "video": "youtube", "short": "youtube", "arxiv": "arxiv"}  # UI-02


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

    query = select(Notizia).options(selectinload(Notizia.pertinenze).selectinload(Pertinenza.interesse),
                                    selectinload(Notizia.argomento))
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


def in_evidenza(sessione: Session, soglia: int, esecuzione_id: int | None = None,
                quante: int = 3) -> dict[str, list[Notizia]]:
    """Per tipo di fonte, le notizie mostrate più pertinenti: quelle scoperte nelle ultime 24 ore
    (Home, UI-02) oppure quelle di un'esecuzione (messaggio Telegram, TG-03)."""
    dal = adesso() - timedelta(hours=24)
    gruppi: dict[str, list[Notizia]] = {"siti": [], "youtube": [], "arxiv": []}
    for n in elenca(sessione, Filtri(), soglia):  # già in ordine di pertinenza
        gruppo = gruppi[GRUPPI_EVIDENZA[n.tipo]]
        scelta = n.esecuzione_id == esecuzione_id if esecuzione_id is not None else n.scoperta_il >= dal
        if scelta and len(gruppo) < quante:
            gruppo.append(n)
    return gruppi


def nome_fonte(tipo: str, fonte: str, nomi_categorie: dict[str, str]) -> str:
    """Nome mostrato di una fonte: per arXiv quello dato alla categoria nelle Impostazioni, se c'è (ARX-01)."""
    return nomi_categorie.get(fonte, fonte) if tipo == "arxiv" else fonte


def fonti(sessione: Session, tipi: list[str], nomi_categorie: dict[str, str]) -> dict[str, str]:
    """Fonti delle notizie dei tipi scelti (tutti se `tipi` è vuoto), come {valore: nome mostrato}."""
    query = select(Notizia.tipo, Notizia.fonte).distinct()
    if tipi:
        query = query.where(Notizia.tipo.in_(tipi))
    nomi = {fonte: nome_fonte(tipo, fonte, nomi_categorie) for tipo, fonte in sessione.execute(query)}
    return dict(sorted(nomi.items(), key=lambda voce: voce[1].casefold()))


def cancella_scadute(sessione: Session) -> int:
    """ESE-09: via le notizie senza cuore più vecchie di 7 giorni. Per le date incerte `pubblicata_il`
    è già la data di scoperta. Gli indirizzi restano nel registro delle viste, così non tornano."""
    limite = adesso() - timedelta(days=GIORNI_CONSERVAZIONE)
    risultato = sessione.execute(delete(Notizia).where(Notizia.cuore.is_(False), Notizia.pubblicata_il < limite))
    sessione.execute(delete(Argomento).where(~Argomento.notizie.any()))  # ESE-10: argomenti rimasti vuoti
    sessione.commit()
    return risultato.rowcount


def dettaglio(sessione: Session, id: int) -> Notizia | None:
    query = (
        select(Notizia)
        .where(Notizia.id == id)
        .options(selectinload(Notizia.pertinenze).selectinload(Pertinenza.interesse), selectinload(Notizia.argomento))
    )
    return sessione.scalars(query).first()


def imposta_cuore(sessione: Session, id: int, cuore: bool) -> Notizia:
    notizia = sessione.get_one(Notizia, id)
    notizia.cuore, notizia.cuore_il = cuore, adesso() if cuore else None
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
