"""Aggiornamento di Gradiens senza terminale (`gradiens aggiorna` e il bottone del pannello): scarica la versione
nuova da GitHub, aggiorna le dipendenze e riaccende Gradiens se era acceso. Il database si aggiorna da solo alla
riaccensione, con una copia di sicurezza prima (`database.migra`).
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

from gradiens.app import cli
from gradiens.app.avvio_sistema import eseguibile
from gradiens.app.configurazione import RADICE, Configurazione


class ErroreAggiornamento(Exception):
    """Aggiornamento non fatto; il messaggio è pensato per l'utente."""


def _comando(argomenti: list[str], cartella: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argomenti, cwd=cartella, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=600)
    except (OSError, subprocess.TimeoutExpired) as errore:
        raise ErroreAggiornamento(f"{Path(argomenti[0]).name} non ha funzionato: {errore}") from None


def aggiorna(conf: Configurazione, avanzamento: Callable[[str], None] = print, radice: Path = RADICE) -> str:
    """Restituisce l'esito per l'utente, o solleva ErroreAggiornamento senza aver cambiato niente di importante."""
    git, uv = eseguibile("git"), eseguibile("uv")
    if git is None or not (radice / ".git").exists():
        raise ErroreAggiornamento("Questa copia di Gradiens non è stata scaricata con git: per aggiornarla scaricala di nuovo.")
    if uv is None:
        raise ErroreAggiornamento("uv non è installato: serve per aggiornare le dipendenze (vedi il README).")
    if _comando([git, "status", "--porcelain", "--untracked-files=no"], radice).stdout.strip():
        raise ErroreAggiornamento("Ci sono modifiche locali al codice di Gradiens: aggiornamento non fatto, per non perderle.")

    avanzamento("Controllo se c'è una versione nuova…")
    if (r := _comando([git, "fetch", "--quiet"], radice)).returncode != 0:
        raise ErroreAggiornamento(f"Non riesco a raggiungere GitHub: {r.stderr.strip()[:200]}")
    nuove = _comando([git, "rev-list", "--count", "HEAD..@{u}"], radice)
    if nuove.returncode != 0:
        raise ErroreAggiornamento("Questa copia non segue un ramo su GitHub: aggiornamento non possibile.")
    if int(nuove.stdout.strip() or 0) == 0:
        return "Gradiens è già aggiornato."

    stato = cli.leggi_stato(conf)
    if ((stato or {}).get("ultima_esecuzione") or {}).get("stato") == "in_corso":  # spegnere la interromperebbe
        raise ErroreAggiornamento("Un'esecuzione è in corso: aggiorna quando è finita.")
    acceso = stato is not None
    if acceso:  # su Windows i file in uso non si possono sostituire
        avanzamento("Spengo Gradiens…")
        cli.richiedi_spegnimento(conf)
        if not cli._attendi(lambda: cli.leggi_stato(conf) is None):
            raise ErroreAggiornamento("Gradiens non si è spento in tempo: riprova tra poco.")
    try:
        avanzamento("Scarico la versione nuova…")
        if (r := _comando([git, "merge", "--ff-only", "@{u}"], radice)).returncode != 0:
            raise ErroreAggiornamento(f"La versione nuova non si applica a questa copia: {r.stderr.strip()[:200]}")
        avanzamento("Aggiorno le dipendenze…")
        if (r := _comando([uv, "sync"], radice)).returncode != 0:
            raise ErroreAggiornamento(f"Versione nuova scaricata, ma le dipendenze non si sono aggiornate: {r.stderr.strip()[-300:]}"
                                      " Chiudi il pannello e lancia `uv sync` nella cartella di Gradiens.")
    finally:
        if acceso:  # anche se qualcosa è andato storto: Gradiens resta acceso come prima
            avanzamento("Riaccendo Gradiens…")
            cli._avvia_staccato(conf)
            cli._attendi(lambda: cli.leggi_stato(conf) is not None)
    return f"Gradiens è aggiornato ({nuove.stdout.strip()} modifiche nuove)."
