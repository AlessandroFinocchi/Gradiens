"""Argomenti (ESE-08, ESE-10, UI-09): assegnazione, Timeline e azioni dell'utente."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Argomento, Notizia
from gradiens.dati.notizie import adesso

GIORNI_PER_PROMPT, MASSIMO_PER_PROMPT = 30, 100  # ADR 0008
MINIMO_TIMELINE = 2  # UI-09: un argomento con una sola notizia non compare


@dataclass
class Riassunto:
    """Metadati di un argomento per la Timeline (UI-09)."""

    argomento: Argomento
    notizie: int
    dal: datetime
    aggiornato: datetime
    in_archivio: int
    nuove: int  # arrivate con l'ultima esecuzione


def per_prompt(sessione: Session) -> list[Argomento]:
    """Argomenti con una notizia scoperta negli ultimi 30 giorni, i più recenti per primi (ADR 0008)."""
    ultima = func.max(Notizia.scoperta_il)
    query = (
        select(Argomento).join(Notizia).group_by(Argomento.id)
        .having(ultima >= adesso() - timedelta(days=GIORNI_PER_PROMPT))
        .order_by(ultima.desc()).limit(MASSIMO_PER_PROMPT)
    )
    return list(sessione.scalars(query))


def crea(sessione: Session, nome: str) -> Argomento:
    argomento = Argomento(nome=nome.strip()[:200], creato_il=adesso())
    sessione.add(argomento)
    sessione.flush()
    return argomento


def _riassunto(a: Argomento, ultima_esecuzione_id: int | None) -> Riassunto:
    date = [n.pubblicata_il for n in a.notizie]
    nuove = sum(ultima_esecuzione_id is not None and n.esecuzione_id == ultima_esecuzione_id for n in a.notizie)
    return Riassunto(a, len(a.notizie), min(date), max(date), sum(n.cuore for n in a.notizie), nuove)


def timeline(sessione: Session, ultima_esecuzione_id: int | None) -> list[Riassunto]:
    """UI-09: argomenti con almeno 2 notizie, prima quelli aggiornati più di recente."""
    elenco = [_riassunto(a, ultima_esecuzione_id)
              for a in sessione.scalars(select(Argomento).options(selectinload(Argomento.notizie)))
              if len(a.notizie) >= MINIMO_TIMELINE]
    return sorted(elenco, key=lambda r: r.aggiornato, reverse=True)


def riassunto(sessione: Session, id: int, ultima_esecuzione_id: int | None) -> Riassunto | None:
    """Pagina dell'argomento: si apre anche con una sola notizia (es. dal link sulla notizia)."""
    a = sessione.get(Argomento, id)
    return _riassunto(a, ultima_esecuzione_id) if a is not None and a.notizie else None


def tutti(sessione: Session) -> list[Argomento]:
    """Per la scelta della destinazione di un'unione."""
    return list(sessione.scalars(select(Argomento).where(Argomento.notizie.any()).order_by(Argomento.nome)))


def rinomina(sessione: Session, id: int, nome: str) -> None:
    nome = nome.strip()
    if not 1 <= len(nome) <= 200:
        raise ImpostazioneNonValida("Il nome dell'argomento va da 1 a 200 caratteri.")
    sessione.get_one(Argomento, id).nome = nome
    sessione.commit()


def unisci(sessione: Session, id: int, destinazione: int) -> None:
    """Le notizie passano nell'argomento di destinazione, che tiene il suo nome."""
    if id == destinazione:
        raise ImpostazioneNonValida("Scegli un altro argomento.")
    sessione.get_one(Argomento, destinazione)
    sessione.execute(update(Notizia).where(Notizia.argomento_id == id).values(argomento_id=destinazione))
    sessione.delete(sessione.get_one(Argomento, id))
    sessione.commit()


def elimina(sessione: Session, id: int) -> None:
    """Le notizie restano, senza argomento."""
    sessione.execute(update(Notizia).where(Notizia.argomento_id == id).values(argomento_id=None))
    sessione.delete(sessione.get_one(Argomento, id))
    sessione.commit()

