"""Rotte della dashboard: pagine intere e pezzi di pagina per htmx (ADR 0003)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from gradiens.dati import impostazioni

CARTELLA = Path(__file__).parent
modelli = Jinja2Templates(directory=CARTELLA / "templates")
router = APIRouter()

PAGINE = {
    "home": ("Home", "/"),
    "notizie": ("Notizie", "/notizie"),
    "timeline": ("Timeline", "/timeline"),
    "archivio": ("Archivio", "/archivio"),
}
# Sezioni delle Impostazioni (UI-10): ogni fetta aggiunge le sue.
SEZIONI = {"aspetto": ("Interfaccia", "Aspetto", "aspetto")}


def sessione(request: Request) -> Iterator[Session]:
    with request.app.state.sessioni() as s:
        yield s


Sessione = Annotated[Session, Depends(sessione)]


def pagina(request: Request, s: Session, modello: str, nome: str, **contesto) -> HTMLResponse:
    """Pagina intera: `nome` indica la voce attiva nella sidebar."""
    return modelli.TemplateResponse(
        request, f"{modello}.html", {"pagina": nome, "pagine": PAGINE, "tema": impostazioni.leggi(s).tema, **contesto}
    )


# Pagine che arrivano nelle fette successive (docs/architettura/piano-fase-4.md).
IN_ARRIVO = {  # nome: (indirizzo, titolo, messaggio)
    "home": ("/", "Home", "La Home arriva con la fetta 4: ultima esecuzione, avvisi, notizie in evidenza e storico."),
    "notizie": ("/notizie", "Notizie", "Le notizie arrivano con la fetta 1, a partire da arXiv."),
    "timeline": ("/timeline", "Timeline", "La Timeline arriva con la fetta 6, insieme agli argomenti."),
    "archivio": ("/archivio", "Archivio", "L'archivio arriva con la fetta 1, insieme al cuore."),
    "aiuto": ("/aiuto", "Aiuto", "La guida completa arriva con la fetta 7."),
}


def _in_arrivo(nome: str, titolo: str, messaggio: str):
    def vista(request: Request, s: Sessione) -> HTMLResponse:
        return pagina(request, s, "in_arrivo", nome, titolo=titolo, messaggio=messaggio)

    return vista


for _nome, (_percorso, _titolo, _messaggio) in IN_ARRIVO.items():
    router.add_api_route(_percorso, _in_arrivo(_nome, _titolo, _messaggio), methods=["GET"], response_class=HTMLResponse)


def finestra_impostazioni(request: Request, s: Session, sezione: str) -> HTMLResponse:
    if sezione not in SEZIONI:
        raise HTTPException(404, "Sezione inesistente")
    return modelli.TemplateResponse(
        request,
        "impostazioni.html",
        {"sezioni": SEZIONI, "sezione": sezione, "imp": impostazioni.leggi(s)},
    )


@router.get("/impostazioni/{sezione}", response_class=HTMLResponse)
def apri_impostazioni(request: Request, s: Sessione, sezione: str):
    return finestra_impostazioni(request, s, sezione)


@router.post("/impostazioni/tema", response_class=HTMLResponse)
def cambia_tema(request: Request, s: Sessione, tema: Annotated[Literal["auto", "light", "dark"], Form()]):
    impostazioni.salva_tema(s, tema)
    risposta = finestra_impostazioni(request, s, "aspetto")
    risposta.headers["HX-Trigger"] = json.dumps({"tema-cambiato": tema})
    return risposta


def registra(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=CARTELLA / "static"), name="static")
    app.include_router(router)
