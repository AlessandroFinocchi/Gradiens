"""Interessi dell'utente (PRD INT-01, INT-02, INT-08, INT-09)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Interesse


def elenca(sessione: Session) -> list[Interesse]:
    return list(sessione.scalars(select(Interesse).order_by(Interesse.nome)))


def _pulisci(nome: str, descrizione: str) -> tuple[str, str]:
    nome, descrizione = nome.strip(), descrizione.strip()
    if not nome or not descrizione:
        raise ImpostazioneNonValida("Nome e descrizione sono obbligatori.")
    if len(nome) > 80:
        raise ImpostazioneNonValida("Il nome può avere al massimo 80 caratteri.")
    return nome, descrizione


def _salva(sessione: Session, nome: str) -> None:
    try:
        sessione.commit()
    except IntegrityError:
        sessione.rollback()
        raise ImpostazioneNonValida(f"Esiste già un interesse chiamato «{nome}».") from None


def aggiungi(sessione: Session, nome: str, descrizione: str) -> Interesse:
    nome, descrizione = _pulisci(nome, descrizione)
    interesse = Interesse(nome=nome, descrizione=descrizione)
    sessione.add(interesse)
    _salva(sessione, nome)
    return interesse


def modifica(sessione: Session, id: int, nome: str, descrizione: str, raffinamento: str) -> None:
    nome, descrizione = _pulisci(nome, descrizione)
    interesse = sessione.get_one(Interesse, id)
    interesse.nome, interesse.descrizione = nome, descrizione
    interesse.raffinamento = raffinamento.strip() or None  # INT-05: si può azzerare
    _salva(sessione, nome)


def elimina(sessione: Session, id: int) -> None:
    """Le pertinenze dell'interesse si cancellano a cascata (INT-09)."""
    if len(elenca(sessione)) <= 1:
        raise ImpostazioneNonValida("Deve esistere almeno un interesse.")
    sessione.delete(sessione.get_one(Interesse, id))
    sessione.commit()
