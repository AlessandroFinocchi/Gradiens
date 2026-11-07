"""Configurazione iniziale guidata (UI-11, decisioni 55 e 56)."""

from gradiens.dashboard import rotte_configurazione
from gradiens.dati import impostazioni
from gradiens.llm.base import ErroreLLM

# Le richieste htmx dalla pagina della procedura: i moduli delle Impostazioni rispondono con il passo.
DALLA_PROCEDURA = {"HX-Request": "true", "HX-Current-URL": "http://127.0.0.1/configurazione?passo=interessi"}


def test_un_gradiens_nuovo_porta_alla_configurazione(client_nuovo):
    for percorso in ["/", "/notizie", "/aiuto"]:
        risposta = client_nuovo.get(percorso)
        assert risposta.url.path == "/configurazione" and "Benvenuto in Gradiens" in risposta.text
        assert 'aria-label="Pagine"' not in risposta.text  # niente sidebar: la dashboard non si usa ancora
    assert "<button class=\"bottone\" disabled>Avanti</button>" in client_nuovo.get("/configurazione").text


def test_i_passi_usano_i_moduli_delle_impostazioni(client_nuovo):
    passo = client_nuovo.post("/impostazioni/interessi", data={"nome": "AI", "descrizione": "Modelli"},
                              headers=DALLA_PROCEDURA).text
    assert "Benvenuto in Gradiens" in passo and "finestra-testata" not in passo  # il passo, non la finestra
    assert 'href="/configurazione?passo=fonti">Avanti' in passo

    passo = client_nuovo.post("/impostazioni/arxiv/categorie", data={"codice": "cs.CR"}, headers=DALLA_PROCEDURA).text
    assert 'href="/configurazione?passo=claude">Avanti' in passo  # basta una fonte qualsiasi (decisione 56)


def test_passo_di_claude_code(client_nuovo, monkeypatch):
    assert "abbonamento Pro" in client_nuovo.get("/configurazione?passo=claude").text

    def scollegato():
        raise ErroreLLM("Claude Code non è collegato a un account.")

    monkeypatch.setattr(rotte_configurazione, "stato_account", scollegato)
    pagina = client_nuovo.get("/configurazione?passo=claude").text
    assert "non è collegato" in pagina and "claude setup-token" in pagina


def test_completare_sblocca_la_dashboard_e_non_torna_piu(client_nuovo):
    h = {"HX-Request": "true"}
    assert "Aggiungi almeno un interesse" in client_nuovo.post("/configurazione/completa", headers=h).text
    client_nuovo.post("/impostazioni/interessi", data={"nome": "AI", "descrizione": "Modelli"}, headers=h)
    client_nuovo.post("/impostazioni/arxiv/categorie", data={"codice": "cs.CR"}, headers=h)
    with client_nuovo.app.state.sessioni() as s:
        impostazioni.leggi(s).telegram_chat_id = 4242
        s.commit()
    client_nuovo.app.state.conf.telegram_token = "presente"

    risposta = client_nuovo.post("/configurazione/completa", headers=h)
    assert risposta.status_code == 204 and risposta.headers["HX-Redirect"] == "/"
    assert 'aria-label="Pagine"' in client_nuovo.get("/").text
    assert client_nuovo.get("/configurazione").url.path == "/"
    # Decisione 55: un dato tolto dopo si vede solo come segnale, la dashboard resta usabile.
    client_nuovo.post("/impostazioni/arxiv/categorie/rimuovi", data={"codice": "cs.CR"}, headers=h)
    pagina = client_nuovo.get("/notizie")
    assert pagina.url.path == "/notizie" and "3 sezioni delle Impostazioni da guardare" in pagina.text
