"""Notizie, pertinenze, cuore e registro delle notizie viste."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from gradiens.dati.modelli import (
    FONTE_DI_TIPO,
    TIPI_NOTIZIA,
    Argomento,
    CanaleYoutube,
    CategoriaArxiv,
    Notizia,
    NotiziaDaRiprovare,
    NotiziaVista,
    Pertinenza,
    Sito,
)

GIORNI_CONSERVAZIONE = 7  # ESE-09
TIPI_DEL_GRUPPO = {g: [t for t, gruppo in FONTE_DI_TIPO.items() if gruppo == g] for g in set(FONTE_DI_TIPO.values())}


def adesso() -> datetime:
    """Ora in UTC senza fuso, come le date nel database."""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class Filtri:
    """Filtri e ordinamento della pagina Notizie e dell'Archivio (UI-06, UI-07, UI-08)."""

    archivio: bool = False
    tipi: list[str] = field(default_factory=list)  # vuoto = tutti
    interessi: list[int] = field(default_factory=list)  # vuoto = tutti; più valori in OR (UI-06)
    fonti: list[str] = field(default_factory=list)  # vuoto = tutte; più valori in OR
    giorni: int | None = None  # solo le notizie pubblicate negli ultimi N giorni
    testo: str = ""  # ricerca: ogni parola deve comparire nel titolo, nella traduzione, nel riassunto o nella fonte
    solo_cuore: bool = False
    ordine: str = "pertinenza"  # oppure "data"
    crescente: bool = False


def soglie_fonti(sessione: Session) -> dict[tuple[str, str], int]:
    """ESE-06, decisione 73: (gruppo, fonte come la scrive la notizia) -> soglia propria della fonte, per le sole
    fonti che ne hanno una. I siti si riconoscono dal dominio, come nelle notizie (`Profilo.dominio`)."""
    soglie = {("arxiv", c.codice): c.soglia for c in sessione.scalars(select(CategoriaArxiv))}
    soglie |= {("youtube", c.nome): c.soglia for c in sessione.scalars(select(CanaleYoutube))}
    for sito in sessione.scalars(select(Sito).where(Sito.soglia.is_not(None))):
        chiave = ("siti", urlsplit(sito.url).netloc.lower().removeprefix("www."))
        # shortcut: due siti dello stesso dominio (es. /blog e /news) non si distinguono: per entrambi vale la
        # più bassa tra quelle impostate. Per pochi siti seguiti basta.
        soglie[chiave] = min(sito.soglia, soglie.get(chiave, sito.soglia))
    return {chiave: soglia for chiave, soglia in soglie.items() if soglia is not None}


def soglia_di(soglie: dict[tuple[str, str], int], generale: int, tipo: str, fonte: str) -> int:
    return soglie.get((FONTE_DI_TIPO[tipo], fonte), generale)


def _soglia_sql(sessione: Session, generale: int):
    """La soglia di ogni notizia nella query: quella della sua fonte, se ne ha una, altrimenti la generale."""
    casi = [
        (and_(Notizia.tipo.in_(TIPI_DEL_GRUPPO[gruppo]), Notizia.fonte == fonte), soglia)
        for (gruppo, fonte), soglia in soglie_fonti(sessione).items()
    ]
    return case(*casi, else_=generale) if casi else generale


def elenca(sessione: Session, filtri: Filtri, soglia: int) -> list[Notizia]:
    # UI-07: conta il punteggio più alto, tra i soli interessi filtrati se ce ne sono
    punteggio = select(func.max(Pertinenza.punteggio)).where(Pertinenza.notizia_id == Notizia.id)
    if filtri.interessi:
        punteggio = punteggio.where(Pertinenza.interesse_id.in_(filtri.interessi))
    punteggio = punteggio.scalar_subquery()

    query = select(Notizia).options(
        selectinload(Notizia.pertinenze).selectinload(Pertinenza.interesse), selectinload(Notizia.argomento)
    )
    if filtri.archivio:
        query = query.where(Notizia.cuore)
        if filtri.interessi:
            query = query.where(punteggio.is_not(None))
    else:  # UI-04: ultimi 7 giorni, almeno un punteggio sopra la soglia della fonte o generale (ESE-06)
        # Senza pertinenze il punteggio è 0: una fonte con soglia 0 mostra anche le notizie lontane da ogni interesse.
        query = query.where(
            Notizia.pubblicata_il >= adesso() - timedelta(days=GIORNI_CONSERVAZIONE),
            func.coalesce(punteggio, 0) >= _soglia_sql(sessione, soglia),
        )
        if filtri.interessi:
            query = query.where(punteggio.is_not(None))
    if filtri.tipi:
        query = query.where(Notizia.tipo.in_([t for t in filtri.tipi if t in TIPI_NOTIZIA]))
    if filtri.fonti:
        query = query.where(Notizia.fonte.in_(filtri.fonti))
    if filtri.giorni:
        query = query.where(Notizia.pubblicata_il >= adesso() - timedelta(days=filtri.giorni))
    if filtri.solo_cuore:
        query = query.where(Notizia.cuore)
    # shortcut: LIKE di SQLite ignora maiuscole e minuscole solo per le lettere senza accento ("È" non trova "è").
    # Per qualche migliaio di notizie basta; con molte di più servirebbe la ricerca full-text (FTS5).
    for parola in filtri.testo.split():
        query = query.where(
            or_(
                *(
                    campo.icontains(parola, autoescape=True)
                    for campo in (Notizia.titolo, Notizia.titolo_it, Notizia.riassunto, Notizia.fonte)
                )
            )
        )

    chiave = punteggio if filtri.ordine == "pertinenza" else Notizia.pubblicata_il
    query = query.order_by(chiave.asc() if filtri.crescente else chiave.desc(), Notizia.pubblicata_il.desc())
    return list(sessione.scalars(query))


def in_evidenza(
    sessione: Session, soglia: int, esecuzione_id: int | None = None, quante: int = 3
) -> dict[str, list[Notizia]]:
    """Per tipo di fonte, le notizie mostrate più pertinenti: quelle scoperte nelle ultime 24 ore
    (Home, UI-02) oppure quelle di un'esecuzione (messaggio Telegram, TG-03)."""
    dal = adesso() - timedelta(hours=24)
    gruppi: dict[str, list[Notizia]] = {"siti": [], "youtube": [], "arxiv": []}
    for n in elenca(sessione, Filtri(), soglia):  # già in ordine di pertinenza
        gruppo = gruppi[FONTE_DI_TIPO[n.tipo]]  # UI-02
        scelta = n.esecuzione_id == esecuzione_id if esecuzione_id is not None else n.scoperta_il >= dal
        if scelta and len(gruppo) < quante:
            gruppo.append(n)
    return gruppi


def nome_fonte(tipo: str, fonte: str, nomi_categorie: dict[str, str]) -> str:
    """Nome mostrato di una fonte: per arXiv quello dato alla categoria nelle Impostazioni, se c'è (ARX-01)."""
    return nomi_categorie.get(fonte, fonte) if tipo == "arxiv" else fonte


def fonti(sessione: Session, tipi: list[str], nomi_categorie: dict[str, str], archivio: bool = False) -> dict[str, str]:
    """Fonti delle notizie dei tipi scelti (tutti se `tipi` è vuoto), come {valore: nome mostrato}.
    Per l'Archivio solo quelle delle notizie con il cuore."""
    query = select(Notizia.tipo, Notizia.fonte).distinct()
    if tipi:
        query = query.where(Notizia.tipo.in_(tipi))
    if archivio:
        query = query.where(Notizia.cuore)
    nomi = {fonte: nome_fonte(tipo, fonte, nomi_categorie) for tipo, fonte in sessione.execute(query)}
    return dict(sorted(nomi.items(), key=lambda voce: voce[1].casefold()))


def cancella_scadute(sessione: Session) -> int:
    """ESE-09: via le notizie senza cuore più vecchie di 7 giorni. Per le date incerte `pubblicata_il`
    è già la data di scoperta. Gli indirizzi restano nel registro delle viste, così non tornano."""
    limite = adesso() - timedelta(days=GIORNI_CONSERVAZIONE)
    risultato = sessione.execute(delete(Notizia).where(Notizia.cuore.is_(False), Notizia.pubblicata_il < limite))
    # ESE-10: argomenti rimasti vuoti; un tema resta (ESE-08b)
    sessione.execute(delete(Argomento).where(~Argomento.notizie.any(), Argomento.tema.is_(False)))
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


def rimanda(sessione: Session, notizia: NotiziaDaRiprovare) -> None:
    """La fonte ha limitato le richieste: la notizia si riprova alle prossime esecuzioni."""
    sessione.merge(notizia)


def da_riprovare(sessione: Session, dal: datetime) -> list[NotiziaDaRiprovare]:
    """Le notizie rimandate ancora da valutare (oggi solo video di YouTube). Si tolgono quelle già viste, uscite
    dalla finestra di raccolta o di un canale tolto dalle fonti."""
    righe = list(sessione.scalars(select(NotiziaDaRiprovare)))
    viste = gia_viste(sessione, [r.url for r in righe])
    canali = set(sessione.scalars(select(CanaleYoutube.nome)))
    restano = []
    for r in righe:
        if r.url in viste or r.pubblicata_il < dal or r.fonte not in canali:
            sessione.delete(r)
        else:
            restano.append(r)
    sessione.commit()
    return restano
