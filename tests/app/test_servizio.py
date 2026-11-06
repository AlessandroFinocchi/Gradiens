from fastapi.testclient import TestClient

from gradiens.app.configurazione import RADICE, Configurazione
from gradiens.app.servizio import crea_app

HTMX = {"HX-Request": "true"}


def test_i_dati_stanno_dentro_la_repository():
    # PER-02, PER-03: niente fuori dalla cartella del progetto.
    assert Configurazione(_env_file=None).cartella_dati.is_relative_to(RADICE)


def test_le_pagine_si_aprono_con_la_sidebar(client):
    for percorso in ["/", "/notizie", "/timeline", "/archivio", "/aiuto"]:
        risposta = client.get(percorso)
        assert risposta.status_code == 200, percorso
        assert 'aria-label="Pagine"' in risposta.text


def test_nome_host_sconosciuto_rifiutato(conf):
    # Difesa dal DNS rebinding: un sito che punta il suo dominio a 127.0.0.1 non entra.
    client = TestClient(crea_app(conf), base_url="http://sito-malevolo.example")
    assert client.get("/").status_code == 400


def test_modifica_senza_intestazione_htmx_rifiutata(client):
    # Una form inviata da un altro sito (CSRF) non può aggiungere l'intestazione.
    assert client.post("/impostazioni/tema", data={"tema": "dark"}).status_code == 403


def test_cambio_tema_salvato_e_applicato(client):
    risposta = client.post("/impostazioni/tema", data={"tema": "dark"}, headers=HTMX)
    assert risposta.status_code == 200
    assert "tema-cambiato" in risposta.headers["HX-Trigger"]
    assert 'data-theme="dark"' in client.get("/").text


def test_tema_non_valido_rifiutato(client):
    assert client.post("/impostazioni/tema", data={"tema": "viola"}, headers=HTMX).status_code == 422


def test_sezione_inesistente(client):
    assert client.get("/impostazioni/inesistente").status_code == 404
    assert client.get("/impostazioni/aspetto").status_code == 200


def test_spegnimento_solo_dal_pc_stesso(conf):
    app = crea_app(conf)
    da_fuori = TestClient(app, base_url="http://127.0.0.1", client=("192.168.1.20", 50000))
    assert da_fuori.post("/api/spegni", headers={"X-Gradiens-Cli": "1"}).status_code == 403
    locale = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000))
    assert locale.post("/api/spegni", headers={"X-Gradiens-Cli": "1"}).status_code == 200


def test_api_esecuzione_rifiuta_la_seconda_e_mostra_l_avanzamento(client):
    from gradiens.esecuzione.esecutore import Avanzamento

    client.app.state.esecutore.avanzamento = Avanzamento(esecuzione_id=7, fase="valutazione", fatti=2, totale=5)
    cli = {"X-Gradiens-Cli": "1"}
    assert client.post("/api/esegui", headers=cli).status_code == 409  # ESE-02
    dati = client.get("/api/esecuzione").json()
    assert dati["avanzamento"]["fase"] == "valutazione"
    assert dati["ultima"] is None
