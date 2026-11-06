"""Finestra delle Impostazioni (UI-10): ogni azione restituisce la finestra aggiornata."""

import json
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from gradiens.dashboard.comune import Sessione, frammento
from gradiens.dati import impostazioni, interessi
from gradiens.dati.impostazioni import ImpostazioneNonValida

# Sezione: (gruppo, nome, icona). Ogni fetta aggiunge le sue.
SEZIONI = {
    "interessi": ("Contenuti", "Interessi", "interessi"),
    "arxiv": ("Contenuti", "arXiv", "arxiv"),
    "esecuzione": ("Funzionamento", "Esecuzione", "esecuzione"),
    "aspetto": ("Interfaccia", "Aspetto", "aspetto"),
}
router = APIRouter(prefix="/impostazioni")


def finestra(request: Request, s: Session, sezione: str, errore: str | None = None) -> HTMLResponse:
    if sezione not in SEZIONI:
        raise HTTPException(404, "Sezione inesistente")
    contesto = {"sezioni": SEZIONI, "sezione": sezione, "imp": impostazioni.leggi(s), "errore": errore}
    if sezione == "interessi":
        contesto["interessi"] = interessi.elenca(s)
    elif sezione == "arxiv":
        contesto["categorie"] = impostazioni.categorie_arxiv(s)
    return frammento(request, "impostazioni", **contesto)


def _esegui(request: Request, s: Session, sezione: str, azione: Callable[[], object]) -> HTMLResponse:
    try:
        azione()
    except ImpostazioneNonValida as errore:
        s.rollback()
        return finestra(request, s, sezione, errore=str(errore))
    except NoResultFound:
        raise HTTPException(404, "Elemento inesistente") from None
    return finestra(request, s, sezione)


Testo = Annotated[str, Form()]
Numero = Annotated[int, Form()]


@router.get("/{sezione}", response_class=HTMLResponse)
def apri(request: Request, s: Sessione, sezione: str):
    return finestra(request, s, sezione)


@router.post("/tema", response_class=HTMLResponse)
def cambia_tema(request: Request, s: Sessione, tema: Annotated[Literal["auto", "light", "dark"], Form()]):
    risposta = _esegui(request, s, "aspetto", lambda: impostazioni.salva_tema(s, tema))
    risposta.headers["HX-Trigger"] = json.dumps({"tema-cambiato": tema})
    return risposta


@router.post("/interessi", response_class=HTMLResponse)
def aggiungi_interesse(request: Request, s: Sessione, nome: Testo, descrizione: Testo):
    return _esegui(request, s, "interessi", lambda: interessi.aggiungi(s, nome, descrizione))


@router.post("/interessi/{id}", response_class=HTMLResponse)
def modifica_interesse(request: Request, s: Sessione, id: int, nome: Testo, descrizione: Testo,
                       raffinamento: Annotated[str, Form()] = ""):
    return _esegui(request, s, "interessi", lambda: interessi.modifica(s, id, nome, descrizione, raffinamento))


@router.post("/interessi/{id}/elimina", response_class=HTMLResponse)
def elimina_interesse(request: Request, s: Sessione, id: int):
    return _esegui(request, s, "interessi", lambda: interessi.elimina(s, id))


@router.post("/arxiv/categorie", response_class=HTMLResponse)
def aggiungi_categoria(request: Request, s: Sessione, codice: Testo):
    return _esegui(request, s, "arxiv", lambda: impostazioni.aggiungi_categoria(s, codice))


@router.post("/arxiv/categorie/rimuovi", response_class=HTMLResponse)
def rimuovi_categoria(request: Request, s: Sessione, codice: Testo):
    return _esegui(request, s, "arxiv", lambda: impostazioni.rimuovi_categoria(s, codice))


@router.post("/arxiv/tetto", response_class=HTMLResponse)
def tetto_arxiv(request: Request, s: Sessione, tetto: Numero):
    return _esegui(request, s, "arxiv", lambda: impostazioni.salva_tetto_arxiv(s, tetto))


@router.post("/esecuzione", response_class=HTMLResponse)
def esecuzione(request: Request, s: Sessione, soglia: Numero, finestra_giorni: Numero):
    return _esegui(request, s, "esecuzione", lambda: impostazioni.salva_esecuzione(s, soglia, finestra_giorni))
