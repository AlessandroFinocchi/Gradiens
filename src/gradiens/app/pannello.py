"""Pannello di controllo (AMB-05, ADR 0009): una finestrella per accendere e spegnere Gradiens e vederne lo
stato senza terminale. Parla con il servizio come la CLI, quindi vede anche un Gradiens partito all'accensione,
e chiuderla non lo spegne. Tkinter fa parte di Python: funziona uguale su Windows e su Linux, anche con Wayland.
"""

import queue
import threading
import time
import tkinter as tk
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from tkinter import messagebox, ttk

import httpx

from gradiens.app import aggiornamento
from gradiens.app.cli import ATTESA_MASSIMA, _avvia_staccato, leggi_stato, richiedi_spegnimento
from gradiens.app.configurazione import Configurazione

ICONA = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "gradiens.png"
OGNI = 3  # secondi tra due letture dello stato
COLORI = {"spento": "#9A9A9A", "acceso": "#2E8B57", "in_corso": "#B4512F", "attesa": "#C9A227"}


def descrivi(dati: dict | None) -> tuple[str, str, str]:
    """(stato del pallino, titolo, dettaglio) dalla risposta di /api/stato, o da None se Gradiens è spento."""
    if dati is None:
        return "spento", "Gradiens è spento", "Premi Accendi per farlo partire."
    ultima = dati.get("ultima_esecuzione") or {}
    if ultima.get("stato") == "in_corso":
        avvio = datetime.fromisoformat(ultima["avviata_il"]).replace(tzinfo=UTC).astimezone()
        return "in_corso", "Esecuzione in corso", f"Avviata alle {avvio:%H:%M}. Gradiens è acceso."
    if prossima := dati.get("prossima_esecuzione"):
        return "acceso", "Gradiens è acceso", f"Prossima esecuzione: {datetime.fromisoformat(prossima):%d/%m alle %H:%M}."
    return "acceso", "Gradiens è acceso", "La programmazione è in pausa."


class Pannello:
    def __init__(self, conf: Configurazione):
        self._conf = conf
        self._letture: queue.Queue = queue.Queue()  # dal thread che legge lo stato: Tkinter si usa solo nel principale
        self._dati: dict | None = None
        self._attesa: tuple[str, float] | None = None  # ("accensione" | "spegnimento" | "aggiornamento", scadenza)
        self._passo = ""  # cosa sta facendo l'aggiornamento, scritto dal suo thread
        self._esiti: queue.Queue = queue.Queue()  # (testo, è un errore) alla fine dell'aggiornamento

        self.finestra = tk.Tk()
        self.finestra.title("Gradiens")
        self.finestra.resizable(False, False)
        if ICONA.exists():
            self.finestra.iconphoto(True, tk.PhotoImage(file=str(ICONA)))
        corpo = ttk.Frame(self.finestra, padding=20)
        corpo.grid()
        self._pallino = tk.Canvas(corpo, width=16, height=16, highlightthickness=0)
        self._pallino.grid(row=0, column=0, padx=(0, 10))
        self._cerchio = self._pallino.create_oval(2, 2, 14, 14, fill=COLORI["spento"], outline="")
        self._titolo = ttk.Label(corpo, font=("TkDefaultFont", 13, "bold"))
        self._titolo.grid(row=0, column=1, sticky="w")
        self._dettaglio = ttk.Label(corpo, wraplength=320)
        self._dettaglio.grid(row=1, column=1, sticky="w", pady=(2, 16))
        bottoni = ttk.Frame(corpo)
        bottoni.grid(row=2, column=0, columnspan=2, sticky="w")
        self._accendi = ttk.Button(bottoni, text="Accendi", command=self._premi_accendi)
        self._spegni = ttk.Button(bottoni, text="Spegni", command=self._premi_spegni)
        self._apri = ttk.Button(bottoni, text="Apri la dashboard", command=lambda: webbrowser.open(conf.indirizzo_locale))
        self._aggiorna = ttk.Button(bottoni, text="Aggiorna", command=self._premi_aggiorna)
        for colonna, bottone in enumerate((self._accendi, self._spegni, self._apri, self._aggiorna)):
            bottone.grid(row=0, column=colonna, padx=(0, 8))

        threading.Thread(target=self._leggi_sempre, daemon=True).start()
        self._mostra()
        self.finestra.after(200, self._controlla)

    def _leggi_sempre(self) -> None:
        while True:
            self._letture.put(leggi_stato(self._conf))
            time.sleep(OGNI)

    def _controlla(self) -> None:
        try:
            while True:
                self._dati = self._letture.get_nowait()
        except queue.Empty:
            pass
        try:
            testo, errore = self._esiti.get_nowait()
            self._attesa = None
            (messagebox.showerror if errore else messagebox.showinfo)("Gradiens", testo)
        except queue.Empty:
            pass
        if self._attesa and self._attesa[0] != "aggiornamento":
            cosa, scadenza = self._attesa
            if (cosa == "accensione") == (self._dati is not None):
                self._attesa = None
            elif time.monotonic() > scadenza:
                self._attesa = None
                messagebox.showerror("Gradiens", "Gradiens non è partito. I dettagli sono nei log, nella cartella "
                                     f"{self._conf.cartella_log}." if cosa == "accensione"
                                     else "Gradiens non si è spento in tempo. Riprova tra poco.")
        self._mostra()
        self.finestra.after(500, self._controlla)

    def _mostra(self) -> None:
        if self._attesa and self._attesa[0] == "aggiornamento":
            stato, titolo, dettaglio = "attesa", "Aggiornamento in corso…", self._passo
        elif self._attesa:
            stato, titolo = "attesa", "Si sta accendendo…" if self._attesa[0] == "accensione" else "Si sta spegnendo…"
            dettaglio = "Ci vuole qualche secondo."
        else:
            stato, titolo, dettaglio = descrivi(self._dati)
        self._pallino.itemconfigure(self._cerchio, fill=COLORI[stato])
        self._titolo.configure(text=titolo)
        self._dettaglio.configure(text=dettaglio)
        acceso = self._dati is not None and not self._attesa
        self._accendi.state(["!disabled"] if self._dati is None and not self._attesa else ["disabled"])
        self._spegni.state(["!disabled"] if acceso else ["disabled"])
        self._apri.state(["!disabled"] if acceso else ["disabled"])
        self._aggiorna.state(["disabled"] if self._attesa else ["!disabled"])

    def _premi_accendi(self) -> None:
        self._attesa = "accensione", time.monotonic() + ATTESA_MASSIMA
        threading.Thread(target=_avvia_staccato, args=(self._conf,), daemon=True).start()
        self._mostra()

    def _premi_spegni(self) -> None:
        in_corso = (self._dati or {}).get("ultima_esecuzione", {}) or {}
        if in_corso.get("stato") == "in_corso" and not messagebox.askyesno(
                "Gradiens", "C'è un'esecuzione in corso: verrà interrotta e le notizie rimaste si riprenderanno "
                            "alla prossima. Spegnere Gradiens?"):
            return
        try:
            richiedi_spegnimento(self._conf)
        except httpx.HTTPError as errore:
            messagebox.showerror("Gradiens", f"Spegnimento non riuscito: {errore}")
            return
        self._attesa = "spegnimento", time.monotonic() + ATTESA_MASSIMA
        self._mostra()


    def _premi_aggiorna(self) -> None:
        self._attesa, self._passo = ("aggiornamento", float("inf")), "Controllo se c'è una versione nuova…"

        def lavora() -> None:
            try:
                self._esiti.put((aggiornamento.aggiorna(self._conf, self._imposta_passo), False))
            except Exception as errore:  # anche un errore imprevisto deve sbloccare il pannello
                self._esiti.put((str(errore), True))

        threading.Thread(target=lavora, daemon=True).start()
        self._mostra()

    def _imposta_passo(self, testo: str) -> None:
        self._passo = testo


def apri(conf: Configurazione) -> int:
    Pannello(conf).finestra.mainloop()
    return 0
