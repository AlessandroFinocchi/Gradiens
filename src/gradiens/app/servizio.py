"""Il processo unico di Gradiens: dashboard, esecuzioni e, nelle fette successive, programmazione e bot (ADR 0003)."""

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from gradiens.app.configurazione import Configurazione
from gradiens.dashboard import rotte as dashboard
from gradiens.dati import esecuzioni
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.esecuzione.esecutore import Esecutore, GiaInCorso
from gradiens.esecuzione.programmatore import Programmatore
from gradiens.telegram.bot import BotGradiens

METODI_SICURI = {"GET", "HEAD", "OPTIONS"}
# Intestazioni che un altro sito non può aggiungere a una richiesta senza il permesso CORS,
# che Gradiens non concede: bastano a bloccare le richieste forgiate da altri siti (CSRF).
INTESTAZIONI_FIDATE = ("hx-request", "x-gradiens-cli")
INDIRIZZI_LOCALI = {"127.0.0.1", "::1"}

log = logging.getLogger("gradiens")
controllo = APIRouter(prefix="/api")


@controllo.get("/stato")
def stato(request: Request) -> dict:
    """CLI-03. Ore del PC, tranne `avviata_il` dell'ultima esecuzione, che è in UTC come nel database."""
    prossima = request.app.state.programmatore.prossima()
    with request.app.state.sessioni() as s:
        u = esecuzioni.ultima(s)
        ultima = None if u is None else {"stato": u.stato, "avviata_il": u.avviata_il.isoformat(timespec="seconds")}
    return {
        "avviato_alle": request.app.state.avviato_alle.isoformat(timespec="seconds"),
        "prossima_esecuzione": prossima and prossima.isoformat(timespec="minutes"),  # None: in pausa
        "ultima_esecuzione": ultima,
    }


@controllo.post("/spegni")
def spegni(request: Request) -> JSONResponse:
    if request.client is None or request.client.host not in INDIRIZZI_LOCALI:
        return JSONResponse({"errore": "Gradiens si spegne solo dal PC su cui gira."}, status_code=403)
    log.info("Spegnimento richiesto dalla CLI")
    server = getattr(request.app.state, "server", None)
    if server is not None:
        server.should_exit = True
    return JSONResponse({"ok": True})


@controllo.post("/esegui")
async def esegui(request: Request) -> JSONResponse:
    """Avvio di un'esecuzione dalla CLI (CLI-02). `async`: l'esecuzione parte nel ciclo del servizio."""
    try:
        id = request.app.state.esecutore.avvia("cli")
    except GiaInCorso as errore:
        return JSONResponse({"errore": str(errore)}, status_code=409)
    return JSONResponse({"esecuzione_id": id})


@controllo.get("/esecuzione")
def esecuzione(request: Request) -> dict:
    """Avanzamento dell'esecuzione in corso e ultima esecuzione registrata."""
    avanzamento = request.app.state.esecutore.avanzamento
    with request.app.state.sessioni() as s:
        u = esecuzioni.ultima(s)
        ultima = None if u is None else {
            "id": u.id, "stato": u.stato, "motivo": u.motivo, "metriche": json.loads(u.metriche or "null"),
        }
    return {"avanzamento": vars(avanzamento) if avanzamento else None, "ultima": ultima}


@asynccontextmanager
async def ciclo_di_vita(app: FastAPI):
    # Prima il bot: un'esecuzione recuperata all'avvio che fallisce subito deve poterlo segnalare (ESE-13).
    await app.state.bot.avvia()
    compiti = [asyncio.create_task(app.state.programmatore.gira()),  # ESE-01
               asyncio.create_task(app.state.bot.gira())]  # sezione 7 del PRD
    yield
    for compito in compiti:
        compito.cancel()
    await app.state.esecutore.ferma()  # allo spegnimento: esecuzione interrotta e registrata (ESE-12)
    await app.state.bot.ferma()


def crea_app(conf: Configurazione) -> FastAPI:
    motore = crea_motore(conf.percorso_database)
    migra(motore)

    app = FastAPI(title="Gradiens", docs_url=None, redoc_url=None, openapi_url=None, lifespan=ciclo_di_vita)
    app.state.sessioni = fabbrica_sessioni(motore)
    with app.state.sessioni() as s:
        if interrotte := esecuzioni.segna_interrotte(s):  # ESE-12: spento durante un'esecuzione
            log.warning("%s esecuzioni segnate come interrotte", interrotte)
    app.state.esecutore = Esecutore(app.state.sessioni)
    app.state.programmatore = Programmatore(app.state.sessioni, app.state.esecutore)
    app.state.conf = conf
    app.state.bot = BotGradiens(conf, app.state.sessioni, app.state.esecutore, app.state.programmatore.prossima)
    app.state.esecutore.al_termine = app.state.bot.invia_esecuzione
    app.state.avviato_alle = datetime.now()

    @app.middleware("http")
    async def blocca_richieste_forgiate(request: Request, call_next):
        if request.method not in METODI_SICURI and not any(h in request.headers for h in INTESTAZIONI_FIDATE):
            return JSONResponse({"errore": "Richiesta rifiutata."}, status_code=403)
        return await call_next(request)

    # Aggiunto per ultimo, quindi controlla per primo: difesa dal DNS rebinding.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=conf.host_consentiti)
    app.include_router(controllo)
    dashboard.registra(app)
    return app


def configura_log(conf: Configurazione) -> None:
    conf.cartella_log.mkdir(parents=True, exist_ok=True)
    gestore = RotatingFileHandler(conf.cartella_log / "gradiens.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    gestore.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    gestori = [gestore] if sys.stdout is None else [gestore, logging.StreamHandler(sys.stdout)]
    logging.basicConfig(level=logging.INFO, handlers=gestori)
    # A livello INFO httpx scrive ogni indirizzo chiamato: per Telegram contiene il token (PER-04).
    logging.getLogger("httpx").setLevel(logging.WARNING)


def esegui(conf: Configurazione) -> None:
    """Avvia il servizio in primo piano e ritorna quando viene spento."""
    configura_log(conf)
    app = crea_app(conf)
    server = uvicorn.Server(uvicorn.Config(app, host=conf.host, port=conf.porta, log_config=None))
    app.state.server = server
    log.info("Gradiens in ascolto su http://%s:%s", conf.host, conf.porta)
    server.run()
    log.info("Gradiens spento")
