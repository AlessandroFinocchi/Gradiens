"""Il processo unico di Gradiens: dashboard e, nelle fette successive, programmazione e bot (ADR 0003)."""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from gradiens.app.configurazione import Configurazione
from gradiens.dashboard import rotte as dashboard
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra

METODI_SICURI = {"GET", "HEAD", "OPTIONS"}
# Intestazioni che un altro sito non può aggiungere a una richiesta senza il permesso CORS,
# che Gradiens non concede: bastano a bloccare le richieste forgiate da altri siti (CSRF).
INTESTAZIONI_FIDATE = ("hx-request", "x-gradiens-cli")
INDIRIZZI_LOCALI = {"127.0.0.1", "::1"}

log = logging.getLogger("gradiens")
controllo = APIRouter(prefix="/api")


@controllo.get("/stato")
def stato(request: Request) -> dict:
    return {"avviato_alle": request.app.state.avviato_alle.isoformat(timespec="seconds")}


@controllo.post("/spegni")
def spegni(request: Request) -> JSONResponse:
    if request.client is None or request.client.host not in INDIRIZZI_LOCALI:
        return JSONResponse({"errore": "Gradiens si spegne solo dal PC su cui gira."}, status_code=403)
    log.info("Spegnimento richiesto dalla CLI")
    server = getattr(request.app.state, "server", None)
    if server is not None:
        server.should_exit = True
    return JSONResponse({"ok": True})


def crea_app(conf: Configurazione) -> FastAPI:
    motore = crea_motore(conf.percorso_database)
    migra(motore)

    app = FastAPI(title="Gradiens", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.sessioni = fabbrica_sessioni(motore)
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


def esegui(conf: Configurazione) -> None:
    """Avvia il servizio in primo piano e ritorna quando viene spento."""
    configura_log(conf)
    app = crea_app(conf)
    server = uvicorn.Server(uvicorn.Config(app, host=conf.host, port=conf.porta, log_config=None))
    app.state.server = server
    log.info("Gradiens in ascolto su http://%s:%s", conf.host, conf.porta)
    server.run()
    log.info("Gradiens spento")
