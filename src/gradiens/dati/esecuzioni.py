"""Registro delle esecuzioni."""

import json

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from gradiens.dati.modelli import Esecuzione
from gradiens.dati.notizie import adesso


def inizia(sessione: Session, avviata_da: str) -> Esecuzione:
    esecuzione = Esecuzione(avviata_il=adesso(), avviata_da=avviata_da, stato="in_corso")
    sessione.add(esecuzione)
    sessione.commit()
    return esecuzione


def termina(sessione: Session, id: int, stato: str, metriche: dict, motivo: str | None = None) -> None:
    esecuzione = sessione.get_one(Esecuzione, id)
    esecuzione.stato, esecuzione.motivo = stato, motivo
    esecuzione.finita_il = adesso()
    esecuzione.metriche = json.dumps(metriche, ensure_ascii=False)
    sessione.commit()


def segna_interrotte(sessione: Session) -> int:
    """All'avvio del servizio, un'esecuzione ancora "in corso" è stata interrotta (ESE-12)."""
    risultato = sessione.execute(
        update(Esecuzione)
        .where(Esecuzione.stato == "in_corso")
        .values(stato="interrotta", finita_il=adesso(), motivo="Gradiens è stato spento durante l'esecuzione.")
    )
    sessione.commit()
    return risultato.rowcount


def ultima(sessione: Session) -> Esecuzione | None:
    return sessione.scalars(select(Esecuzione).order_by(Esecuzione.id.desc()).limit(1)).first()
