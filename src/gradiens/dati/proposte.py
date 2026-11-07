"""Proposte di raffinamento e di nuovi interessi (INT-04, INT-06), da approvare, modificare o scartare.

Una proposta nasce da almeno 3 cuori messi dopo l'ultima proposta. Finché una proposta aspetta una
risposta, per quell'interesse (o per gli interessi nuovi) non se ne genera un'altra.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from gradiens.dati import impostazioni, interessi
from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Interesse, Notizia, Pertinenza, Proposta
from gradiens.dati.notizie import adesso

MINIMO_CUORI = 3  # INT-04, e la stessa soglia per INT-06
MASSIMO_NOTIZIE = 10  # notizie mandate all'LLM per una proposta: le più recenti


def pendenti(sessione: Session) -> list[Proposta]:
    return list(sessione.scalars(select(Proposta).order_by(Proposta.creata_il)))


def _cuori(sessione: Session, query, dal) -> list[Notizia]:
    if dal is not None:
        query = query.where(Notizia.cuore_il > dal)
    return list(sessione.scalars(query.order_by(Notizia.cuore_il.desc())))


def da_raffinare(sessione: Session, soglia: int) -> list[tuple[Interesse, list[Notizia]]]:
    """INT-04: interessi senza proposta in sospeso, con almeno 3 cuori nuovi su notizie pertinenti."""
    in_sospeso = {p.interesse_id for p in pendenti(sessione)}
    risultato = []
    for i in interessi.elenca(sessione):
        if i.id in in_sospeso:
            continue
        query = select(Notizia).join(Pertinenza).where(
            Notizia.cuore, Pertinenza.interesse_id == i.id, Pertinenza.punteggio >= soglia)
        if len(notizie := _cuori(sessione, query, i.ultima_proposta_il)) >= MINIMO_CUORI:
            risultato.append((i, notizie))
    return risultato


def senza_interesse(sessione: Session, soglia: int) -> list[Notizia]:
    """INT-06: cuori nuovi su notizie che non superano la soglia per nessun interesse."""
    if any(p.interesse_id is None for p in pendenti(sessione)):
        return []
    sopra = select(Pertinenza.notizia_id).where(Pertinenza.punteggio >= soglia)
    query = select(Notizia).where(Notizia.cuore, Notizia.id.not_in(sopra))
    notizie = _cuori(sessione, query, impostazioni.leggi(sessione).ultima_proposta_interesse_il)
    return notizie if len(notizie) >= MINIMO_CUORI else []


def registra_raffinamento(sessione: Session, interesse: Interesse, testo: str, notizie: int) -> None:
    """Anche senza testo (l'LLM non ha trovato niente da aggiungere) si riparte a contare i cuori."""
    interesse.ultima_proposta_il = adesso()
    if testo.strip() and testo.strip() != (interesse.raffinamento or ""):
        sessione.add(Proposta(interesse_id=interesse.id, testo=testo.strip(), notizie=notizie, creata_il=adesso()))
    sessione.commit()


def registra_interesse(sessione: Session, nome: str, descrizione: str, notizie: int) -> None:
    impostazioni.leggi(sessione).ultima_proposta_interesse_il = adesso()
    if nome.strip() and descrizione.strip():
        sessione.add(Proposta(nome=nome.strip()[:80], testo=descrizione.strip(), notizie=notizie, creata_il=adesso()))
    sessione.commit()


def approva(sessione: Session, id: int, testo: str | None = None, nome: str | None = None) -> None:
    """Con `testo` (e `nome`) l'utente approva la sua versione modificata."""
    p = sessione.get_one(Proposta, id)
    testo = (testo if testo is not None else p.testo).strip()
    if p.interesse is not None:
        if not testo:
            raise ImpostazioneNonValida("Il raffinamento approvato non può essere vuoto: per scartarlo usa Scarta.")
        p.interesse.raffinamento = testo  # la descrizione dell'utente non si tocca (INT-04)
    else:
        interessi.aggiungi(sessione, nome if nome is not None else p.nome or "", testo)
    sessione.delete(p)
    sessione.commit()


def scarta(sessione: Session, id: int) -> None:
    sessione.delete(sessione.get_one(Proposta, id))
    sessione.commit()
