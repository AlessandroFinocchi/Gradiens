"""gradiens aggiorna: con repository git veri ma temporanei, uv e il servizio finti."""

import subprocess

import pytest

from gradiens.app import aggiornamento


def git(cartella, *argomenti):
    subprocess.run(["git", "-c", "user.name=Prova", "-c", "user.email=prova@example.org", "-c", "init.defaultBranch=main",
                    *argomenti], cwd=cartella, check=True, capture_output=True)


@pytest.fixture
def installazione(tmp_path, monkeypatch):
    """Una copia "installata" che segue un repository remoto, e un'altra copia per pubblicare versioni nuove."""
    remoto, sviluppo, installata = tmp_path / "remoto.git", tmp_path / "sviluppo", tmp_path / "installata"
    git(tmp_path, "init", "--bare", str(remoto))
    git(tmp_path, "clone", str(remoto), str(sviluppo))
    (sviluppo / "README.md").write_text("v1\n", encoding="utf-8")
    git(sviluppo, "add", ".")
    git(sviluppo, "commit", "-m", "v1")
    git(sviluppo, "push", "origin", "HEAD:main")
    git(tmp_path, "clone", str(remoto), str(installata))

    eventi = []
    originale = aggiornamento._comando
    monkeypatch.setattr(aggiornamento, "eseguibile", lambda nome: "git" if nome == "git" else "UV")
    monkeypatch.setattr(aggiornamento, "_comando", lambda a, c: eventi.append("uv sync") or subprocess.CompletedProcess(a, 0, "", "")
                        if a[0] == "UV" else originale(a, c))
    monkeypatch.setattr(aggiornamento.cli, "_attendi", lambda condizione: True)
    monkeypatch.setattr(aggiornamento.cli, "richiedi_spegnimento", lambda conf: eventi.append("spegni"))
    monkeypatch.setattr(aggiornamento.cli, "_avvia_staccato", lambda conf: eventi.append("riaccendi"))
    monkeypatch.setattr(aggiornamento.cli, "leggi_stato", lambda conf: None)

    def pubblica(testo):
        (sviluppo / "README.md").write_text(testo, encoding="utf-8")
        git(sviluppo, "commit", "-am", testo)
        git(sviluppo, "push", "origin", "HEAD:main")

    return installata, pubblica, eventi


def test_gia_aggiornato(installazione):
    installata, _, eventi = installazione
    assert aggiornamento.aggiorna(None, lambda _: None, installata) == "Gradiens è già aggiornato."
    assert eventi == []


def test_scarica_aggiorna_le_dipendenze_e_riaccende(installazione, monkeypatch):
    installata, pubblica, eventi = installazione
    pubblica("v2\n")
    monkeypatch.setattr(aggiornamento.cli, "leggi_stato", lambda conf: {"acceso": True})
    assert aggiornamento.aggiorna(None, lambda _: None, installata) == "Gradiens è aggiornato (1 modifiche nuove)."
    assert (installata / "README.md").read_text(encoding="utf-8") == "v2\n"
    assert eventi == ["spegni", "uv sync", "riaccendi"]  # su Windows i file in uso non si sostituiscono


def test_non_tocca_le_modifiche_locali(installazione):
    installata, pubblica, eventi = installazione
    pubblica("v2\n")
    (installata / "README.md").write_text("modificato a mano\n", encoding="utf-8")
    with pytest.raises(aggiornamento.ErroreAggiornamento, match="modifiche locali"):
        aggiornamento.aggiorna(None, lambda _: None, installata)
    assert (installata / "README.md").read_text(encoding="utf-8") == "modificato a mano\n" and eventi == []


def test_non_interrompe_un_esecuzione_in_corso(installazione, monkeypatch):
    installata, pubblica, eventi = installazione
    pubblica("v2\n")
    monkeypatch.setattr(aggiornamento.cli, "leggi_stato", lambda conf: {"ultima_esecuzione": {"stato": "in_corso"}})
    with pytest.raises(aggiornamento.ErroreAggiornamento, match="esecuzione è in corso"):
        aggiornamento.aggiorna(None, lambda _: None, installata)
    assert (installata / "README.md").read_text(encoding="utf-8") == "v1\n" and eventi == []  # niente spento né scaricato
