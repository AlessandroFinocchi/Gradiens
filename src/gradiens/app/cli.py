"""Comandi da terminale: gradiens avvia | esegui | stato | spegni (PRD CLI-01..04)."""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

import httpx

from gradiens.app.configurazione import Configurazione, configurazione

ATTESA_MASSIMA = 20  # secondi per l'avvio o lo spegnimento
INTESTAZIONE_CLI = {"X-Gradiens-Cli": "1"}


def leggi_stato(conf: Configurazione) -> dict | None:
    """Stato del servizio in esecuzione, oppure None se non risponde."""
    try:
        risposta = httpx.get(f"{conf.indirizzo_locale}/api/stato", timeout=2)
        risposta.raise_for_status()
        return risposta.json()
    except (httpx.HTTPError, ValueError):
        return None


def _attendi(condizione, secondi: float = ATTESA_MASSIMA) -> bool:
    fine = time.monotonic() + secondi
    while time.monotonic() < fine:
        if condizione():
            return True
        time.sleep(0.3)
    return False


def _avvia_staccato(conf: Configurazione) -> None:
    """Lancia il servizio come processo indipendente dal terminale (e dalla sessione SSH)."""
    conf.cartella_log.mkdir(parents=True, exist_ok=True)
    comando = [sys.executable, "-m", "gradiens", "avvia", "--primo-piano"]
    with open(conf.cartella_log / "avvio.log", "ab") as errori:
        opzioni = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errori, close_fds=True)
        if os.name != "nt":
            subprocess.Popen(comando, start_new_session=True, **opzioni)
            return
        base = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            # Esce dal "job" della sessione SSH, che altrimenti chiuderebbe Gradiens all'uscita.
            subprocess.Popen(comando, creationflags=base | subprocess.CREATE_BREAKAWAY_FROM_JOB, **opzioni)
        except OSError:
            subprocess.Popen(comando, creationflags=base, **opzioni)


def avvia(conf: Configurazione, primo_piano: bool) -> int:
    if leggi_stato(conf) is not None:
        print(f"Gradiens è già in esecuzione: {conf.indirizzo_locale}")
        return 0
    if primo_piano:
        from gradiens.app import servizio  # import qui: la CLI resta veloce per stato e spegni

        servizio.esegui(conf)
        return 0
    _avvia_staccato(conf)
    if _attendi(lambda: leggi_stato(conf) is not None):
        print(f"Gradiens è in esecuzione: {conf.indirizzo_locale}")
        return 0
    print(f"Gradiens non è partito. Guarda i log in {conf.cartella_log}", file=sys.stderr)
    return 1


def stato(conf: Configurazione) -> int:
    dati = leggi_stato(conf)
    if dati is None:
        print("Gradiens non è in esecuzione.")
        return 1
    dal = datetime.fromisoformat(dati["avviato_alle"]).strftime("%d/%m alle %H:%M")
    print(f"Gradiens è in esecuzione dal {dal}: {conf.indirizzo_locale}")
    return 0


def spegni(conf: Configurazione) -> int:
    if leggi_stato(conf) is None:
        print("Gradiens non è in esecuzione.")
        return 0
    try:
        httpx.post(f"{conf.indirizzo_locale}/api/spegni", headers=INTESTAZIONE_CLI, timeout=5).raise_for_status()
    except httpx.HTTPError as errore:
        print(f"Spegnimento non riuscito: {errore}", file=sys.stderr)
        return 1
    if _attendi(lambda: leggi_stato(conf) is None):
        print("Gradiens è spento.")
        return 0
    print("Gradiens non si è spento in tempo.", file=sys.stderr)
    return 1


def _riepilogo(ultima: dict) -> str:
    righe = [f"Esecuzione {ultima['stato']}."]
    if ultima.get("motivo"):
        righe.append(f"Motivo: {ultima['motivo']}")
    m = ultima.get("metriche") or {}
    if a := m.get("arxiv"):
        righe.append(
            f"arXiv: {a['esaminate']} esaminate, {a['scartate_prefiltro']} scartate dal pre-filtro, "
            f"{a['oltre_tetto']} oltre il tetto, {a['scartate_valutazione']} scartate dalla valutazione, "
            f"{a['mostrate']} mostrate, {a['errori']} errori."
        )
    if t := m.get("token"):
        righe.append("Token: " + ", ".join(f"{r} {v['ingresso']} in ingresso e {v['uscita']} in uscita" for r, v in t.items()))
    if "durata_s" in m:
        righe.append(f"Durata: {m['durata_s']} s")
    return "\n".join(righe)


def esegui(conf: Configurazione) -> int:
    """Lancia un'esecuzione nel servizio (avviandolo se serve), ne mostra l'avanzamento e le metriche (CLI-02)."""
    if leggi_stato(conf) is None and avvia(conf, primo_piano=False) != 0:
        return 1
    risposta = httpx.post(f"{conf.indirizzo_locale}/api/esegui", headers=INTESTAZIONE_CLI, timeout=10)
    if risposta.status_code == 409:
        print("Esecuzione già in corso.")
        return 1
    risposta.raise_for_status()
    id = risposta.json()["esecuzione_id"]
    print(f"Esecuzione {id} avviata. Ctrl+C chiude solo questo comando: l'esecuzione continua.")
    ultimo_messaggio = ""
    while True:
        time.sleep(1)
        try:
            dati = httpx.get(f"{conf.indirizzo_locale}/api/esecuzione", timeout=10).json()
        except (httpx.HTTPError, ValueError):  # es. `gradiens spegni` da un altro terminale
            print("Gradiens non risponde più: l'esecuzione è stata interrotta.", file=sys.stderr)
            return 1
        avanzamento = dati["avanzamento"]
        if avanzamento is None or avanzamento["esecuzione_id"] != id:
            break
        messaggio = f"  {avanzamento['fase']}: {avanzamento['fatti']} di {avanzamento['totale']}"
        if messaggio != ultimo_messaggio:
            print(messaggio, flush=True)
            ultimo_messaggio = messaggio
    print(_riepilogo(dati["ultima"]))
    return 0 if dati["ultima"]["stato"] == "completata" else 1


def main(argv: list[str] | None = None) -> int:
    # Su Windows l'output verso pipe e SSH userebbe cp1252 e le lettere accentate si rovinano.
    # Senza terminale (es. pythonw) i flussi valgono None.
    for flusso in (sys.stdout, sys.stderr):
        if flusso is not None:
            flusso.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="gradiens", description="Notizie filtrate e riassunte in base ai tuoi interessi.")
    comandi = parser.add_subparsers(dest="comando", required=True, metavar="comando")
    p_avvia = comandi.add_parser("avvia", help="fa partire dashboard, programmazione giornaliera e bot Telegram")
    p_avvia.add_argument("--primo-piano", action="store_true", help="resta collegato al terminale invece di staccarsi")
    comandi.add_parser("esegui", help="lancia un'esecuzione, ne mostra l'avanzamento e le metriche")
    comandi.add_parser("stato", help="mostra se Gradiens è in esecuzione")
    comandi.add_parser("spegni", help="termina l'applicazione")
    args = parser.parse_args(argv)

    conf = configurazione()
    if args.comando == "avvia":
        return avvia(conf, args.primo_piano)
    if args.comando == "esegui":
        return esegui(conf)
    if args.comando == "stato":
        return stato(conf)
    return spegni(conf)
