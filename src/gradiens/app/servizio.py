"""Il processo unico di Gradiens: dashboard, esecuzioni e, nelle fette successive, programmazione e bot (ADR 0003)."""

import asyncio
import json
import logging
import socket
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from gradiens.app.configurazione import Configurazione
from gradiens.dashboard import rotte as dashboard
from gradiens.dashboard.comune import dal_pc
from gradiens.dati import esecuzioni, impostazioni
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.esecuzione.esecutore import Esecutore, GiaInCorso
from gradiens.esecuzione.programmatore import Programmatore
from gradiens.telegram.bot import BotGradiens

METODI_SICURI = {"GET", "HEAD", "OPTIONS"}
# Intestazioni che un altro sito non può aggiungere a una richiesta senza il permesso CORS,
# che Gradiens non concede: bastano a bloccare le richieste forgiate da altri siti (CSRF).
INTESTAZIONI_FIDATE = ("hx-request", "x-gradiens-cli")
# Un altro sito non può mostrare la dashboard dentro una sua pagina (clickjacking): i clic nella cornice
# sarebbero della stessa origine e passerebbero la difesa CSRF (ADR 0013).
NIENTE_CORNICI = {"X-Frame-Options": "DENY", "Content-Security-Policy": "frame-ancestors 'none'"}

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
    if not dal_pc(request):
        return JSONResponse({"errore": "Gradiens si spegne solo dal PC su cui gira."}, status_code=403)
    log.info("Spegnimento richiesto dalla CLI")
    server = getattr(request.app.state, "server", None)
    if server is not None:
        server.should_exit = True
    return JSONResponse({"ok": True})


@controllo.post("/esegui")
async def esegui_da_cli(request: Request) -> JSONResponse:
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
        ultima = (
            None
            if u is None
            else {
                "id": u.id,
                "stato": u.stato,
                "motivo": u.motivo,
                "metriche": json.loads(u.metriche or "null"),
            }
        )
    return {"avanzamento": vars(avanzamento) if avanzamento else None, "ultima": ultima}


def rifiuto_da_fuori(nome: str | None, intestazioni: Headers) -> Response | None:
    """Una richiesta arrivata sulla porta per Tailscale Serve passa solo con l'accesso da fuori casa attivo, con il
    nome Tailscale salvato e con l'identità che Serve aggiunge per i dispositivi della rete Tailscale. Il traffico di
    Funnel, che arriva da internet, quell'identità non ce l'ha (ADR 0013)."""
    if nome is None:
        return PlainTextResponse("Accesso da fuori casa spento: si attiva dalle Impostazioni, stando al PC.", 403)
    if intestazioni.get("host", "").split(":")[0].lower() != nome:
        return PlainTextResponse("Invalid host header", 400)
    if "tailscale-user-login" not in intestazioni:
        return PlainTextResponse(
            "Richiesta senza l'identità di Tailscale: la dashboard si apre solo dai dispositivi "
            "della tua rete Tailscale, mai da internet con Funnel.",
            403,
        )
    return None


class ControlloHost:
    """Difesa dal DNS rebinding sulla porta principale (i nomi del .env); sulla porta per Tailscale Serve,
    `rifiuto_da_fuori`. Il nome Tailscale sta in `app.state.accesso_remoto`, aggiornato dalle Impostazioni."""

    def __init__(self, app: ASGIApp, conf: Configurazione):
        self.app = app
        self.principale = TrustedHostMiddleware(app, allowed_hosts=conf.host_consentiti)
        self.porta_remota = conf.porta_remota

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or (scope.get("server") or ("", None))[1] != self.porta_remota:
            await self.principale(scope, receive, send)
        elif rifiuto := rifiuto_da_fuori(scope["app"].state.accesso_remoto, Headers(scope=scope)):
            await rifiuto(scope, receive, send)
        else:
            await self.app(scope, receive, send)


@asynccontextmanager
async def ciclo_di_vita(app: FastAPI):
    # Prima il bot: un'esecuzione recuperata all'avvio che fallisce subito deve poterlo segnalare (ESE-13).
    await app.state.bot.avvia()
    compiti = [
        asyncio.create_task(app.state.programmatore.gira()),  # ESE-01
        asyncio.create_task(app.state.bot.gira()),
    ]  # sezione 7 del PRD
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
        app.state.accesso_remoto = impostazioni.nome_remoto(impostazioni.leggi(s))  # ADR 0013
    app.state.esecutore = Esecutore(app.state.sessioni)
    app.state.programmatore = Programmatore(app.state.sessioni, app.state.esecutore)
    app.state.conf = conf
    app.state.bot = BotGradiens(conf, app.state.sessioni, app.state.esecutore, app.state.programmatore.prossima)
    app.state.esecutore.al_termine = app.state.bot.invia_esecuzione
    app.state.avviato_alle = datetime.now()
    app.state.porta_remota_aperta = True  # `esegui` lo corregge se la porta per Tailscale Serve è occupata

    @app.middleware("http")
    async def protezioni(request: Request, call_next):
        if request.method not in METODI_SICURI and not any(h in request.headers for h in INTESTAZIONI_FIDATE):
            return JSONResponse({"errore": "Richiesta rifiutata."}, status_code=403)
        risposta = await call_next(request)
        risposta.headers.update(NIENTE_CORNICI)
        return risposta

    # Aggiunto per ultimo, quindi controlla per primo: difesa dal DNS rebinding e porta per Tailscale Serve.
    app.add_middleware(ControlloHost, conf=conf)
    app.include_router(controllo)
    dashboard.registra(app)
    return app


def configura_log(conf: Configurazione) -> None:
    conf.cartella_log.mkdir(parents=True, exist_ok=True)
    gestore = RotatingFileHandler(
        conf.cartella_log / "gradiens.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    gestore.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    gestori = [gestore] if sys.stdout is None else [gestore, logging.StreamHandler(sys.stdout)]
    logging.basicConfig(level=logging.INFO, handlers=gestori)
    # A livello INFO httpx scrive ogni indirizzo chiamato: per Telegram contiene il token (PER-04).
    logging.getLogger("httpx").setLevel(logging.WARNING)


def configurazione_uvicorn(app: FastAPI) -> uvicorn.Config:
    """Valori scritti qui, non presi dall'ambiente: uvicorn si fida della X-Forwarded-For solo se arriva da questo
    PC (da Tailscale Serve), così il log registra il dispositivo che chiede. "Dal PC" non ne dipende (`dal_pc`)."""
    return uvicorn.Config(app, log_config=None, proxy_headers=True, forwarded_allow_ips="127.0.0.1,::1")


def apri_prese(conf: Configurazione) -> list[socket.socket]:
    """La porta principale e quella per Tailscale Serve, sempre su 127.0.0.1 (ADR 0013). `create_server` sceglie
    da sé le opzioni giuste per Windows e per Linux. Se la seconda porta è occupata Gradiens parte lo stesso."""
    famiglia = socket.AF_INET6 if ":" in conf.host else socket.AF_INET
    prese = [socket.create_server((conf.host, conf.porta), family=famiglia)]
    try:
        prese.append(socket.create_server(("127.0.0.1", conf.porta_remota)))
    except OSError as errore:
        log.warning("Porta %s per l'accesso da fuori casa non disponibile: %s", conf.porta_remota, errore)
    return prese


def esegui(conf: Configurazione) -> None:
    """Avvia il servizio in primo piano e ritorna quando viene spento."""
    configura_log(conf)
    app = crea_app(conf)
    try:
        prese = apri_prese(conf)
    except OSError as errore:  # es. un altro programma sulla porta principale
        log.error("Porta %s non disponibile: %s", conf.porta, errore)
        raise SystemExit(1) from None
    app.state.porta_remota_aperta = len(prese) > 1
    server = uvicorn.Server(configurazione_uvicorn(app))
    app.state.server = server
    log.info(
        "Gradiens in ascolto su http://%s:%s (porta per Tailscale Serve: %s)",
        conf.host,
        conf.porta,
        conf.porta_remota if app.state.porta_remota_aperta else "non disponibile",
    )
    server.run(sockets=prese)
    log.info("Gradiens spento")
