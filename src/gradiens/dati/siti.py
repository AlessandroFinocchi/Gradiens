"""Siti seguiti e il loro profilo (PRD WEB-02, WEB-24..26). Il profilo è un JSON di `fonti.siti.Profilo`."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gradiens.dati import notizie
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


def aggiorna_dettaglio(sessione: Session, id: int, dettaglio: str) -> None:
    """Cambia solo la spiegazione dell'ultimo esito, es. dopo una rigenerazione che ha tenuto il profilo vecchio."""
    sessione.get_one(Sito, id).dettaglio = dettaglio
    sessione.commit()


def salva_rigenerato(sessione: Session, id: int, nuovo: dict) -> None:
    """WEB-25: il profilo vecchio resta per mostrare le differenze; il sito ha lo stato "profilo rigenerato"."""
    sito = sessione.get_one(Sito, id)
    sito.profilo_precedente, sito.profilo = sito.profilo, json.dumps(nuovo, ensure_ascii=False)
    sito.stato, sito.guasti_consecutivi = "profilo rigenerato", 0
    sessione.commit()


# Raccolta incrementale (ADR 0011). "coperto fino a" vale solo con la finestra di raccolta e il profilo di quando è
# stato salvato: l'impronta li ricorda, così un cambio dell'una o dell'altro (anche durante un'esecuzione, anche per
# una rigenerazione) fa ripartire dalla finestra intera senza che chi li cambia debba ricordarsene.


def impronta(finestra_giorni: int, profilo: str) -> str:
    return hashlib.sha256(f"{finestra_giorni}\n{profilo}".encode()).hexdigest()


def partenza(sito: Sito, inizio_finestra: datetime, finestra_giorni: int) -> datetime:
    """Da dove cercare gli articoli: da "coperto fino a", sempre dentro la finestra; la finestra intera alla prima
    raccolta, dopo un guasto e dopo un cambio della finestra o del profilo."""
    if sito.coperto_fino_a is None or sito.coperto_con != impronta(finestra_giorni, sito.profilo):
        return inizio_finestra
    return max(inizio_finestra, sito.coperto_fino_a)


@dataclass
class Copertura:
    """La raccolta di un sito in un'esecuzione, per far avanzare "coperto fino a" a fine esecuzione."""

    ora: datetime  # quando è iniziata la raccolta del sito (UTC senza fuso)
    impronta: str | None  # None dopo un guasto: la raccolta successiva riparte dalla finestra intera
    date: dict[str, datetime]  # indirizzo -> data di pubblicazione delle candidate del sito


def salva_coperture(sessione: Session, coperture: dict[int, Copertura]) -> None:
    """A fine esecuzione, anche interrotta o fallita (decisione 34): "coperto fino a" avanza fino all'ora della
    raccolta, ma non oltre la notizia più vecchia del sito che non è nel registro delle viste (rimasta senza esito
    per un errore o un'interruzione), così all'esecuzione dopo la si ritrova."""
    viste = notizie.gia_viste(sessione, [url for c in coperture.values() for url in c.date])
    for id, c in coperture.items():
        if (sito := sessione.get(Sito, id)) is None:  # rimosso durante l'esecuzione
            continue
        if c.impronta is None:
            sito.coperto_fino_a = sito.coperto_con = None
        else:
            sito.coperto_fino_a = min([c.ora, *(data for url, data in c.date.items() if url not in viste)])
            sito.coperto_con = c.impronta
    sessione.commit()
