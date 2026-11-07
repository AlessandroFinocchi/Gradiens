"""Siti seguiti e il loro profilo (PRD WEB-02, WEB-24..26). Il profilo è un JSON di `fonti.siti.Profilo`."""

import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Sito

GUASTI_PER_RIGENERARE = 3  # WEB-24


def elenca(sessione: Session) -> list[Sito]:
    return list(sessione.scalars(select(Sito).order_by(Sito.url)))


def in_errore(sessione: Session) -> list[Sito]:
    """Siti che all'ultima raccolta non hanno funzionato, per gli avvisi della Home (UI-02)."""
    return list(sessione.scalars(select(Sito).where(Sito.guasti_consecutivi > 0).order_by(Sito.url)))


def aggiungi(sessione: Session, url: str, profilo: dict, stato: str | None = None) -> Sito:
    sito = Sito(url=url, profilo=json.dumps(profilo, ensure_ascii=False), stato=stato)
    sessione.add(sito)
    try:
        sessione.commit()
    except IntegrityError:
        sessione.rollback()
        raise ImpostazioneNonValida(f"Il sito {url} è già tra quelli seguiti.") from None
    return sito


def rimuovi(sessione: Session, id: int) -> None:
    sessione.delete(sessione.get_one(Sito, id))
    sessione.commit()


def salva_profilo(sessione: Session, id: int, profilo: dict) -> None:
    """Profilo modificato dall'utente nelle Impostazioni."""
    sessione.get_one(Sito, id).profilo = json.dumps(profilo, ensure_ascii=False)
    sessione.commit()


def registra_esito(sessione: Session, id: int, stato: str, dettaglio: str, guasto: bool) -> int:
    """Salva l'esito della raccolta e restituisce i guasti consecutivi: "nessun articolo nuovo" li azzera."""
    sito = sessione.get_one(Sito, id)
    sito.stato, sito.dettaglio = stato, dettaglio
    sito.guasti_consecutivi = sito.guasti_consecutivi + 1 if guasto else 0
    sessione.commit()
    return sito.guasti_consecutivi


def salva_rigenerato(sessione: Session, id: int, nuovo: dict) -> None:
    """WEB-25: il profilo vecchio resta per mostrare le differenze; il sito ha lo stato "profilo rigenerato"."""
    sito = sessione.get_one(Sito, id)
    sito.profilo_precedente, sito.profilo = sito.profilo, json.dumps(nuovo, ensure_ascii=False)
    sito.stato, sito.guasti_consecutivi = "profilo rigenerato", 0
    sessione.commit()
