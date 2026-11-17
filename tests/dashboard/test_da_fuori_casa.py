"""Dashboard da fuori casa con Tailscale Serve (ADR 0013, decisioni 53-56)."""

import json

import pytest
from fastapi.testclient import TestClient

from gradiens.app import avvio_sistema
from gradiens.app.servizio import crea_app
from gradiens.dashboard.comune import SOLO_DAL_PC
from gradiens.dashboard.rotte_impostazioni import ALZARE_SOLO_DAL_PC
from gradiens.dati import impostazioni, interessi
from gradiens.dati import siti as dati_siti
from gradiens.dati.modelli import CanaleYoutube, Notizia, Sito
from gradiens.dati.notizie import adesso
from gradiens.fonti import siti
from gradiens.telegram import bot as telegram

HTMX = {"HX-Request": "true"}
NOME = "pc.tail1234.ts.net"
IDENTITA = {"Tailscale-User-Login": "io@example.com"}  # Serve la aggiunge per i dispositivi della rete Tailscale


def cliente(app, host: str, porta: int, **intestazioni) -> TestClient:
    # Serve inoltra da 127.0.0.1: il cliente è sempre locale, conta la porta.
    return TestClient(app, base_url=f"http://{host}:{porta}", client=("127.0.0.1", 50000), headers=intestazioni)


def da_fuori(app) -> TestClient:
    """Il telefono nella rete Tailscale, con l'accesso attivato dal PC: Serve inoltra sulla seconda porta,
    con il nome Tailscale come Host e l'identità di chi chiede."""
    dal_pc = cliente(app, "127.0.0.1", app.state.conf.porta, **HTMX)
    assert dal_pc.post("/impostazioni/accesso", data={"attivo": "true", "indirizzo": f"https://{NOME}/"}).status_code == 200
    return cliente(app, NOME, app.state.conf.porta_remota, **HTMX, **IDENTITA)


@pytest.fixture
def remoto(client) -> TestClient:
    return da_fuori(client.app)


@pytest.fixture
def fonti(client):
    """Un interesse, una fonte per tipo e una notizia con il cuore."""
    with client.app.state.sessioni() as s:
        interesse = interessi.aggiungi(s, "Sicurezza", "attacchi")
        impostazioni.aggiungi_categoria(s, "cs.CR")
        impostazioni.aggiungi_canale(s, "UC" + "x" * 22, "Canale")
        sito = dati_siti.aggiungi(s, "https://hwupgrade.it/", siti.Profilo(url="https://hwupgrade.it/").come_dict())
        notizia = Notizia(tipo="sito", url="https://hwupgrade.it/a", fonte="hwupgrade.it", titolo="Con il cuore",
                          riassunto="Riassunto.", pubblicata_il=adesso(), scoperta_il=adesso(), cuore=True)
        s.add(notizia)
        s.commit()
        return {"interesse": interesse.id, "sito": sito.id, "notizia": notizia.id}


def test_da_fuori_casa_le_azioni_solo_dal_pc_sono_rifiutate(client, remoto, fonti, monkeypatch):
    # Decisione 56: oltre a spegnimento, avvio, icone e Telegram, anche eliminare interessi e fonti.
    chiamate = []
    monkeypatch.setattr(avvio_sistema, "attiva_avvio", lambda radice: chiamate.append("avvio"))
    monkeypatch.setattr(avvio_sistema, "crea_icone", lambda radice: chiamate.append("icone"))

    async def verifica(token):
        chiamate.append("token")
        return "altro_bot"

    async def collega(token, chat):
        chiamate.append("collega")

    monkeypatch.setattr(telegram, "verifica_token", verifica)
    monkeypatch.setattr(telegram, "collega", collega)
    client.app.state.conf.telegram_token = "presente"
    with client.app.state.sessioni() as s:
        impostazioni.leggi(s).telegram_chat_id = 4242
        s.commit()

    rotte = [
        ("/impostazioni/avvio", {"attivo": "true"}),
        ("/impostazioni/avvio/icone", {"attivo": "true"}),
        ("/impostazioni/telegram/token", {"token": "123456:" + "A" * 35}),
        ("/impostazioni/telegram/conferma", {"chat_id": 999, "nome": "Estraneo"}),
        ("/impostazioni/telegram/cambia-chat", {}),
        (f"/impostazioni/interessi/{fonti['interesse']}/elimina", {}),
        ("/impostazioni/youtube/rimuovi", {"id": "UC" + "x" * 22}),
        (f"/impostazioni/siti/{fonti['sito']}/rimuovi", {}),
        ("/impostazioni/arxiv/categorie/rimuovi", {"codice": "cs.CR"}),
        ("/impostazioni/accesso", {"attivo": "true", "indirizzo": "https://altro.tail9999.ts.net"}),
    ]
    for rotta, dati in rotte:
        risposta = remoto.post(rotta, data=dati)
        assert risposta.status_code == 403, rotta
        assert SOLO_DAL_PC in risposta.text
    assert chiamate == []
    with client.app.state.sessioni() as s:
        assert impostazioni.leggi(s).telegram_chat_id == 4242
        assert interessi.elenca(s) and impostazioni.categorie_arxiv(s) and s.get(CanaleYoutube, "UC" + "x" * 22)
        assert s.get(Sito, fonti["sito"]) is not None
        assert impostazioni.leggi(s).indirizzo_remoto == NOME


def test_da_fuori_casa_il_cuore_si_mette_ma_non_si_toglie(client, remoto, fonti):
    # Togliere il cuore fa cancellare la notizia alla pulizia, che parte con ogni esecuzione (decisione 56).
    assert remoto.post(f"/notizie/{fonti['notizia']}/cuore").status_code == 403
    with client.app.state.sessioni() as s:
        assert s.get(Notizia, fonti["notizia"]).cuore
        s.get(Notizia, fonti["notizia"]).cuore = False
        s.commit()
    assert remoto.post(f"/notizie/{fonti['notizia']}/cuore").status_code == 200
    pagina = remoto.get(f"/notizie/{fonti['notizia']}").text
    assert 'aria-pressed="true"' in pagina and "disabled" in pagina.split('aria-pressed="true"')[0].rsplit("<button", 1)[1]
    assert "disabled" not in client.get(f"/notizie/{fonti['notizia']}").text.split('aria-pressed="true"')[0].rsplit("<button", 1)[1]


def test_da_fuori_casa_i_tetti_si_abbassano_ma_non_si_alzano(client, remoto, fonti):
    id = fonti["sito"]
    assert ALZARE_SOLO_DAL_PC in remoto.post("/impostazioni/arxiv/tetto", data={"tetto": 31}).text
    remoto.post("/impostazioni/arxiv/tetto", data={"tetto": 10})
    assert ALZARE_SOLO_DAL_PC in remoto.post(f"/impostazioni/siti/{id}/tetti", data={"pagine": 41, "articoli": 100}).text
    assert ALZARE_SOLO_DAL_PC in remoto.post(f"/impostazioni/siti/{id}/tetti", data={"pagine": 40, "articoli": 101}).text
    remoto.post(f"/impostazioni/siti/{id}/tetti", data={"pagine": 20, "articoli": 50})
    with client.app.state.sessioni() as s:
        impostazioni.leggi(s).finestra_giorni = 3
        s.commit()
    assert ALZARE_SOLO_DAL_PC in remoto.post("/impostazioni/esecuzione", data={"soglia": 70, "finestra_giorni": 4}).text
    remoto.post("/impostazioni/esecuzione", data={"soglia": 70, "finestra_giorni": 2})
    with client.app.state.sessioni() as s:
        imp = impostazioni.leggi(s)
        profilo = json.loads(s.get(Sito, id).profilo)
        assert (imp.tetto_arxiv, imp.finestra_giorni, imp.soglia) == (10, 2, 70)
        assert (profilo["pagine_massime"], profilo["articoli_massimi"]) == (20, 50)
    # Dal PC si alzano come prima.
    client.post("/impostazioni/arxiv/tetto", data={"tetto": 500}, headers=HTMX)
    with client.app.state.sessioni() as s:
        assert impostazioni.leggi(s).tetto_arxiv == 500


def test_da_fuori_casa_i_comandi_solo_dal_pc_sono_disattivati(client, remoto, fonti):
    client.app.state.conf.telegram_token = "presente"
    with client.app.state.sessioni() as s:
        imp = impostazioni.leggi(s)
        imp.telegram_chat_id, imp.telegram_chat_nome, imp.telegram_bot = 4242, "Io", "mio_bot"
        s.commit()
    for sezione in ("avvio", "telegram", "interessi", "canali-youtube", "siti", "arxiv", "accesso"):
        da_fuori, dal_pc = remoto.get(f"/impostazioni/{sezione}").text, client.get(f"/impostazioni/{sezione}", headers=HTMX).text
        assert SOLO_DAL_PC in da_fuori and " disabled" in da_fuori, sezione
        assert SOLO_DAL_PC not in dal_pc, sezione


def test_da_fuori_casa_l_icona_non_si_crea_alla_fine_della_configurazione(client_nuovo, monkeypatch):
    create = []
    monkeypatch.setattr(avvio_sistema, "crea_icone", lambda radice: create.append(radice))
    h = HTMX
    client_nuovo.post("/impostazioni/interessi", data={"nome": "AI", "descrizione": "Modelli"}, headers=h)
    client_nuovo.post("/impostazioni/arxiv/categorie", data={"codice": "cs.CR"}, headers=h)
    with client_nuovo.app.state.sessioni() as s:
        impostazioni.leggi(s).telegram_chat_id = 4242
        s.commit()
    client_nuovo.app.state.conf.telegram_token = "presente"
    remoto = da_fuori(client_nuovo.app)
    assert 'name="icone" value="true" disabled' in remoto.get("/configurazione?passo=telegram").text
    assert "stando al PC" in remoto.post("/configurazione/completa", data={"icone": "true"}).text
    assert not create
    assert remoto.post("/configurazione/completa").status_code == 204  # senza icona si completa


def test_feed_e_siti_della_rete_di_casa_non_si_aggiungono(client, fonti):
    # ADR 0013: con Serve chi è nella rete Tailscale farebbe leggere al PC i servizi della rete di casa.
    id = fonti["sito"]
    for indirizzo in ("http://192.168.1.1/feed", "http://127.1:8765/api/stato", "http://100.101.102.103/",
                      "http://localhost/feed"):
        finestra = client.post(f"/impostazioni/siti/{id}/feed", data={"indirizzo": indirizzo}, headers=HTMX).text
        assert "rete di casa" in finestra, indirizzo
        assert "Indirizzo non valido" in client.post("/impostazioni/siti", data={"indirizzo": indirizzo}, headers=HTMX).text
    with client.app.state.sessioni() as s:
        assert json.loads(s.get(Sito, id).profilo)["feed"] == []


def test_la_porta_per_serve_risponde_solo_con_l_accesso_attivo(client):
    porta = client.app.state.conf.porta_remota
    spento = cliente(client.app, NOME, porta, **IDENTITA).get("/")
    assert spento.status_code == 403 and "spento" in spento.text
    remoto = da_fuori(client.app)
    assert remoto.get("/").status_code == 200
    # Un Host locale scritto a mano non fa entrare dalla porta per Serve (rilettura di sicurezza, punto 1).
    assert cliente(client.app, "localhost", porta, **IDENTITA).get("/").status_code == 400
    # Funnel: traffico da internet, senza l'identità di Tailscale.
    funnel = cliente(client.app, NOME, porta).get("/")
    assert funnel.status_code == 403 and "Funnel" in funnel.text
    # Il nome Tailscale vale solo sulla porta per Serve; sulla principale restano i nomi del .env.
    assert cliente(client.app, NOME, client.app.state.conf.porta).get("/").status_code == 400
    # Spento dal PC: si rifiuta subito, senza riavvio, e il nome resta salvato per la volta dopo.
    client.post("/impostazioni/accesso", data={"indirizzo": f"https://{NOME}"}, headers=HTMX)
    assert remoto.get("/").status_code == 403
    assert f'value="https://{NOME}"' in client.get("/impostazioni/accesso", headers=HTMX).text


def test_l_accesso_resta_attivo_dopo_un_riavvio(client, conf):
    da_fuori(client.app)
    assert cliente(crea_app(conf), NOME, conf.porta_remota, **IDENTITA).get("/").status_code == 200


def test_sezione_accesso_da_fuori_casa(client):
    porta = client.app.state.conf.porta_remota
    pagina = client.get("/impostazioni/accesso", headers=HTMX).text
    assert "Accesso da fuori casa" in pagina and f"tailscale serve --bg {porta}" in pagina and "Spento" in pagina
    for sbagliato in ("*.tail1234.ts.net", "https://esempio.it", "pc.ts.net", f"https://{NOME}:8443",
                      f"https://{NOME}.esempio.it", "ftp://pc.tail1234.ts.net"):
        risposta = client.post("/impostazioni/accesso", data={"attivo": "true", "indirizzo": sbagliato}, headers=HTMX)
        assert "non è un indirizzo Tailscale" in risposta.text, sbagliato
    assert "Per attivare" in client.post("/impostazioni/accesso", data={"attivo": "true"}, headers=HTMX).text
    with client.app.state.sessioni() as s:
        assert not impostazioni.leggi(s).accesso_remoto and client.app.state.accesso_remoto is None
    attivo = client.post("/impostazioni/accesso", data={"attivo": "true", "indirizzo": " HTTPS://PC.Tail1234.ts.net/ "},
                         headers=HTMX).text
    assert f'href="https://{NOME}/"' in attivo
    with client.app.state.sessioni() as s:
        assert (impostazioni.leggi(s).accesso_remoto, impostazioni.leggi(s).indirizzo_remoto) == (True, NOME)
    client.app.state.porta_remota_aperta = False  # `esegui` non è riuscito ad aprirla
    assert "occupata" in client.get("/impostazioni/accesso", headers=HTMX).text
