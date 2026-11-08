"""Configurazione iniziale guidata (UI-11): blocca la dashboard finché non è stata completata una volta
(decisione 55). I passi riusano i moduli delle sezioni delle Impostazioni: le loro risposte, quando la
richiesta arriva da questa pagina, tornano come passo della procedura (`rotte_impostazioni.finestra`)."""

from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from gradiens.app import avvio_sistema
from gradiens.app.configurazione import RADICE
from gradiens.dashboard.comune import Sessione, modelli
from gradiens.dashboard.rotte_impostazioni import dati_sezione
from gradiens.dati import impostazioni, interessi
from gradiens.dati import siti as dati_siti
from gradiens.llm.base import ErroreLLM
from gradiens.llm.claude_code import stato_account

PASSI = {  # passo: (nome, sezioni delle Impostazioni che usa)
    "interessi": ("Interessi", ["interessi"]),
    "fonti": ("Fonti", ["canali-youtube", "siti", "arxiv"]),
    "claude": ("Claude Code", []),
    "telegram": ("Telegram", ["telegram"]),
}
PASSO_DI = {sezione: passo for passo, (_, sezioni) in PASSI.items() for sezione in sezioni}
MANCA = {
    "interessi": "Aggiungi almeno un interesse.",
    "fonti": "Aggiungi almeno una fonte: un canale YouTube, un sito o una categoria arXiv.",
    "claude": "Collega Claude Code a un account.",
    "telegram": "Collega il bot Telegram con i tre passi qui sopra.",
}
router = APIRouter(prefix="/configurazione")


def dalla_procedura(request: Request) -> bool:
    return urlparse(request.headers.get("HX-Current-URL", "")).path == "/configurazione"


def _fatti(request: Request, s: Session, con_claude: bool) -> tuple[dict[str, bool | None], str]:
    """Per ogni passo se i suoi dati obbligatori ci sono, e lo stato di Claude Code da mostrare. Claude Code
    si controlla solo se serve (`con_claude`): lancia un comando esterno, che non deve rallentare gli altri passi."""
    claude, account = None, ""
    if con_claude:
        try:
            claude, account = True, stato_account()
        except ErroreLLM as errore:
            claude, account = False, str(errore)
    fatti = {
        "interessi": bool(interessi.elenca(s)),
        # Decisione 56: basta una fonte di qualsiasi tipo.
        "fonti": bool(impostazioni.canali_youtube(s) or dati_siti.elenca(s) or impostazioni.categorie_arxiv(s)),
        "claude": claude,
        "telegram": request.app.state.conf.telegram_token is not None and impostazioni.leggi(s).telegram_chat_id is not None,
    }
    return fatti, account


def passo(request: Request, s: Session, nome: str, errore: str | None = None, **extra) -> HTMLResponse:
    fatti, account = _fatti(request, s, con_claude=nome == "claude")
    contesto = {"passi": PASSI, "passo": nome, "indice": list(PASSI).index(nome), "fatti": fatti, "MANCA": MANCA,
                "account": account, "imp": impostazioni.leggi(s), "errore": errore, "voci": set(), **extra}
    for sezione in PASSI[nome][1]:
        contesto.update(dati_sezione(request, s, sezione))
    intera = not request.headers.get("HX-Request")
    return modelli.TemplateResponse(request, "configurazione.html" if intera else "configurazione_passo.html",
                                    {**contesto, "tema": contesto["imp"].tema, "procedura": True})


@router.get("", response_class=HTMLResponse)
def apri(request: Request, s: Sessione, passo_scelto: Annotated[str, Query(alias="passo")] = "interessi") -> Response:
    if impostazioni.leggi(s).configurazione_completata:
        return RedirectResponse("/", status_code=303)
    if passo_scelto not in PASSI:
        raise HTTPException(404, "Passo inesistente")
    return passo(request, s, passo_scelto)


@router.post("/completa", response_class=HTMLResponse)
def completa(request: Request, s: Sessione, icone: Annotated[bool, Form()] = False) -> Response:
    fatti, _ = _fatti(request, s, con_claude=True)
    if mancanti := [MANCA[p] for p, fatto in fatti.items() if not fatto]:
        return passo(request, s, "telegram", errore=" ".join(mancanti))
    if icone:  # AMB-05: l'icona del pannello di controllo, proposta alla fine (ADR 0009)
        try:
            avvio_sistema.crea_icone(RADICE)
        except avvio_sistema.ErroreAvvio as errore:
            return passo(request, s, "telegram", errore=f"{errore} Togli la spunta per continuare senza icona: "
                                                         "potrai crearla dopo dalle Impostazioni, sezione Avvio.")
    impostazioni.leggi(s).configurazione_completata = True
    s.commit()
    return Response(status_code=204, headers={"HX-Redirect": "/"})
