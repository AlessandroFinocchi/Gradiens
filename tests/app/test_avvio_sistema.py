from pathlib import Path
from types import SimpleNamespace

from gradiens.app import avvio_sistema
from gradiens.app.avvio_sistema import eseguibile_claude


def test_su_windows_lo_script_npm_diventa_l_eseguibile_nativo(monkeypatch):
    # Si sostituisce solo `os` del modulo: pathlib altrove deve restare quello del sistema vero.
    monkeypatch.setattr(avvio_sistema, "os", SimpleNamespace(name="nt"))
    nativo = eseguibile_claude(Path("npm/claude.CMD"))
    assert nativo == Path("npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe")


def test_su_linux_il_percorso_resta_quello(monkeypatch):
    monkeypatch.setattr(avvio_sistema, "os", SimpleNamespace(name="posix"))
    assert eseguibile_claude(Path("bin/claude")) == Path("bin/claude")
