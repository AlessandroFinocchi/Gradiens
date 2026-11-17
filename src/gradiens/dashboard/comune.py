"""Parti comuni della dashboard: template, filtri Jinja, sessione del database."""

import difflib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from gradiens.app import avvio_sistema
from gradiens.app.configurazione import RADICE
from gradiens.dashboard import segnali
from gradiens.dati import impostazioni
from gradiens.dati.esecuzioni import STATI_BUONI
from gradiens.dati.notizie import nome_fonte
from gradiens.llm import nome_provider

CARTELLA = Path(__file__).parent
modelli = Jinja2Templates(directory=CARTELLA / "templates")


def statico(nome: str) -> str:
    """Indirizzo di un file statico con la sua data di modifica: dopo un aggiornamento il browser lo
    riscarica invece di usare la copia in cache (il server non manda una scadenza)."""
    return f"/static/{nome}?v={int((CARTELLA / 'static' / nome).stat().st_mtime)}"

PAGINE = {
    "home": ("Home", "/"),
    "notizie": ("Notizie", "/notizie"),
    "timeline": ("Timeline", "/timeline"),
    "archivio": ("Archivio", "/archivio"),
}
TIPI = {"arxiv": ("arxiv", "arXiv"), "sito": ("sito", "Sito"), "video": ("video", "Video YT"), "short": ("short", "Short YT")}
FONTI = {"siti": ("sito", "Siti web"), "youtube": ("youtube", "YouTube"), "arxiv": ("arxiv", "arXiv")}  # (icona, nome)
AVVIATA_DA = {"programmazione": "programmazione", "dashboard": "dashboard", "cli": "terminale", "telegram": "Telegram"}
MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def _locale(d: datetime) -> datetime:
    """Le date nel database sono in UTC: si mostrano nell'ora del PC."""
    return d.replace(tzinfo=UTC).astimezone()


def data_breve(d: datetime) -> str:
    ora = _locale(d)
    return f"{ora.day} {MESI[ora.month - 1]}, {ora:%H:%M}"


def data_breve_giorno(d: datetime) -> str:
    ora = _locale(d)
    return f"{ora.day} {MESI[ora.month - 1]}"


def data_lunga(d: datetime) -> str:
    ora = _locale(d)
    return f"{ora.day} {MESI[ora.month - 1]} {ora.year} alle {ora:%H:%M}"


def data_relativa(d: datetime) -> str:
    ora, oggi = _locale(d), datetime.now().astimezone().date()
    if ora.date() == oggi:
        return f"oggi alle {ora:%H:%M}"
    if ora.date() == oggi - timedelta(days=1):
        return f"ieri alle {ora:%H:%M}"
    if ora.date() == oggi + timedelta(days=1):
        return f"domani alle {ora:%H:%M}"
    return f"il {ora.day} {MESI[ora.month - 1]} alle {ora:%H:%M}"


def evidenzia(attuale: str, proposto: str) -> list[tuple[str, bool]]:
    """Il testo proposto a pezzi, con True per i pezzi nuovi rispetto all'attuale (INT-04).
    Le parole si confrontano senza punteggiatura né maiuscole; le parole nuove vicine stanno in un pezzo solo."""
    def pulita(parola: str) -> str:
        return parola.strip(".,;:!?()«»\"'").casefold()

    dopo = proposto.split()
    pezzi: list[tuple[str, bool]] = []
    confronto = difflib.SequenceMatcher(a=[pulita(p) for p in attuale.split()], b=[pulita(p) for p in dopo], autojunk=False)
    for op, _, _, j1, j2 in confronto.get_opcodes():
        if j1 < j2:
            pezzi.append((" ".join(dopo[j1:j2]), op in ("insert", "replace")))
    return pezzi


def durata(secondi: float | None) -> str:
    if secondi is None:
        return "—"
    minuti, resto = divmod(round(secondi), 60)
    return f"{minuti} min {resto:02d} s" if minuti else f"{resto} s"


def cambio_versione(riepilogo: dict) -> str | None:
    """Decisione 45: il provider (es. Claude Code) ha cambiato versione e la prova è riuscita. Se non è
    riuscita l'esecuzione è fallita e lo dice il suo motivo."""
    v = riepilogo.get("versione_llm") or {}
    if not (v.get("precedente") and v.get("provata")):
        return None
    return (f"{nome_provider(v['provider'])} è passato dalla versione {v['precedente']} alla {v['versione']}: "
            "la prova di funzionamento è riuscita.")


def migliaia(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def token_brevi(n: int) -> str:
    return migliaia(n) if n < 1000 else f"{round(n / 1000)} mila"


modelli.env.filters.update(data_breve=data_breve, data_breve_giorno=data_breve_giorno, data_lunga=data_lunga, data_relativa=data_relativa,
                           durata=durata, migliaia=migliaia, token_brevi=token_brevi)
modelli.env.globals.update(statico=statico, TIPI=TIPI, FONTI=FONTI, AVVIATA_DA=AVVIATA_DA, STATI_BUONI=STATI_BUONI, nome_fonte=nome_fonte,
                           evidenzia=evidenzia)


INDIRIZZI_LOCALI = {"127.0.0.1", "::1"}
SOLO_DAL_PC = "Si fa stando al PC su cui gira Gradiens."


def dal_pc(request: Request) -> bool:
    """La richiesta arriva dal PC su cui gira Gradiens (ADR 0013). Tailscale Serve inoltra da 127.0.0.1 e l'Host lo
    scrive il cliente, quindi non bastano: conta la porta, perché Serve entra solo dalla seconda (`porta_remota`)."""
    server, cliente = request.scope.get("server"), request.client
    return (server is not None and server[1] == request.app.state.conf.porta
            and cliente is not None and cliente.host in INDIRIZZI_LOCALI)


def solo_dal_pc(request: Request) -> None:
    """Dipendenza delle rotte che da fuori casa non si usano (decisione 56)."""
    if not dal_pc(request):
        raise HTTPException(403, SOLO_DAL_PC)


def disattiva_fuori(request: Request) -> Markup:
    """Attributi di un comando solo dal PC: da fuori casa è disattivato e dice perché."""
    return Markup() if dal_pc(request) else Markup(' disabled title="{}"').format(SOLO_DAL_PC)


SoloDalPc = Depends(solo_dal_pc)
modelli.env.globals.update(dal_pc=dal_pc, disattiva_fuori=disattiva_fuori)


def sessione(request: Request) -> Iterator[Session]:
    with request.app.state.sessioni() as s:
        yield s


Sessione = Annotated[Session, Depends(sessione)]


def pagina(request: Request, s: Session, modello: str, nome: str, **contesto) -> HTMLResponse | RedirectResponse:
    """Pagina intera: `nome` indica la voce attiva nella sidebar, l'ingranaggio mostra i segnali (UI-14).
    Finché la configurazione iniziale non è completata, ogni pagina porta lì (UI-11)."""
    imp = impostazioni.leggi(s)
    if not imp.configurazione_completata:
        return RedirectResponse("/configurazione", status_code=303)
    return modelli.TemplateResponse(request, f"{modello}.html", {
        "pagina": nome, "pagine": PAGINE, "tema": imp.tema,
        "segnale_globale": segnali.globale(segnali.segnali(s, request.app.state.bot.problema(),
                                                           avvio_sistema.stato_avvio(RADICE).problema)), **contesto,
    })


def frammento(request: Request, modello: str, **contesto) -> HTMLResponse:
    """Pezzo di pagina per htmx."""
    return modelli.TemplateResponse(request, f"{modello}.html", contesto)
