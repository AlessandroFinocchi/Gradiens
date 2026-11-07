"""Finestra delle Impostazioni (UI-10): ogni azione restituisce la finestra aggiornata."""

import json
from collections.abc import Callable
from urllib.parse import urlparse

import httpx
from typing import Annotated, Literal

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from gradiens.dashboard import segnali
from gradiens.dashboard.comune import Sessione, frammento
from gradiens.dati import impostazioni, interessi
from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati import siti as dati_siti
from gradiens.dati.modelli import Sito
from gradiens.fonti import siti, youtube
from gradiens.fonti.siti import Profilo
from gradiens.app.configurazione import salva_segreto
from gradiens.telegram import bot as telegram
from gradiens.telegram.messaggi import COMANDI

# Sezione: (gruppo, nome, icona). Ogni fetta aggiunge le sue.
SEZIONI = {
    "interessi": ("Contenuti", "Interessi", "interessi"),
    "canali-youtube": ("Contenuti", "Canali YouTube", "youtube"),
    "siti": ("Contenuti", "Siti web", "sito"),
    "arxiv": ("Contenuti", "arXiv", "arxiv"),
    "esecuzione": ("Funzionamento", "Esecuzione", "esecuzione"),
    "telegram": ("Funzionamento", "Telegram", "telegram"),
    "aspetto": ("Interfaccia", "Aspetto", "aspetto"),
}
router = APIRouter(prefix="/impostazioni")


def finestra(request: Request, s: Session, sezione: str, errore: str | None = None, **extra) -> HTMLResponse:
    if sezione not in SEZIONI:
        raise HTTPException(404, "Sezione inesistente")
    bot = request.app.state.bot
    trovati = segnali.segnali(s, bot.problema())
    contesto = {"sezioni": SEZIONI, "sezione": sezione, "imp": impostazioni.leggi(s), "errore": errore,
                "segnali": trovati, "segnale_globale": segnali.globale(trovati),
                "voci": trovati[sezione].voci if sezione in trovati else set(), **extra}
    if sezione == "telegram":
        contesto.update(token_salvato=request.app.state.conf.telegram_token is not None, problema_bot=bot.errore,
                        COMANDI=COMANDI)
    if sezione == "interessi":
        contesto["interessi"] = interessi.elenca(s)
    elif sezione == "canali-youtube":
        contesto["canali"] = impostazioni.canali_youtube(s)
    elif sezione == "siti":
        contesto["siti"] = [(sito, Profilo.da_dict(json.loads(sito.profilo))) for sito in dati_siti.elenca(s)]
    elif sezione == "arxiv":
        contesto["categorie"] = impostazioni.elenca_categorie(s)
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


@router.post("/youtube", response_class=HTMLResponse)
async def aggiungi_canale(request: Request, s: Sessione, indirizzo: Testo):
    """YT-01: si ricava il canale da un indirizzo qualsiasi (@nome, /channel/…, link di un video)."""
    try:
        canale = await youtube.risolvi_canale(indirizzo)
    except ValueError as errore:
        return finestra(request, s, "canali-youtube", errore=str(errore))
    return _esegui(request, s, "canali-youtube", lambda: impostazioni.aggiungi_canale(s, canale.id, canale.nome))


@router.post("/youtube/rimuovi", response_class=HTMLResponse)
def rimuovi_canale(request: Request, s: Sessione, id: Testo):
    return _esegui(request, s, "canali-youtube", lambda: impostazioni.rimuovi_canale(s, id))


# ---------- Siti web (WEB-01, WEB-07, WEB-21, WEB-25) ----------

def _indirizzo_web(testo: str) -> str:
    testo = testo.strip()
    parti = urlparse(testo)
    if parti.scheme not in ("http", "https") or not parti.netloc:
        raise ImpostazioneNonValida("Serve un indirizzo completo che inizi con https://")
    return testo


def _modifica_profilo(request: Request, s: Session, id: int, cambia: Callable[[Profilo], None]) -> HTMLResponse:
    """Modifica manuale del profilo: la rigenerazione la conserva (WEB-25)."""
    def azione():
        sito = s.get_one(Sito, id)
        profilo = Profilo.da_dict(json.loads(sito.profilo))
        cambia(profilo)
        dati_siti.salva_profilo(s, id, profilo.come_dict())
    return _esegui(request, s, "siti", azione)


@router.post("/siti", response_class=HTMLResponse)
async def aggiungi_sito(request: Request, s: Sessione, indirizzo: Testo):
    """WEB-01: basta l'indirizzo; l'analisi crea il profilo (qualche secondo: rispetta le pause tra le richieste)."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            profilo = await siti.analizza(client, indirizzo)
    except ValueError:
        return finestra(request, s, "siti", errore="Indirizzo non valido: incolla l'indirizzo della home o di una sezione.")
    return _esegui(request, s, "siti", lambda: dati_siti.aggiungi(s, profilo.url, profilo.come_dict(), profilo.diagnosi or None))


@router.post("/siti/{id}/rimuovi", response_class=HTMLResponse)
def rimuovi_sito(request: Request, s: Sessione, id: int):
    return _esegui(request, s, "siti", lambda: dati_siti.rimuovi(s, id))


@router.post("/siti/{id}/feed", response_class=HTMLResponse)
def aggiungi_feed(request: Request, s: Sessione, id: int, indirizzo: Testo):
    return _modifica_profilo(request, s, id, lambda p: p.aggiungi_feed(_indirizzo_web(indirizzo)))


@router.post("/siti/{id}/escludi", response_class=HTMLResponse)
def escludi_percorso(request: Request, s: Sessione, id: int, indirizzo: Testo):
    return _modifica_profilo(request, s, id, lambda p: p.escludi(_indirizzo_web(indirizzo)))


@router.post("/siti/{id}/collegato", response_class=HTMLResponse)
def sito_collegato(request: Request, s: Sessione, id: int, dominio: Testo, attivo: Annotated[bool, Form()] = False):
    """WEB-07: i domini esterni trovati nell'analisi sono proposti disattivati; l'utente li attiva."""
    def cambia(p: Profilo) -> None:
        if dominio not in p.siti_collegati:
            raise ImpostazioneNonValida("Sito collegato sconosciuto.")
        p.siti_collegati[dominio] = attivo
        if "siti_collegati" not in p.modificati:
            p.modificati.append("siti_collegati")
    return _modifica_profilo(request, s, id, cambia)


@router.post("/siti/{id}/tetti", response_class=HTMLResponse)
def tetti_sito(request: Request, s: Sessione, id: int, pagine: Numero, articoli: Numero):
    """WEB-19: per un sito che pubblica molto (es. hwupgrade) si alzano i tetti per esecuzione."""
    def cambia(p: Profilo) -> None:
        if not (1 <= pagine <= 500 and 1 <= articoli <= 1000):
            raise ImpostazioneNonValida("Le pagine vanno da 1 a 500, gli articoli da 1 a 1000.")
        p.pagine_massime, p.articoli_massimi = pagine, articoli
        p.modificati += [c for c in ("pagine_massime", "articoli_massimi") if c not in p.modificati]
    return _modifica_profilo(request, s, id, cambia)


@router.post("/siti/{id}/rigenera", response_class=HTMLResponse)
async def rigenera_profilo(request: Request, s: Sessione, id: int):
    sito = s.get(Sito, id)
    if sito is None:
        raise HTTPException(404, "Sito inesistente")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        nuovo = await siti.rigenera(client, Profilo.da_dict(json.loads(sito.profilo)))
    return _esegui(request, s, "siti", lambda: dati_siti.salva_rigenerato(s, id, nuovo.come_dict()))


@router.post("/arxiv/categorie", response_class=HTMLResponse)
def aggiungi_categoria(request: Request, s: Sessione, codice: Testo, nome: Annotated[str, Form()] = ""):
    return _esegui(request, s, "arxiv", lambda: impostazioni.aggiungi_categoria(s, codice, nome))


@router.post("/arxiv/categorie/rimuovi", response_class=HTMLResponse)
def rimuovi_categoria(request: Request, s: Sessione, codice: Testo):
    return _esegui(request, s, "arxiv", lambda: impostazioni.rimuovi_categoria(s, codice))


@router.post("/arxiv/tetto", response_class=HTMLResponse)
def tetto_arxiv(request: Request, s: Sessione, tetto: Numero):
    return _esegui(request, s, "arxiv", lambda: impostazioni.salva_tetto_arxiv(s, tetto))


@router.post("/esecuzione", response_class=HTMLResponse)
def esecuzione(request: Request, s: Sessione, soglia: Numero, finestra_giorni: Numero,
               escludi_sponsorizzati: Annotated[bool, Form()] = False, escludi_pagamento: Annotated[bool, Form()] = False,
               orario: Annotated[str | None, Form()] = None, in_pausa: Annotated[bool, Form()] = False):
    # Una casella non spuntata non viene inviata: per questo il valore di base qui è False.
    return _esegui(request, s, "esecuzione", lambda: impostazioni.salva_esecuzione(
        s, soglia, finestra_giorni, escludi_sponsorizzati, escludi_pagamento, orario, in_pausa))


# ---------- Telegram (TG-01): tutorial, prova, cambio di chat ----------

@router.post("/telegram/token", response_class=HTMLResponse)
async def telegram_token(request: Request, s: Sessione, token: Testo):
    token = token.strip()
    try:
        nome = await telegram.verifica_token(token)
    except telegram.ErroreTelegram as errore:
        return finestra(request, s, "telegram", errore=str(errore))
    await request.app.state.bot.ferma()
    salva_segreto(request.app.state.conf, "telegram_token", token)  # nel .env, mai nel database (PER-02)
    imp = impostazioni.leggi(s)
    imp.telegram_bot, imp.telegram_chat_id, imp.telegram_chat_nome = nome, None, None  # nuovo bot: chat da confermare
    s.commit()
    return finestra(request, s, "telegram")


@router.post("/telegram/cerca", response_class=HTMLResponse)
async def telegram_cerca(request: Request, s: Sessione):
    token = request.app.state.conf.telegram_token
    if token is None:
        return finestra(request, s, "telegram", errore="Prima incolla il token del bot.")
    try:
        trovata = await telegram.cerca_chat(token.get_secret_value())
    except telegram.ErroreTelegram as errore:
        return finestra(request, s, "telegram", errore=str(errore))
    if trovata is None:
        return finestra(request, s, "telegram", errore="Nessun /start ricevuto: scrivi /start al bot e riprova.")
    return finestra(request, s, "telegram", chat_trovata=trovata)


@router.post("/telegram/conferma", response_class=HTMLResponse)
async def telegram_conferma(request: Request, s: Sessione, chat_id: Numero, nome: Testo):
    token = request.app.state.conf.telegram_token
    if token is None:
        return finestra(request, s, "telegram", errore="Prima incolla il token del bot.")
    try:
        await telegram.collega(token.get_secret_value(), chat_id)
    except telegram.ErroreTelegram as errore:
        return finestra(request, s, "telegram", errore=str(errore))
    imp = impostazioni.leggi(s)
    imp.telegram_chat_id, imp.telegram_chat_nome = chat_id, nome[:200]
    s.commit()
    await request.app.state.bot.avvia()
    return finestra(request, s, "telegram")


@router.post("/telegram/prova", response_class=HTMLResponse)
async def telegram_prova(request: Request, s: Sessione):
    try:
        await request.app.state.bot.invia_prova()
    except telegram.ErroreTelegram as errore:
        return finestra(request, s, "telegram", errore=str(errore))
    return finestra(request, s, "telegram", esito="Messaggio di prova inviato: controlla Telegram.")


@router.post("/telegram/cambia-chat", response_class=HTMLResponse)
async def telegram_cambia_chat(request: Request, s: Sessione):
    await request.app.state.bot.ferma()
    imp = impostazioni.leggi(s)
    imp.telegram_chat_id = imp.telegram_chat_nome = None
    s.commit()
    return finestra(request, s, "telegram")

