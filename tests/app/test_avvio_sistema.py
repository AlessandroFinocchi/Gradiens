import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

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


# ---- Avvio all'accensione (AMB-04) ----

@pytest.fixture
def systemd(tmp_path, monkeypatch):
    """systemctl e loginctl finti: registrano i comandi e rispondono come un sistema con systemd."""
    monkeypatch.setattr(avvio_sistema, "os", SimpleNamespace(name="posix", environ={"XDG_CONFIG_HOME": str(tmp_path)}))
    monkeypatch.setattr(avvio_sistema.shutil, "which", lambda nome: f"/usr/bin/{nome}")
    monkeypatch.setattr(avvio_sistema, "_cache", None)
    finto = SimpleNamespace(comandi=[], abilitato=False, linger="no")

    def esegui(comando):
        finto.comandi.append(comando[1:] if comando[0] == "systemctl" else comando)
        uscita = ""
        if comando[-2:] == ["is-enabled", "gradiens.service"]:
            uscita = "enabled" if finto.abilitato else "disabled"
        elif comando[:2] == ["systemctl", "--user"] and comando[2] in ("enable", "disable"):
            finto.abilitato = comando[2] == "enable"
        elif comando[:2] == ["loginctl", "show-user"]:
            uscita = finto.linger
        elif comando[:2] == ["loginctl", "enable-linger"]:
            finto.linger = "yes"
        return subprocess.CompletedProcess(comando, 0, uscita, "")

    monkeypatch.setattr(avvio_sistema, "_esegui", esegui)
    finto.file = tmp_path / "systemd" / "user" / "gradiens.service"
    return finto


def test_unita_systemd_con_virgolette_e_percento():
    unita = avvio_sistema.unita_systemd(Path("/home/a/Gradiens 100%"), "/home/a/x/python", "/home/a/.local/bin/claude")
    assert "WorkingDirectory=/home/a/Gradiens 100%%\n" in unita
    assert 'ExecStart="/home/a/x/python" "-m" "gradiens" "avvia" "--primo-piano"\n' in unita
    assert 'Environment="GRADIENS_CLAUDE=/home/a/.local/bin/claude"\n' in unita  # niente PATH della shell al boot
    assert "Environment" not in avvio_sistema.unita_systemd(Path("/g"), "/p", None)


def test_linux_attiva_controlla_e_disattiva(systemd, tmp_path):
    assert avvio_sistema.stato_avvio(tmp_path) == avvio_sistema.StatoAvvio(False)
    assert avvio_sistema.attiva_avvio(tmp_path) == avvio_sistema.StatoAvvio(True)
    assert systemd.file.exists() and systemd.abilitato and systemd.linger == "yes"
    assert ["--user", "enable", "gradiens.service"] in systemd.comandi
    assert not any("start" in c or "--now" in c for c in systemd.comandi)  # parte al prossimo avvio, non adesso

    avvio_sistema.disattiva_avvio(tmp_path)
    assert not systemd.file.exists() and not systemd.abilitato
    assert avvio_sistema.stato_avvio(tmp_path).attivo is False


def test_linux_registrazione_da_rifare_o_senza_lingering(systemd, tmp_path):
    avvio_sistema.attiva_avvio(tmp_path)
    avvio_sistema._cache = None
    assert "altra cartella" in avvio_sistema.stato_avvio(tmp_path / "spostata").problema

    systemd.linger = "no"  # es. la distribuzione chiede la password per il lingering
    avvio_sistema._cache = None
    stato = avvio_sistema.stato_avvio(tmp_path)
    assert "dopo l'accesso" in stato.problema and stato.comando.startswith("sudo loginctl enable-linger ")

    systemd.abilitato = False
    avvio_sistema._cache = None
    assert "non è abilitato" in avvio_sistema.stato_avvio(tmp_path).problema


def test_script_windows_con_apostrofi_e_utente_letto_prima_dell_elevazione():
    script = avvio_sistema.script_windows(Path(r"C:\Users\D'Amico\Gradiens"), r"C:\G\.venv\Scripts\python.exe", r"PC\D'Amico")
    assert r"-WorkingDirectory 'C:\Users\D''Amico\Gradiens'" in script
    assert r"-UserId 'PC\D''Amico' -LogonType S4U" in script
    assert "-AtStartup" in script and "-TaskName 'Gradiens'" in script


XML_ATTIVITA = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Settings><Enabled>{abilitata}</Enabled></Settings>
  <Actions Context="Author"><Exec>
    <Command>"C:\\G\\.venv\\Scripts\\python.exe"</Command><Arguments>-m gradiens avvia --primo-piano</Arguments>
    <WorkingDirectory>C:\\G</WorkingDirectory>
  </Exec></Actions>
</Task>"""


def test_stato_dell_attivita_pianificata():
    python = r"C:\G\.venv\Scripts\python.exe"
    assert avvio_sistema.stato_da_xml(XML_ATTIVITA.format(abilitata="true"), Path(r"C:\G"), python).problema is None
    assert "altra cartella" in avvio_sistema.stato_da_xml(XML_ATTIVITA.format(abilitata="true"), Path(r"C:\H"), python).problema
    assert "disabilitata" in avvio_sistema.stato_da_xml(XML_ATTIVITA.format(abilitata="false"), Path(r"C:\G"), python).problema


def test_senza_systemd_lo_stato_diventa_un_problema_non_un_errore(systemd, tmp_path, monkeypatch):
    # Interruttore acceso su un sistema senza systemctl: il file resta, ma le pagine non devono rompersi.
    monkeypatch.setattr(avvio_sistema.shutil, "which", lambda nome: None)
    with pytest.raises(avvio_sistema.ErroreAvvio, match="non usa systemd"):
        avvio_sistema.attiva_avvio(tmp_path)
    avvio_sistema._cache = None
    stato = avvio_sistema.stato_avvio(tmp_path)
    assert stato.attivo and "non usa systemd" in stato.problema
