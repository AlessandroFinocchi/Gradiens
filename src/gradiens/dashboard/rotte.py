"""Rotte delle pagine della dashboard e pezzi di pagina per htmx (ADR 0003)."""

import json
from datetime import UTC

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import QueryParams

from gradiens.dashboard import rotte_impostazioni
from gradiens.dashboard.comune import CARTELLA, TIPI, Sessione, frammento, pagina
from gradiens.dati import esecuzioni, impostazioni, interessi, notizie
from gradiens.dati import siti as dati_siti
from gradiens.dati.modelli import Esecuzione, Notizia
from gradiens.dati.notizie import Filtri
from gradiens.esecuzione.esecutore import GiaInCorso

router = APIRouter()

# Pagine che arrivano nelle fette successive (docs/architettura/piano-fase-4.md).
IN_ARRIVO = {  # nome: (indirizzo, titolo, messaggio)
    "timeline": ("/timeline", "Timeline", "La Timeline arriva con la fetta 6, insieme agli argomenti."),
    "aiuto": ("/aiuto", "Aiuto", "La guida completa arriva con la fetta 7."),
}


def _in_arrivo(nome: str, titolo: str, messaggio: str):
    def vista(request: Request, s: Sessione) -> HTMLResponse:
        return pagina(request, s, "in_arrivo", nome, titolo=titolo, messaggio=messaggio)

    return vista


for _nome, (_percorso, _titolo, _messaggio) in IN_ARRIVO.items():
    router.add_api_route(_percorso, _in_arrivo(_nome, _titolo, _messaggio), methods=["GET"], response_class=HTMLResponse)


# ---------- Home (UI-02) e resoconto di un'esecuzione (UI-03) ----------

@router.get("/", response_class=HTMLResponse)
def home(request: Request, s: Sessione):
    ultima = esecuzioni.ultima(s)
    prossima = request.app.state.programmatore.prossima()
    return pagina(
        request, s, "home", "home",
        prossima=prossima and prossima.astimezone(UTC).replace(tzinfo=None),  # i filtri delle date vogliono UTC
        avanzamento=request.app.state.esecutore.avanzamento,
        ultima=ultima, riepilogo=ultima and esecuzioni.riepilogo(ultima),
        evidenza=notizie.in_evidenza(s, impostazioni.leggi(s).soglia),
        nomi_categorie=impostazioni.nomi_categorie(s),
        siti_in_errore=dati_siti.in_errore(s),
        storico=[(e, esecuzioni.riepilogo(e)) for e in esecuzioni.storico(s)],
    )


@router.get("/esecuzioni/{id}", response_class=HTMLResponse)
def resoconto(request: Request, s: Sessione, id: int):
    esecuzione = s.get(Esecuzione, id)
    if esecuzione is None:
        raise HTTPException(404, "Esecuzione inesistente")
    return pagina(request, s, "resoconto", "home", e=esecuzione, riepilogo=esecuzioni.riepilogo(esecuzione))


# ---------- Notizie e Archivio (UI-04..UI-08) ----------

def _intero(valore: str | None) -> int | None:
    try:
        return int(valore) if valore else None
    except ValueError:  # es. "²": isdigit() lo accetterebbe, int() no
        return None


def leggi_filtri(q: QueryParams, archivio: bool) -> Filtri:
    """I parametri arrivano dall'indirizzo: tutto ciò che non è riconosciuto si ignora."""
    ordine, _, verso = (q.get("ordine") or ("data-desc" if archivio else "pertinenza-desc")).partition("-")
    return Filtri(
        archivio=archivio,
        tipi=[t for t in q.getlist("tipo") if t in TIPI],
        interesse_id=_intero(q.get("interesse")),
        fonte=q.get("fonte") or None,
        giorni=_intero(q.get("giorni")),
        solo_cuore=q.get("cuore") == "1",
        ordine="data" if ordine == "data" else "pertinenza",
        crescente=verso == "asc",
    )


def _elenco(request: Request, s: Sessione, archivio: bool) -> HTMLResponse:
    filtri = leggi_filtri(request.query_params, archivio)
    nomi_categorie = impostazioni.nomi_categorie(s)
    fonti = notizie.fonti(s, filtri.tipi, nomi_categorie)
    if filtri.fonte not in fonti:  # fonte di un tipo non selezionato (UI-06): si ignora
        filtri.fonte = None
    soglia = impostazioni.leggi(s).soglia
    nome = "archivio" if archivio else "notizie"
    return pagina(
        request, s, "notizie", nome,
        archivio=archivio, filtri=filtri, soglia=soglia,
        notizie=notizie.elenca(s, filtri, soglia),
        filtrata=bool(request.query_params.get("tipo") or filtri.interesse_id or filtri.fonte or filtri.giorni or filtri.solo_cuore),
        interessi=interessi.elenca(s), fonti=fonti, nomi_categorie=nomi_categorie, ultima=esecuzioni.ultima(s),
        avanzamento=request.app.state.esecutore.avanzamento,
    )


@router.get("/notizie", response_class=HTMLResponse)
def pagina_notizie(request: Request, s: Sessione):
    return _elenco(request, s, archivio=False)


@router.get("/archivio", response_class=HTMLResponse)
def pagina_archivio(request: Request, s: Sessione):
    return _elenco(request, s, archivio=True)


@router.get("/notizie/{id}", response_class=HTMLResponse)
def notizia_specifica(request: Request, s: Sessione, id: int):
    notizia = notizie.dettaglio(s, id)
    if notizia is None:
        raise HTTPException(404, "Notizia inesistente o cancellata")
    return pagina(request, s, "notizia", "archivio" if notizia.cuore else "notizie",
                  n=notizia, numero_interessi=len(interessi.elenca(s)), nomi_categorie=impostazioni.nomi_categorie(s))


@router.post("/notizie/{id}/cuore", response_class=HTMLResponse)
def cuore(request: Request, s: Sessione, id: int):
    """UI-05: mette o toglie il cuore e restituisce il bottone aggiornato."""
    attuale = s.get(Notizia, id)
    if attuale is None:
        raise HTTPException(404, "Notizia inesistente o cancellata")
    n = notizie.imposta_cuore(s, id, not attuale.cuore)
    return frammento(request, "cuore", n=n, con_testo=request.query_params.get("testo") == "1")


# ---------- Esecuzione dalla dashboard (ESE-01) ----------

@router.post("/esecuzione", response_class=HTMLResponse)
async def avvia_esecuzione(request: Request):
    try:
        request.app.state.esecutore.avvia("dashboard")
    except GiaInCorso:
        pass  # ESE-02: si mostra l'avanzamento di quella già in corso
    return frammento(request, "avanzamento", avanzamento=request.app.state.esecutore.avanzamento)


@router.get("/esecuzione/avanzamento", response_class=HTMLResponse)
def avanzamento(request: Request, s: Sessione):
    attuale = request.app.state.esecutore.avanzamento
    risposta = frammento(request, "avanzamento", avanzamento=attuale, ultima=esecuzioni.ultima(s), mostra_esito=attuale is None)
    if attuale is None:  # finita: la pagina ricarica l'elenco
        risposta.headers["HX-Trigger"] = json.dumps({"esecuzione-finita": True})
    return risposta


def registra(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=CARTELLA / "static"), name="static")
    app.include_router(rotte_impostazioni.router)
    app.include_router(router)
