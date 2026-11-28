"""Argomenti e temi (ESE-08, ESE-08b, ESE-10, UI-09): assegnazione, Timeline e azioni dell'utente."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Argomento, Notizia
from gradiens.dati.notizie import adesso

GIORNI_PER_PROMPT, MASSIMO_PER_PROMPT = 30, 100  # ADR 0008
MINIMO_TIMELINE = 2  # UI-09: un argomento con una sola notizia non compare; un tema sì, anche vuoto
MASSIMO_DESCRIZIONE = 1000


@dataclass
class Riassunto:
    """Metadati di un argomento per la Timeline (UI-09)."""

    argomento: Argomento
    notizie: int
    dal: datetime | None  # None per un tema ancora vuoto
    aggiornato: datetime | None
    in_archivio: int
    nuove: int  # arrivate con l'ultima esecuzione
    evoluzione_vecchia: bool  # il riassunto dell'evoluzione non copre più le notizie di oggi (decisione 72)


def per_prompt(sessione: Session) -> tuple[list[Argomento], list[Argomento]]:
    """Temi, tutti (ADR 0015), e argomenti con una notizia scoperta negli ultimi 30 giorni, i più recenti per
    primi (ADR 0008)."""
    temi = list(sessione.scalars(select(Argomento).where(Argomento.tema).order_by(Argomento.nome)))
    ultima = func.max(Notizia.scoperta_il)
    query = (
        select(Argomento)
        .join(Notizia)
        .where(Argomento.tema.is_(False))
        .group_by(Argomento.id)
        .having(ultima >= adesso() - timedelta(days=GIORNI_PER_PROMPT))
        .order_by(ultima.desc())
        .limit(MASSIMO_PER_PROMPT)
    )
    return temi, list(sessione.scalars(query))


def crea(sessione: Session, nome: str) -> Argomento:
    argomento = Argomento(nome=nome.strip()[:200], creato_il=adesso())
    sessione.add(argomento)
    sessione.flush()
    return argomento


def _nome_valido(nome: str) -> str:
    nome = nome.strip()
    if not 1 <= len(nome) <= 200:
        raise ImpostazioneNonValida("Il nome dell'argomento va da 1 a 200 caratteri.")
    return nome


def _descrizione_valida(testo: str) -> str | None:
    testo = testo.strip()
    if len(testo) > MASSIMO_DESCRIZIONE:
        raise ImpostazioneNonValida(f"La descrizione arriva al massimo a {MASSIMO_DESCRIZIONE} caratteri.")
    return testo or None


def crea_tema(sessione: Session, nome: str, descrizione: str = "") -> int:
    """UI-09: un tema nuovo, vuoto; l'LLM ci mette le notizie dalla prossima esecuzione."""
    argomento = Argomento(
        nome=_nome_valido(nome), creato_il=adesso(), tema=True, descrizione=_descrizione_valida(descrizione)
    )
    sessione.add(argomento)
    sessione.commit()
    return argomento.id


def imposta_tema(sessione: Session, id: int, tema: bool) -> bool:
    """Mette o toglie il segno di tema. Un argomento che smette di essere tema senza notizie viene cancellato
    (ESE-10): restituisce False in quel caso."""
    argomento = sessione.get_one(Argomento, id)
    argomento.tema = tema
    rimasto = tema or bool(argomento.notizie)
    if not rimasto:
        sessione.delete(argomento)
    sessione.commit()
    return rimasto


def salva_descrizione(sessione: Session, id: int, testo: str) -> None:
    sessione.get_one(Argomento, id).descrizione = _descrizione_valida(testo)
    sessione.commit()


def _riassunto(a: Argomento, ultima_esecuzione_id: int | None) -> Riassunto:
    date = [n.pubblicata_il for n in a.notizie] or [None]
    nuove = sum(ultima_esecuzione_id is not None and n.esecuzione_id == ultima_esecuzione_id for n in a.notizie)
    vecchia = a.evoluzione_il is not None and (
        len(a.notizie) != a.evoluzione_notizie or any(n.scoperta_il > a.evoluzione_il for n in a.notizie)
    )  # notizie arrivate, scadute o unite da un altro argomento dopo il riassunto
    return Riassunto(a, len(a.notizie), min(date), max(date), sum(n.cuore for n in a.notizie), nuove, vecchia)


def timeline(sessione: Session, ultima_esecuzione_id: int | None) -> list[Riassunto]:
    """UI-09: temi e argomenti con almeno 2 notizie, prima quelli aggiornati più di recente, i temi vuoti per ultimi."""
    elenco = [
        _riassunto(a, ultima_esecuzione_id)
        for a in sessione.scalars(select(Argomento).options(selectinload(Argomento.notizie)))
        if a.tema or len(a.notizie) >= MINIMO_TIMELINE
    ]
    return sorted(elenco, key=lambda r: r.aggiornato or datetime.min, reverse=True)


def riassunto(sessione: Session, id: int, ultima_esecuzione_id: int | None) -> Riassunto | None:
    """Pagina dell'argomento: si apre anche con una sola notizia (es. dal link sulla notizia), un tema anche vuoto."""
    a = sessione.get(Argomento, id)
    return _riassunto(a, ultima_esecuzione_id) if a is not None and (a.notizie or a.tema) else None


def tutti(sessione: Session) -> list[Argomento]:
    """Per la scelta della destinazione di un'unione: gli stessi argomenti della Timeline (UI-09)."""
    query = (
        select(Argomento)
        .outerjoin(Notizia)
        .group_by(Argomento.id)
        .having(or_(Argomento.tema, func.count(Notizia.id) >= MINIMO_TIMELINE))
        .order_by(Argomento.nome)
    )
    return list(sessione.scalars(query))


def rinomina(sessione: Session, id: int, nome: str) -> None:
    sessione.get_one(Argomento, id).nome = _nome_valido(nome)
    sessione.commit()


def unisci(sessione: Session, id: int, destinazione: int) -> None:
    """Le notizie passano nell'argomento di destinazione, che tiene il suo nome. Se uno dei due è un tema la
    destinazione diventa tema, e tiene la sua descrizione o prende quella dell'altro (UI-09)."""
    if id == destinazione:
        raise ImpostazioneNonValida("Scegli un altro argomento.")
    arrivo, partenza = sessione.get_one(Argomento, destinazione), sessione.get_one(Argomento, id)
    arrivo.tema = arrivo.tema or partenza.tema
    arrivo.descrizione = arrivo.descrizione or partenza.descrizione
    sessione.execute(update(Notizia).where(Notizia.argomento_id == id).values(argomento_id=destinazione))
    sessione.delete(partenza)
    sessione.commit()


def imposta_cuore(sessione: Session, id: int, cuore: bool) -> None:
    """Cuore a tutte le notizie dell'argomento (UI-09); quelle che lo hanno già tengono la data del loro cuore."""
    for n in sessione.get_one(Argomento, id).notizie:
        if n.cuore != cuore:
            n.cuore, n.cuore_il = cuore, adesso() if cuore else None
    sessione.commit()


def salva_evoluzione(sessione: Session, id: int, testo: str, notizie: int) -> None:
    a = sessione.get_one(Argomento, id)
    a.evoluzione, a.evoluzione_il, a.evoluzione_notizie = testo, adesso(), notizie
    sessione.commit()


def elimina(sessione: Session, id: int) -> None:
    """Le notizie restano, senza argomento."""
    sessione.execute(update(Notizia).where(Notizia.argomento_id == id).values(argomento_id=None))
    sessione.delete(sessione.get_one(Argomento, id))
    sessione.commit()
