"""Lettura e scrittura delle impostazioni modificabili dalla dashboard."""

from sqlalchemy.orm import Session

from gradiens.dati.modelli import TEMI, Impostazioni


def leggi(sessione: Session) -> Impostazioni:
    return sessione.get_one(Impostazioni, 1)


def salva_tema(sessione: Session, tema: str) -> None:
    if tema not in TEMI:
        raise ValueError(f"Tema non valido: {tema!r}")
    leggi(sessione).tema = tema
    sessione.commit()
