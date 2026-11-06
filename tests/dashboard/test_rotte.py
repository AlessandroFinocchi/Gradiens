from datetime import timedelta

import pytest

from gradiens.dati import impostazioni, interessi
from gradiens.dati.modelli import Notizia, Pertinenza
from gradiens.dati.notizie import adesso
from gradiens.esecuzione.esecutore import Avanzamento

HTMX = {"HX-Request": "true"}


@pytest.fixture
def dati(client):
    """Due interessi, una categoria e tre notizie, di cui una con il cuore e una vecchia."""
    with client.app.state.sessioni() as s:
        sic = interessi.aggiungi(s, "Sicurezza", "attacchi")
        interessi.aggiungi(s, "Corsa", "allenamento")
        impostazioni.aggiungi_categoria(s, "cs.CR")
        ora = adesso()
        for url, tipo, punteggio, giorni, cuore, titolo in [
            ("https://arxiv.org/abs/1", "arxiv", 90, 1, False, "Paper <script>alert(1)</script>"),
            ("https://example.org/2", "video", 70, 2, True, "Video sul ransomware"),
            ("https://arxiv.org/abs/3", "arxiv", 95, 30, True, "Paper vecchio con il cuore"),
        ]:
            s.add(Notizia(tipo=tipo, url=url, fonte="cs.CR" if tipo == "arxiv" else "Lab", titolo=titolo,
                          titolo_it=None, riassunto="Primo paragrafo.\nSecondo paragrafo.",
                          pubblicata_il=ora - timedelta(days=giorni), scoperta_il=ora, cuore=cuore,
                          pertinenze=[Pertinenza(interesse_id=sic.id, punteggio=punteggio)]))
        s.commit()
    return client


def test_notizie_mostra_gli_ultimi_7_giorni_e_non_esegue_html(dati):
    pagina = dati.get("/notizie").text
    assert "Video sul ransomware" in pagina and "Paper vecchio" not in pagina
    assert "<script>alert(1)</script>" not in pagina  # testo delle fonti: sempre escapato
    assert "&lt;script&gt;" in pagina


def test_filtri_dall_indirizzo(dati):
    pagina = dati.get("/notizie?tipo=video&ordine=data-asc").text
    assert "Video sul ransomware" in pagina and "Paper &lt;script" not in pagina
    assert 'value="video" checked' in pagina
    assert "Nessuna notizia con questi filtri" in dati.get("/notizie?fonte=inesistente").text
    assert dati.get("/notizie?interesse=abc&giorni=²&tipo=altro").status_code == 200  # parametri ignorati


def test_archivio_tiene_anche_le_vecchie(dati):
    pagina = dati.get("/archivio").text
    assert "Paper vecchio con il cuore" in pagina and "Video sul ransomware" in pagina
    assert "Paper &lt;script" not in pagina


def test_notizia_specifica_e_cuore(dati):
    with dati.app.state.sessioni() as s:
        id = s.query(Notizia).filter_by(url="https://arxiv.org/abs/1").one().id
    pagina = dati.get(f"/notizie/{id}").text
    assert "<p>Primo paragrafo.</p><p>Secondo paragrafo.</p>" in pagina
    assert "Leggi l'originale" in pagina and 'rel="noopener noreferrer"' in pagina
    assert "Non pertinente agli altri interessi." in pagina
    bottone = dati.post(f"/notizie/{id}/cuore?testo=1", headers=HTMX).text
    assert 'aria-pressed="true"' in bottone and "Ha il cuore" in bottone
    assert dati.get("/notizie/9999").status_code == 404
    assert dati.post("/notizie/9999/cuore", headers=HTMX).status_code == 404


def test_impostazioni_interessi(dati):
    finestra = dati.post("/impostazioni/interessi", data={"nome": "LLM", "descrizione": "modelli"}, headers=HTMX).text
    assert 'value="LLM"' in finestra
    doppione = dati.post("/impostazioni/interessi", data={"nome": "LLM", "descrizione": "x"}, headers=HTMX).text
    assert "Esiste già un interesse" in doppione
    with dati.app.state.sessioni() as s:
        id = next(i.id for i in interessi.elenca(s) if i.nome == "LLM")
    dati.post(f"/impostazioni/interessi/{id}", data={"nome": "LLM e agenti", "descrizione": "modelli",
                                                      "raffinamento": "soprattutto agenti"}, headers=HTMX)
    with dati.app.state.sessioni() as s:
        assert [i.raffinamento for i in interessi.elenca(s) if i.nome == "LLM e agenti"] == ["soprattutto agenti"]
    assert dati.post("/impostazioni/interessi/9999/elimina", headers=HTMX).status_code == 404


def test_impostazioni_arxiv_ed_esecuzione(dati):
    assert "almeno una categoria" in dati.post("/impostazioni/arxiv/categorie/rimuovi", data={"codice": "cs.CR"}, headers=HTMX).text
    assert "non sembra una categoria" in dati.post("/impostazioni/arxiv/categorie", data={"codice": "<b>x</b>"}, headers=HTMX).text
    assert "cs.AI" in dati.post("/impostazioni/arxiv/categorie", data={"codice": "cs.AI"}, headers=HTMX).text
    assert "va da 1 a 7" in dati.post("/impostazioni/esecuzione", data={"soglia": 60, "finestra_giorni": 9}, headers=HTMX).text
    dati.post("/impostazioni/esecuzione", data={"soglia": 75, "finestra_giorni": 3}, headers=HTMX)
    with dati.app.state.sessioni() as s:
        imp = impostazioni.leggi(s)
        assert (imp.soglia, imp.finestra_giorni) == (75, 3)


def test_avanzamento_dell_esecuzione(dati):
    dati.app.state.esecutore.avanzamento = Avanzamento(esecuzione_id=1, fase="valutazione", fatti=3, totale=8)
    in_corso = dati.post("/esecuzione", headers=HTMX)  # già in corso: mostra l'avanzamento (ESE-02)
    assert "valutazione 3 di 8" in in_corso.text and 'hx-trigger="every 2s"' in in_corso.text
    dati.app.state.esecutore.avanzamento = None
    finita = dati.get("/esecuzione/avanzamento")
    assert "esecuzione-finita" in finita.headers["HX-Trigger"]
    assert "Avvia esecuzione" in finita.text
