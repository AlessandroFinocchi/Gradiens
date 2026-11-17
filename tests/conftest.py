import socket
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

from gradiens.app import avvio_sistema
from gradiens.app.configurazione import Configurazione
from gradiens.app.servizio import crea_app
from gradiens.dashboard import rotte_configurazione
from gradiens.dati import impostazioni
from gradiens.esecuzione import esecutore


def porte_libere(quante: int) -> list[int]:
    """Porte diverse tra loro: le prese restano aperte finché non sono state lette tutte."""
    with ExitStack() as pila:
        prese = [pila.enter_context(socket.socket()) for _ in range(quante)]
        for presa in prese:
            presa.bind(("127.0.0.1", 0))
        return [presa.getsockname()[1] for presa in prese]


@pytest.fixture(autouse=True)
def senza_avvio_registrato(monkeypatch, tmp_path):
    """I test non leggono la registrazione vera dell'avvio all'accensione (systemd o Utilità di pianificazione)."""
    monkeypatch.setattr(avvio_sistema, "_cache", (float("inf"), avvio_sistema.StatoAvvio(False)))
    monkeypatch.setattr(esecutore, "rete_disponibile", lambda: True)  # né la rete vera
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))  # né il login vero di Claude Code


@pytest.fixture
def conf(tmp_path) -> Configurazione:
    # _env_file=None: i test non leggono mai il .env vero con le chiavi.
    porta, porta_remota = porte_libere(2)
    return Configurazione(_env_file=None, cartella_dati=tmp_path / ".gradiens", porta=porta, porta_remota=porta_remota,
                          file_env=tmp_path / ".env")


@pytest.fixture
def client_nuovo(conf, monkeypatch) -> TestClient:
    """Gradiens appena installato: la dashboard porta alla configurazione iniziale (UI-11)."""
    monkeypatch.setattr(rotte_configurazione, "stato_account", lambda: "abbonamento Pro")  # niente `claude` vero
    # Dal PC: porta principale e cliente locale (ADR 0013, `comune.dal_pc`).
    return TestClient(crea_app(conf), base_url=f"http://127.0.0.1:{conf.porta}", client=("127.0.0.1", 50000))


@pytest.fixture
def client(client_nuovo) -> TestClient:
    """Gradiens con la configurazione iniziale già completata."""
    with client_nuovo.app.state.sessioni() as s:
        impostazioni.leggi(s).configurazione_completata = True
        s.commit()
    return client_nuovo

