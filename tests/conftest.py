import socket

import pytest
from fastapi.testclient import TestClient

from gradiens.app import avvio_sistema
from gradiens.app.configurazione import Configurazione
from gradiens.app.servizio import crea_app
from gradiens.dashboard import rotte_configurazione
from gradiens.dati import impostazioni
from gradiens.esecuzione import esecutore


def porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def senza_avvio_registrato(monkeypatch):
    """I test non leggono la registrazione vera dell'avvio all'accensione (systemd o Utilità di pianificazione)."""
    monkeypatch.setattr(avvio_sistema, "_cache", (float("inf"), avvio_sistema.StatoAvvio(False)))
    monkeypatch.setattr(esecutore, "rete_disponibile", lambda: True)  # né la rete vera


@pytest.fixture
def conf(tmp_path) -> Configurazione:
    # _env_file=None: i test non leggono mai il .env vero con le chiavi.
    return Configurazione(_env_file=None, cartella_dati=tmp_path / ".gradiens", porta=porta_libera(),
                          file_env=tmp_path / ".env")


@pytest.fixture
def client_nuovo(conf, monkeypatch) -> TestClient:
    """Gradiens appena installato: la dashboard porta alla configurazione iniziale (UI-11)."""
    monkeypatch.setattr(rotte_configurazione, "stato_account", lambda: "abbonamento Pro")  # niente `claude` vero
    return TestClient(crea_app(conf), base_url="http://127.0.0.1")


@pytest.fixture
def client(client_nuovo) -> TestClient:
    """Gradiens con la configurazione iniziale già completata."""
    with client_nuovo.app.state.sessioni() as s:
        impostazioni.leggi(s).configurazione_completata = True
        s.commit()
    return client_nuovo

