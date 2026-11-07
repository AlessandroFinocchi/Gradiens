import socket

import pytest
from fastapi.testclient import TestClient

from gradiens.app.configurazione import Configurazione
from gradiens.app.servizio import crea_app


def porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def conf(tmp_path) -> Configurazione:
    # _env_file=None: i test non leggono mai il .env vero con le chiavi.
    return Configurazione(_env_file=None, cartella_dati=tmp_path / ".gradiens", porta=porta_libera(),
                          file_env=tmp_path / ".env")


@pytest.fixture
def client(conf) -> TestClient:
    return TestClient(crea_app(conf), base_url="http://127.0.0.1")

