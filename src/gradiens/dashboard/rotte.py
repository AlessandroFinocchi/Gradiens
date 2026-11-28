"""Rotte delle pagine della dashboard e pezzi di pagina per htmx (ADR 0003)."""

import json
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import NoResultFound
from starlette.datastructures import QueryParams

from gradiens.dashboard import rotte_configurazione, rotte_impostazioni
from gradiens.dashboard.comune import (
    CARTELLA,
    FONTI,
    SOLO_DAL_PC,
    TIPI,
    Sessione,
    avvisi_limiti,
    cambio_versione,
    dal_pc,
    frammento,
    pagina,
)
from gradiens.dati import argomenti, esecuzioni, impostazioni, interessi, notizie, proposte
from gradiens.dati import siti as dati_siti
from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import FONTE_DI_TIPO, Argomento, Esecuzione, Notizia
from gradiens.dati.notizie import Filtri
from gradiens.esecuzione import evoluzione
from gradiens.esecuzione.esecutore import GiaInCorso
from gradiens.llm import claude_code
from gradiens.telegram.messaggi import COMANDI

router = APIRouter()


@router.get("/aiuto", response_class=HTMLResponse)
def aiuto(request: Request, s: Sessione):
    """UI-12: pagina statica; i comandi Telegram sono quelli del bot, le porte quelle della configurazione."""
    return pagina(request, s, "aiuto", "aiuto", COMANDI=COMANDI, conf=request.app.state.conf)


@router.post("/sidebar")
def cambia_sidebar(s: Sessione):
    """UI-01: il clic sul simbolo di Gradiens fissa la sidebar espansa o la sblocca; vale per tutte le pagine."""
    imp = impostazioni.leggi(s)
    imp.sidebar_fissa = not imp.sidebar_fissa
    s.commit()
    return Response(status_code=204, headers={"HX-Trigger": json.dumps({"sidebar-cambiata": imp.sidebar_fissa})})


# ---------- Home (UI-02) e resoconto di un'esecuzione (UI-03) ----------


@router.get("/", response_class=HTMLResponse)
def home(request: Request, s: Sessione):
    ultima = esecuzioni.ultima(s)
    riepilogo = ultima and esecuzioni.riepilogo(ultima)
    prossima = request.app.state.programmatore.prossima()
    return pagina(
        request,
        s,
        "home",
        "home",
        prossima=prossima and prossima.astimezone(UTC).replace(tzinfo=None),  # i filtri delle date vogliono UTC
        avanzamento=request.app.state.esecutore.avanzamento,
        ultima=ultima,
        riepilogo=riepilogo,
        evidenza=notizie.in_evidenza(s, impostazioni.leggi(s).soglia),
        nomi_categorie=impostazioni.nomi_categorie(s),
        siti_in_errore=dati_siti.in_errore(s),
        proposte=proposte.pendenti(s),
        avviso_login=claude_code.avviso_login(),
        avviso_versione=riepilogo and cambio_versione(riepilogo),
        avvisi_limiti=avvisi_limiti(riepilogo) if riepilogo else [],
        argomenti_nuovi=[r for r in argomenti.timeline(s, ultima and ultima.id) if r.nuove],  # UI-02, avvisi
        storico=[(e, esecuzioni.riepilogo(e)) for e in esecuzioni.storico(s)],
    )


@router.get("/esecuzioni/{id}", response_class=HTMLResponse)
def resoconto(request: Request, s: Sessione, id: int):
    esecuzione = s.get(Esecuzione, id)
    if esecuzione is None:
        raise HTTPException(404, "Esecuzione inesistente")
    riepilogo = esecuzioni.riepilogo(esecuzione)
    return pagina(
        request, s, "resoconto", "home", e=esecuzione, riepilogo=riepilogo, avvisi_limiti=avvisi_limiti(riepilogo)
    )


# ---------- Timeline e argomenti (UI-09, ESE-08) ----------


def _ultima_id(s) -> int | None:
    ultima = esecuzioni.ultima(s)
    return ultima.id if ultima else None


@router.get("/timeline", response_class=HTMLResponse)
def timeline(request: Request, s: Sessione, cuore: str = ""):
    """Temi in cima e argomenti sotto (UI-09). Filtro sul cuore: "si" quelli con almeno una notizia con il
    cuore, "no" quelli senza."""
    completo = argomenti.timeline(s, _ultima_id(s))
    filtro = cuore in ("si", "no")
    elenco = [r for r in completo if not filtro or (r.in_archivio > 0) == (cuore == "si")]
    return pagina(
        request,
        s,
        "timeline",
        "timeline",
        temi=[r for r in elenco if r.argomento.tema],
        elenco=[r for r in elenco if not r.argomento.tema],
        ci_sono_argomenti=any(not r.argomento.tema for r in completo),
        filtro=filtro,
        cuore=cuore,
        tutti=argomenti.tutti(s),
    )


@router.post("/temi")
def crea_tema(s: Sessione, nome: Annotated[str, Form()], descrizione: Annotated[str, Form()] = ""):
    _azione(s, lambda: argomenti.crea_tema(s, nome, descrizione))
    return _dopo()


@router.get("/argomenti/{id}", response_class=HTMLResponse)
def pagina_argomento(request: Request, s: Sessione, id: int):
    r = argomenti.riassunto(s, id, _ultima_id(s))
    if r is None:
        raise HTTPException(404, "Argomento inesistente o senza notizie")  # un tema si apre anche vuoto
    return pagina(
        request,
        s,
        "argomento",
        "timeline",
        r=r,
        tutti=argomenti.tutti(s),
        ultima_id=_ultima_id(s),
        nomi_categorie=impostazioni.nomi_categorie(s),
    )


def _dopo(indirizzo: str | None = None) -> Response:
    """Dopo un'azione su un argomento: htmx ricarica la pagina, o ne apre un'altra."""
    return Response(status_code=204, headers={"HX-Redirect": indirizzo} if indirizzo else {"HX-Refresh": "true"})


def _azione(s, azione):
    try:
        return azione()
    except ImpostazioneNonValida as errore:
        s.rollback()
        raise HTTPException(422, str(errore)) from None
    except NoResultFound:
        raise HTTPException(404, "Argomento inesistente") from None


@router.post("/argomenti/{id}/rinomina")
def rinomina_argomento(s: Sessione, id: int, nome: Annotated[str, Form()]):
    _azione(s, lambda: argomenti.rinomina(s, id, nome))
    return _dopo()


@router.post("/argomenti/{id}/tema")
def tema_argomento(s: Sessione, id: int, tema: Annotated[bool, Form()] = False):
    """UI-09: l'interruttore "Raccogli tutto il tema". Senza tema e senza notizie l'argomento non c'è più (ESE-10)."""
    rimasto = _azione(s, lambda: argomenti.imposta_tema(s, id, tema))
    return _dopo(None if rimasto else "/timeline")


@router.post("/argomenti/{id}/descrizione")
def descrizione_tema(s: Sessione, id: int, descrizione: Annotated[str, Form()] = ""):
    _azione(s, lambda: argomenti.salva_descrizione(s, id, descrizione))
    return _dopo()


@router.post("/argomenti/{id}/unisci")
def unisci_argomento(request: Request, s: Sessione, id: int, destinazione: Annotated[int, Form()]):
    _azione(s, lambda: argomenti.unisci(s, id, destinazione))
    # Dalla pagina dell'argomento unito si va a quella della destinazione; dalla Timeline si ricarica.
    return _dopo(f"/argomenti/{destinazione}" if "/argomenti/" in request.headers.get("HX-Current-URL", "") else None)


@router.post("/argomenti/{id}/cuore")
def cuore_argomento(request: Request, s: Sessione, id: int):
    """UI-09: se il cuore manca ad almeno una notizia lo mette a tutte, altrimenti lo toglie a tutte. Toglierlo
    fa cancellare alla pulizia le notizie più vecchie di 7 giorni: da fuori casa no, come per una notizia
    (decisione 56)."""
    argomento = s.get(Argomento, id)
    if argomento is None:
        raise HTTPException(404, "Argomento inesistente")
    cuore = not all(n.cuore for n in argomento.notizie)
    if not cuore and not dal_pc(request):
        raise HTTPException(403, SOLO_DAL_PC)
    argomenti.imposta_cuore(s, id, cuore)
    return _dopo()


@router.post("/argomenti/{id}/evoluzione", response_class=HTMLResponse)
async def evoluzione_argomento(request: Request, s: Sessione, id: int):
    """Decisione 72: l'LLM racconta come si è evoluto l'argomento. Consuma quota solo quando lo si chiede."""
    if s.get(Argomento, id) is None:
        raise HTTPException(404, "Argomento inesistente")
    errore = None
    try:
        await evoluzione.riassumi(s, id)
    except evoluzione.RiassuntoNonDisponibile as e:
        errore = str(e)
    return frammento(request, "argomento_evoluzione", r=argomenti.riassunto(s, id, _ultima_id(s)), errore=errore)


@router.post("/argomenti/{id}/elimina")
def elimina_argomento(request: Request, s: Sessione, id: int):
    _azione(s, lambda: argomenti.elimina(s, id))
    return _dopo("/timeline" if "/argomenti/" in request.headers.get("HX-Current-URL", "") else None)


# ---------- Notizie e Archivio (UI-04..UI-08) ----------


def _intero(valore: str | None) -> int | None:
    try:
        return int(valore) if valore else None
    except ValueError:  # es. "²": isdigit() lo accetterebbe, int() no
        return None


# La notizia specifica prima delle pagine: `{id:int}` prende solo le cifre, il resto va a `/notizie/{sezione}`.
@router.get("/notizie/{id:int}", response_class=HTMLResponse)
def notizia_specifica(request: Request, s: Sessione, id: int):
    notizia = notizie.dettaglio(s, id)
    if notizia is None:
        raise HTTPException(404, "Notizia inesistente o cancellata")
    return pagina(
        request,
        s,
        "notizia",
        "archivio" if notizia.cuore else FONTE_DI_TIPO[notizia.tipo],
        n=notizia,
        sezione=FONTE_DI_TIPO[notizia.tipo],
        numero_interessi=len(interessi.elenca(s)),
        nomi_categorie=impostazioni.nomi_categorie(s),
    )


# Tipi di notizia di ogni pagina di notizie (UI-04): siti, YouTube (video e short) e arXiv.
TIPI_DI_PAGINA = {pagina: [t for t in TIPI if FONTE_DI_TIPO[t] == pagina] for pagina in FONTI}


def leggi_filtri(q: QueryParams, archivio: bool, ammessi: list[str]) -> Filtri:
    """I parametri arrivano dall'indirizzo: tutto ciò che non è riconosciuto si ignora. Senza tipi scelti
    valgono tutti quelli `ammessi` dalla pagina."""
    ordine, _, verso = (q.get("ordine") or ("data-desc" if archivio else "pertinenza-desc")).partition("-")
    return Filtri(
        archivio=archivio,
        tipi=[t for t in q.getlist("tipo") if t in ammessi] or list(ammessi),
        interessi=[i for i in map(_intero, q.getlist("interesse")) if i is not None],
        fonti=q.getlist("fonte"),
        giorni=_intero(q.get("giorni")),
        solo_cuore=q.get("cuore") == "1",
        testo=(q.get("q") or "").strip()[:200],
        ordine="data" if ordine == "data" else "pertinenza",
        crescente=verso == "asc",
    )


def _elenco(request: Request, s: Sessione, sezione: str | None) -> HTMLResponse:
    """Una pagina di notizie (`sezione` è una chiave di FONTI) o, senza sezione, l'Archivio con tutti i tipi."""
    archivio = sezione is None
    ammessi = TIPI_DI_PAGINA[sezione] if sezione else list(TIPI)
    filtri = leggi_filtri(request.query_params, archivio, ammessi)
    nomi_categorie = impostazioni.nomi_categorie(s)
    fonti = notizie.fonti(s, filtri.tipi, nomi_categorie, archivio)
    filtri.fonti = [f for f in filtri.fonti if f in fonti]  # fonte di un tipo non selezionato (UI-06): si ignora
    tutti_gli_interessi = interessi.elenca(s)
    filtri.interessi = [i for i in filtri.interessi if i in {x.id for x in tutti_gli_interessi}]
    soglia = impostazioni.leggi(s).soglia
    return pagina(
        request,
        s,
        "notizie",
        sezione or "archivio",
        archivio=archivio,
        sezione=sezione,
        tipi_pagina=ammessi,
        filtri=filtri,
        soglia=soglia,
        notizie=notizie.elenca(s, filtri, soglia),
        filtrata=bool(
            request.query_params.get("tipo")
            or filtri.interessi
            or filtri.fonti
            or filtri.giorni
            or filtri.solo_cuore
            or filtri.testo
        ),
        interessi=tutti_gli_interessi,
        fonti=fonti,
        nomi_categorie=nomi_categorie,
        ultima=esecuzioni.ultima(s),
        avanzamento=request.app.state.esecutore.avanzamento,
    )


@router.get("/notizie")
def notizie_senza_sezione(request: Request):
    """Indirizzo di prima della divisione in tre pagine (decisione 69): porta alla pagina del primo tipo scelto, o
    ai Siti web, con gli stessi filtri. I tipi delle altre pagine lì si ignorano."""
    tipi = [t for t in request.query_params.getlist("tipo") if t in FONTE_DI_TIPO]
    indirizzo = f"/notizie/{FONTE_DI_TIPO[tipi[0]] if tipi else 'siti'}"
    query = request.url.query
    return RedirectResponse(f"{indirizzo}?{query}" if query else indirizzo, status_code=307)


@router.get("/notizie/{sezione}", response_class=HTMLResponse)
def pagina_notizie(request: Request, s: Sessione, sezione: str):
    if sezione not in FONTI:
        raise HTTPException(404, "Pagina inesistente")
    return _elenco(request, s, sezione)


@router.get("/archivio", response_class=HTMLResponse)
def pagina_archivio(request: Request, s: Sessione):
    return _elenco(request, s, None)


@router.post("/notizie/{id}/cuore", response_class=HTMLResponse)
def cuore(request: Request, s: Sessione, id: int):
    """UI-05: mette o toglie il cuore e restituisce il bottone aggiornato. Toglierlo fa cancellare la notizia
    alla pulizia: da fuori casa no (decisione 56)."""
    attuale = s.get(Notizia, id)
    if attuale is None:
        raise HTTPException(404, "Notizia inesistente o cancellata")
    if attuale.cuore and not dal_pc(request):
        raise HTTPException(403, SOLO_DAL_PC)
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
    risposta = frammento(
        request, "avanzamento", avanzamento=attuale, ultima=esecuzioni.ultima(s), mostra_esito=attuale is None
    )
    if attuale is None:  # finita: la pagina ricarica l'elenco
        risposta.headers["HX-Trigger"] = json.dumps({"esecuzione-finita": True})
    return risposta


def registra(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory=CARTELLA / "static"), name="static")
    app.include_router(rotte_impostazioni.router)
    app.include_router(rotte_configurazione.router)
    app.include_router(router)
