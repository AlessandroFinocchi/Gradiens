import socket

import pytest
from fastapi.testclient import TestClient

from gradiens.app.configurazione import RADICE, Configurazione
from gradiens.app.servizio import apri_prese, configurazione_uvicorn, crea_app

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
    da_fuori = TestClient(app, base_url=f"http://127.0.0.1:{conf.porta}", client=("192.168.1.20", 50000))
    assert da_fuori.post("/api/spegni", headers={"X-Gradiens-Cli": "1"}).status_code == 403
    for indirizzo in ("127.0.0.1", "::1"):
        locale = TestClient(app, base_url=f"http://127.0.0.1:{conf.porta}", client=(indirizzo, 50000))
        assert locale.post("/api/spegni", headers={"X-Gradiens-Cli": "1"}).status_code == 200


def test_dalla_porta_per_tailscale_serve_non_si_spegne(conf):
    # ADR 0013: Serve inoltra da 127.0.0.1 e l'Host lo scrive il cliente;
    # conta solo la porta su cui arriva la richiesta.
    app = crea_app(conf)
    da_serve = TestClient(app, base_url=f"http://127.0.0.1:{conf.porta_remota}", client=("127.0.0.1", 50000))
    assert da_serve.post("/api/spegni", headers={"X-Gradiens-Cli": "1"}).status_code == 403


def test_le_due_porte_devono_essere_diverse(tmp_path):
    # Con la stessa porta anche la CLI e il pannello conterebbero come fuori casa e verrebbero rifiutati.
    with pytest.raises(ValueError, match="GRADIENS_PORTA_REMOTA"):
        Configurazione(_env_file=None, cartella_dati=tmp_path, porta=8766, porta_remota=8766)


def test_uvicorn_ha_valori_scritti_nel_codice(conf, monkeypatch):
    # Non cambiano con la variabile d'ambiente né con una versione nuova di uvicorn: uvicorn si fida della
    # X-Forwarded-For scritta da Serve su 127.0.0.1, così il log registra il dispositivo Tailscale che chiede.
    monkeypatch.setenv("FORWARDED_ALLOW_IPS", "*")
    config = configurazione_uvicorn(crea_app(conf))
    assert config.proxy_headers is True
    assert config.forwarded_allow_ips == "127.0.0.1,::1"


def test_gradiens_ascolta_sulla_porta_principale_e_su_quella_per_serve(conf):
    prese = apri_prese(conf)
    try:
        assert [p.getsockname() for p in prese] == [("127.0.0.1", conf.porta), ("127.0.0.1", conf.porta_remota)]
    finally:
        for p in prese:
            p.close()


def test_con_la_porta_per_serve_occupata_gradiens_parte_lo_stesso(conf, caplog):
    with socket.create_server(("127.0.0.1", conf.porta_remota)):
        prese = apri_prese(conf)
    try:
        assert [p.getsockname() for p in prese] == [("127.0.0.1", conf.porta)]
    finally:
        for p in prese:
            p.close()
    assert str(conf.porta_remota) in caplog.text


def test_la_dashboard_non_si_mostra_dentro_altre_pagine(client):
    # Contro l'incorniciamento (clickjacking): i clic dentro una cornice passerebbero la difesa CSRF.
    for risposta in (client.get("/"), client.get("/static/app.js")):
        assert risposta.headers["X-Frame-Options"] == "DENY"
        assert risposta.headers["Content-Security-Policy"] == "frame-ancestors 'none'"


def test_api_esecuzione_rifiuta_la_seconda_e_mostra_l_avanzamento(client):
    from gradiens.esecuzione.metriche import Avanzamento

    client.app.state.esecutore.avanzamento = Avanzamento(esecuzione_id=7, fase="valutazione", fatti=2, totale=5)
    cli = {"X-Gradiens-Cli": "1"}
    assert client.post("/api/esegui", headers=cli).status_code == 409  # ESE-02
    dati = client.get("/api/esecuzione").json()
    assert dati["avanzamento"]["fase"] == "valutazione"
    assert dati["ultima"] is None
