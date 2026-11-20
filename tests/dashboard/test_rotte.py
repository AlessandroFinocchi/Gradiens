from datetime import timedelta

import pytest

from gradiens.app import avvio_sistema
from gradiens.dati import argomenti, esecuzioni, impostazioni, interessi, proposte
from gradiens.dati import siti as dati_siti
from gradiens.dati.modelli import Notizia, Pertinenza
from gradiens.dati.notizie import adesso
from gradiens.esecuzione.metriche import Avanzamento

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
            s.add(
                Notizia(
                    tipo=tipo,
                    url=url,
                    fonte="cs.CR" if tipo == "arxiv" else "Lab",
                    titolo=titolo,
                    titolo_it=None,
                    riassunto="Primo paragrafo.\nSecondo paragrafo.",
                    pubblicata_il=ora - timedelta(days=giorni),
                    scoperta_il=ora,
                    cuore=cuore,
                    pertinenze=[Pertinenza(interesse_id=sic.id, punteggio=punteggio)],
                )
            )
        s.commit()
    return client


def test_notizie_mostra_gli_ultimi_7_giorni_e_non_esegue_html(dati):
    pagina = dati.get("/notizie/arxiv").text
    assert "Paper &lt;script" in pagina and "Paper vecchio" not in pagina
    assert "<script>alert(1)</script>" not in pagina  # testo delle fonti: sempre escapato


def test_una_pagina_per_sorgente(dati):
    """Decisione 69: Siti web, YouTube e arXiv sono pagine diverse, sotto la sezione Notizie della sidebar."""
    arxiv, youtube = dati.get("/notizie/arxiv").text, dati.get("/notizie/youtube").text
    assert "Paper &lt;script" in arxiv and "Video sul ransomware" not in arxiv
    assert "Video sul ransomware" in youtube and "Paper &lt;script" not in youtube
    assert "Nessuna notizia negli ultimi 7 giorni" in dati.get("/notizie/siti").text
    assert 'href="/notizie/arxiv" aria-current="page"' in arxiv and "<span>Notizie</span>" in arxiv
    # Chip dei tipi solo dove la pagina ne ha più di uno: video e short su YouTube.
    assert 'name="tipo" value="short"' in youtube and 'name="tipo"' not in arxiv
    # Vecchio indirizzo: la pagina del primo tipo scelto, o i Siti web, con gli stessi filtri.
    vecchio = lambda q="": dati.get(f"/notizie{q}", follow_redirects=False).headers["location"]  # noqa: E731
    assert vecchio() == "/notizie/siti"
    assert vecchio("?tipo=short&tipo=arxiv&q=gta") == "/notizie/youtube?tipo=short&tipo=arxiv&q=gta"
    assert vecchio("?tipo=altro&cuore=1") == "/notizie/siti?tipo=altro&cuore=1"
    assert dati.get("/notizie/altro").status_code == 404


def test_filtri_dall_indirizzo(dati):
    pagina = dati.get("/notizie/youtube?tipo=video&ordine=data-asc").text
    assert "Video sul ransomware" in pagina and 'value="video" checked' in pagina
    assert "Nessuna notizia con questi filtri" in dati.get("/notizie/youtube?tipo=short").text
    assert "Video sul ransomware" in dati.get("/notizie/youtube?tipo=arxiv").text  # tipo di un'altra pagina: ignorato
    assert dati.get("/notizie/arxiv?interesse=abc&giorni=²&tipo=altro").status_code == 200  # parametri ignorati


def test_interessi_come_caselle_in_or(dati):
    with dati.app.state.sessioni() as s:
        sic, corsa = (next(i.id for i in interessi.elenca(s) if i.nome == nome) for nome in ("Sicurezza", "Corsa"))
    assert "Nessuna notizia con questi filtri" in dati.get(f"/notizie/arxiv?interesse={corsa}").text
    pagina = dati.get(f"/notizie/arxiv?interesse={corsa}&interesse={sic}&interesse=9999").text
    assert "Paper &lt;script" in pagina
    assert f'name="interesse" value="{sic}" checked' in pagina and f'name="interesse" value="{corsa}" checked' in pagina


def test_le_caselle_delle_fonti_mostrano_solo_le_fonti_della_pagina(dati):
    with dati.app.state.sessioni() as s:
        impostazioni.aggiungi_categoria(s, "cs.CR", "Crittografia e Sicurezza")
    arxiv = dati.get("/notizie/arxiv").text
    assert 'name="fonte" value="cs.CR"><span>Crittografia e Sicurezza</span>' in arxiv and 'value="Lab"' not in arxiv
    youtube = dati.get("/notizie/youtube").text
    assert 'name="fonte" value="Lab"><span>Lab</span>' in youtube and 'value="cs.CR"' not in youtube
    # Fonte di un'altra pagina: si ignora.
    assert "Video sul ransomware" in dati.get("/notizie/youtube?fonte=cs.CR").text
    # L'Archivio ha tutti i tipi: le fonti seguono i chip scelti (UI-06), e sono solo quelle con il cuore.
    assert 'value="cs.CR"' in dati.get("/archivio").text
    with dati.app.state.sessioni() as s:
        s.query(Notizia).filter_by(url="https://arxiv.org/abs/3").one().cuore = False
        s.commit()
    assert 'value="cs.CR"' not in dati.get("/archivio").text and 'value="cs.CR"' in dati.get("/notizie/arxiv").text
    solo_video = dati.get("/archivio?tipo=video&fonte=cs.CR&fonte=Lab").text
    assert 'value="cs.CR"' not in solo_video and 'name="fonte" value="Lab" checked' in solo_video
    # Il nome della categoria compare anche nelle schede e nella pagina della notizia, che torna alla sua pagina.
    assert "<span>Crittografia e Sicurezza</span>" in arxiv
    with dati.app.state.sessioni() as s:
        id = s.query(Notizia).filter_by(url="https://arxiv.org/abs/1").one().id
    notizia = dati.get(f"/notizie/{id}").text
    assert "<span>Crittografia e Sicurezza</span>" in notizia and 'class="indietro" href="/notizie/arxiv"' in notizia


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
    # Ogni interesse è compresso (solo il nome); descrizione e raffinamento si aprono dalla testa.
    assert finestra.count('<details class="interesse">') == 3 and "<summary" in finestra
    doppione = dati.post("/impostazioni/interessi", data={"nome": "LLM", "descrizione": "x"}, headers=HTMX).text
    assert "Esiste già un interesse" in doppione
    with dati.app.state.sessioni() as s:
        id = next(i.id for i in interessi.elenca(s) if i.nome == "LLM")
    dati.post(
        f"/impostazioni/interessi/{id}",
        data={"nome": "LLM e agenti", "descrizione": "modelli", "raffinamento": "soprattutto agenti"},
        headers=HTMX,
    )
    with dati.app.state.sessioni() as s:
        assert [i.raffinamento for i in interessi.elenca(s) if i.nome == "LLM e agenti"] == ["soprattutto agenti"]
    assert dati.post("/impostazioni/interessi/9999/elimina", headers=HTMX).status_code == 404


def test_segnali_nella_finestra_e_sull_ingranaggio(dati):
    # Nel fixture c'è solo una categoria arXiv: canali e siti vuoti vanno bene (decisione 56 dei requisiti),
    # manca il bot.
    pagina = dati.get("/notizie").text
    assert 'id="apri-impostazioni"' in pagina and "Bot Telegram non collegato" in pagina
    with dati.app.state.sessioni() as s:
        impostazioni.rimuovi_categoria(s, "cs.CR")  # nessuna fonte: avvertimento sulle tre sezioni delle fonti
    pagina = dati.get("/notizie").text
    assert "4 sezioni delle Impostazioni da guardare" in pagina
    finestra = dati.get("/impostazioni/canali-youtube", headers=HTMX).text
    assert finestra.count('title="Serve almeno una fonte: un canale YouTube, un sito o una categoria arXiv"') == 3
    assert 'class="campo-riga evidenziata"' in finestra  # la voce da sistemare
    assert 'hx-swap-oob="true"' in finestra  # l'ingranaggio si aggiorna con la finestra


def test_impostazioni_arxiv_ed_esecuzione(dati):
    assert (
        "non sembra una categoria"
        in dati.post("/impostazioni/arxiv/categorie", data={"codice": "<b>x</b>"}, headers=HTMX).text
    )
    assert "cs.AI" in dati.post("/impostazioni/arxiv/categorie", data={"codice": "cs.AI"}, headers=HTMX).text
    con_nome = dati.post(
        "/impostazioni/arxiv/categorie", data={"codice": "cs.IR", "nome": "Ricerca <i>"}, headers=HTMX
    ).text
    assert (
        '<div class="titolo"><code>cs.IR</code> · Ricerca &lt;i&gt;</div>' in con_nome
    )  # codice e nome sulla stessa riga
    righe = [con_nome.index(f'<div class="titolo"><code>{c}</code>') for c in ("cs.AI", "cs.CR", "cs.IR")]
    assert righe == sorted(righe)  # in ordine di codice, non di inserimento
    assert con_nome.index("Tetto di paper") < con_nome.index("Categorie seguite") < con_nome.index("<code>cs.IR</code>")
    assert (
        "va da 1 a 7"
        in dati.post("/impostazioni/esecuzione", data={"soglia": 60, "finestra_giorni": 9}, headers=HTMX).text
    )
    assert (
        "non è un orario valido"
        in dati.post(
            "/impostazioni/esecuzione", data={"soglia": 60, "finestra_giorni": 7, "orario": "25:00"}, headers=HTMX
        ).text
    )
    sezione = dati.get("/impostazioni/esecuzione", headers=HTMX).text
    assert 'name="automatica" value="true" checked' in sezione  # programmazione automatica accesa
    assert '<div class="riga solo-se-automatica">' in sezione  # l'orario sparisce quando la si spegne
    # Interruttore spento: la casella non viene inviata, ed è la pausa di /pausa (TG-10).
    dati.post("/impostazioni/esecuzione", data={"soglia": 75, "finestra_giorni": 3, "orario": "06:45"}, headers=HTMX)
    with dati.app.state.sessioni() as s:
        imp = impostazioni.leggi(s)
        assert (imp.soglia, imp.finestra_giorni) == (75, 3)
        assert (imp.orario_programmato, imp.programmazione_in_pausa) == ("06:45", True)
    assert dati.get("/api/stato").json()["prossima_esecuzione"] is None  # in pausa
    dati.post(
        "/impostazioni/esecuzione",
        data={"soglia": 75, "finestra_giorni": 3, "orario": "06:45", "automatica": "true"},
        headers=HTMX,
    )
    assert dati.get("/api/stato").json()["prossima_esecuzione"] is not None


def test_home_senza_esecuzioni(client):
    pagina = client.get("/").text
    assert "Prossima esecuzione programmata" in pagina and "Ancora nessuna esecuzione" in pagina
    assert "Nessun avviso." in pagina and "Nessuna notizia nelle ultime 24 ore." in pagina


def test_home_e_resoconto_di_un_esecuzione(dati):
    with dati.app.state.sessioni() as s:
        e = esecuzioni.inizia(s, "programmazione")
        esecuzioni.termina(
            s,
            e.id,
            "completata",
            {
                "durata_s": 192,
                "fonti": {
                    "siti": {
                        "raccolta_s": 48,
                        "esaminate": 215,
                        "scartate_prefiltro": 160,
                        "scartate_valutazione": 31,
                        "escluse": 1,
                        "senza_contenuto": 0,
                        "mostrate": 17,
                        "errori": 1,
                        "stati": [
                            {
                                "fonte": "rotto.it",
                                "stato": "accesso bloccato",
                                "dettaglio": "Il sito rifiuta le richieste.",
                                "nuove": 0,
                            },
                            {"fonte": "buono.it", "stato": "ok", "nuove": 12},
                        ],
                        "problemi": [],
                        "notizie_escluse": [
                            {
                                "fonte": "buono.it",
                                "titolo": "Sconto <b>40%</b>",
                                "url": "https://buono.it/x",
                                "motivo": "sponsorizzato o offerta",
                            }
                        ],
                    }
                },
                "token": {
                    "prefiltro": {"ingresso": 61400, "uscita": 4900, "provider": "claude-code", "modello": "haiku"},
                    "elaborazione": {
                        "ingresso": 142800,
                        "uscita": 21300,
                        "provider": "claude-code",
                        "modello": "haiku",
                    },
                },
            },
        )
        dati_siti.aggiungi(s, "https://rotto.it/", {"url": "https://rotto.it/"})
        dati_siti.registra_esito(s, dati_siti.elenca(s)[0].id, "accesso bloccato", "x", True)
        id = e.id
    home = dati.get("/").text
    assert "Ultima esecuzione" in home and f'href="/esecuzioni/{id}"' in home
    assert "3 min 12 s" in home and "230 mila" in home  # durata e token in breve
    assert "https://rotto.it/" in home  # avviso del sito in errore
    assert "Paper &lt;script" in home  # in evidenza: la notizia di ieri, escapata
    resoconto = dati.get(f"/esecuzioni/{id}").text
    assert "48 s" in resoconto and "Claude Code · haiku" in resoconto and "61.400" in resoconto
    assert resoconto.index("rotto.it") < resoconto.index("buono.it")  # prima i problemi
    assert "12 nuove" in resoconto and "Sconto &lt;b&gt;40%&lt;/b&gt;" in resoconto
    assert dati.get("/esecuzioni/9999").status_code == 404


def test_resoconto_di_un_esecuzione_registrata_prima_della_fetta_4b(client):
    with client.app.state.sessioni() as s:
        e = esecuzioni.inizia(s, "cli")
        esecuzioni.termina(
            s,
            e.id,
            "completata",
            {
                "durata_s": 5,
                "fonti": {
                    "arxiv": {
                        "esaminate": 3,
                        "scartate_prefiltro": 1,
                        "oltre_tetto": 0,
                        "senza_contenuto": 0,
                        "scartate_valutazione": 1,
                        "mostrate": 1,
                        "errori": 0,
                        "problemi": [{"fonte": "arXiv", "stato": "non raggiungibile: x"}],
                    }
                },
                "token": {"prefiltro": {"ingresso": 1, "uscita": 1}},
            },
        )
    resoconto = client.get(f"/esecuzioni/{e.id}")
    assert resoconto.status_code == 200 and "—" in resoconto.text and "non raggiungibile: x" in resoconto.text


def test_timeline_argomento_e_azioni(dati):
    with dati.app.state.sessioni() as s:
        a = argomenti.crea(s, "Attacco <b>ASL</b>")
        b = argomenti.crea(s, "Altro evento")
        for n in s.query(Notizia):
            n.argomento = a if n.tipo == "arxiv" else b
        s.commit()
        id_a, id_b = a.id, b.id
        id_notizia = s.query(Notizia).filter_by(url="https://arxiv.org/abs/1").one().id
    timeline = dati.get("/timeline").text
    assert "Attacco &lt;b&gt;ASL&lt;/b&gt;" in timeline
    assert f'href="/argomenti/{id_b}"' not in timeline  # 1 sola notizia: niente riga, ma resta destinazione dell'unione
    assert "2 notizie" in timeline and "1 in archivio" in timeline
    pagina = dati.get(f"/argomenti/{id_a}").text
    assert pagina.index("Paper &lt;script") < pagina.index("Paper vecchio")  # dalla più recente
    assert f'href="/argomenti/{id_a}"' in dati.get("/notizie/arxiv").text  # argomento sulla notizia (UI-04)
    assert "Apri la timeline" in dati.get(f"/notizie/{id_notizia}").text
    assert dati.get("/argomenti/9999").status_code == 404
    rinomina = dati.post(f"/argomenti/{id_a}/rinomina", data={"nome": "Attacco alla ASL"}, headers=HTMX)
    assert rinomina.status_code == 204 and rinomina.headers["HX-Refresh"] == "true"
    assert dati.post(f"/argomenti/{id_a}/rinomina", data={"nome": " "}, headers=HTMX).status_code == 422
    unione = dati.post(
        f"/argomenti/{id_b}/unisci",
        data={"destinazione": id_a},
        headers={**HTMX, "HX-Current-URL": f"http://127.0.0.1/argomenti/{id_b}"},
    )
    assert unione.headers["HX-Redirect"] == f"/argomenti/{id_a}"
    assert "3 notizie" in dati.get(f"/argomenti/{id_a}").text
    elimina = dati.post(f"/argomenti/{id_a}/elimina", headers={**HTMX, "HX-Current-URL": "http://127.0.0.1/timeline"})
    assert elimina.headers["HX-Refresh"] == "true" and "Ancora nessun argomento" in dati.get("/timeline").text


def test_proposta_di_raffinamento_nelle_impostazioni(dati):
    with dati.app.state.sessioni() as s:
        sic = next(i for i in interessi.elenca(s) if i.nome == "Sicurezza")
        sic.raffinamento = "Ransomware."
        s.commit()
        proposte.registra_raffinamento(s, sic, "Ransomware <b>nella</b> sanità.", 4)
        id = proposte.pendenti(s)[0].id
    finestra = dati.get("/impostazioni/interessi", headers=HTMX).text
    assert "Proposta di raffinamento, da 4 notizie con il cuore" in finestra
    assert "<mark>&lt;b&gt;nella&lt;/b&gt; sanità.</mark>" in finestra  # parole nuove evidenziate, testo escapato
    assert 'title="Sicurezza: proposta di raffinamento"' in finestra  # segnale sulla sezione
    assert "Proposta di raffinamento" in dati.get("/").text  # avviso nella Home
    approvata = dati.post(f"/impostazioni/proposte/{id}/approva", headers=HTMX).text
    assert "Proposta di raffinamento, da" not in approvata
    with dati.app.state.sessioni() as s:
        assert (
            next(i for i in interessi.elenca(s) if i.nome == "Sicurezza").raffinamento
            == "Ransomware <b>nella</b> sanità."
        )


def test_avanzamento_dell_esecuzione(dati):
    dati.app.state.esecutore.avanzamento = Avanzamento(esecuzione_id=1, fase="valutazione", fatti=3, totale=8)
    in_corso = dati.post("/esecuzione", headers=HTMX)  # già in corso: mostra l'avanzamento (ESE-02)
    assert "valutazione 3 di 8" in in_corso.text and 'hx-trigger="every 2s"' in in_corso.text
    dati.app.state.esecutore.avanzamento = None
    finita = dati.get("/esecuzione/avanzamento")
    assert "esecuzione-finita" in finita.headers["HX-Trigger"]
    assert "Avvia esecuzione" in finita.text


def test_impostazioni_canali_youtube(dati, monkeypatch):
    from gradiens.fonti import youtube

    async def risolvi(indirizzo):
        if "example" in indirizzo:
            raise ValueError("Non è un indirizzo di YouTube")
        return youtube.Canale(id="UC" + "x" * 22, nome="Lab <b>di</b> Sicurezza")

    monkeypatch.setattr(youtube, "risolvi_canale", risolvi)
    finestra = dati.post("/impostazioni/youtube", data={"indirizzo": "@lab"}, headers=HTMX).text
    assert "Lab &lt;b&gt;di&lt;/b&gt; Sicurezza" in finestra  # nome dal web: escapato
    assert (
        "Non è un indirizzo di YouTube"
        in dati.post("/impostazioni/youtube", data={"indirizzo": "https://example.org"}, headers=HTMX).text
    )
    assert (
        "Nessun canale" in dati.post("/impostazioni/youtube/rimuovi", data={"id": "UC" + "x" * 22}, headers=HTMX).text
    )


def test_impostazioni_siti(dati, monkeypatch):
    import json

    from gradiens.dati.modelli import Sito
    from gradiens.fonti import siti

    async def analizza(client, indirizzo):
        if "rotto" in indirizzo:
            raise ValueError("indirizzo non valido")
        return siti.Profilo(
            url="https://redhotcyber.com/",
            perimetro="redhotcyber.com",
            strategie=["feed"],
            siti_collegati={"esterno.example": False},
        )

    monkeypatch.setattr(siti, "analizza", analizza)
    finestra = dati.post("/impostazioni/siti", data={"indirizzo": "redhotcyber.com"}, headers=HTMX).text
    assert "redhotcyber.com" in finestra and "mai raccolto" in finestra
    # Sito nuovo con un sito collegato da attivare: è una novità, e la riga dice perché è evidenziata.
    assert '<div class="riga proposta"' in finestra and "evidenziata" not in finestra.split("Siti seguiti")[1]
    assert "L'analisi ha trovato un sito collegato: esterno.example" in finestra
    assert (
        "già tra quelli seguiti"
        in dati.post("/impostazioni/siti", data={"indirizzo": "redhotcyber.com"}, headers=HTMX).text
    )
    assert "Indirizzo non valido" in dati.post("/impostazioni/siti", data={"indirizzo": "rotto"}, headers=HTMX).text

    with dati.app.state.sessioni() as s:
        id = s.query(Sito).one().id
    assert (
        "Serve un indirizzo completo"
        in dati.post(f"/impostazioni/siti/{id}/feed", data={"indirizzo": "javascript:alert(1)"}, headers=HTMX).text
    )
    dati.post(f"/impostazioni/siti/{id}/feed", data={"indirizzo": "https://redhotcyber.com/feed/gn"}, headers=HTMX)
    dati.post(f"/impostazioni/siti/{id}/collegato", data={"dominio": "esterno.example", "attivo": "true"}, headers=HTMX)
    with dati.app.state.sessioni() as s:
        profilo = json.loads(s.get(Sito, id).profilo)
    assert profilo["feed"] == ["https://redhotcyber.com/feed/gn"]
    assert profilo["siti_collegati"] == {"esterno.example": True}
    assert set(profilo["modificati"]) == {"feed", "siti_collegati"}  # conservati dalla rigenerazione (WEB-25)
    assert "Nessun sito" in dati.post(f"/impostazioni/siti/{id}/rimuovi", headers=HTMX).text


def test_tetti_del_sito_e_interruttori_di_esclusione(dati, monkeypatch):
    import json

    from gradiens.dati import siti as dati_siti
    from gradiens.dati.modelli import Sito
    from gradiens.fonti import siti

    with dati.app.state.sessioni() as s:
        id = dati_siti.aggiungi(s, "https://hwupgrade.it/", siti.Profilo(url="https://hwupgrade.it/").come_dict()).id
    assert (
        "da 1 a 500"
        in dati.post(f"/impostazioni/siti/{id}/tetti", data={"pagine": 0, "articoli": 10}, headers=HTMX).text
    )
    dati.post(f"/impostazioni/siti/{id}/tetti", data={"pagine": 120, "articoli": 400}, headers=HTMX)
    dati.post(
        "/impostazioni/esecuzione",
        data={"soglia": 60, "finestra_giorni": 7, "escludi_sponsorizzati": "true"},
        headers=HTMX,
    )
    with dati.app.state.sessioni() as s:
        profilo = json.loads(s.get(Sito, id).profilo)
        imp = impostazioni.leggi(s)
    assert (profilo["pagine_massime"], profilo["articoli_massimi"]) == (120, 400)
    assert {"pagine_massime", "articoli_massimi"} <= set(profilo["modificati"])
    assert (imp.escludi_sponsorizzati, imp.escludi_pagamento) == (True, False)  # casella non spuntata = disattivo


def test_rigenera_dal_bottone_e_togli_esclusione(dati, monkeypatch):
    import json

    from gradiens.dati import siti as dati_siti
    from gradiens.dati.modelli import Sito
    from gradiens.fonti import siti

    vecchio = siti.Profilo(url="https://sito.it/", strategie=["feed"], esclusi=["https://sito.it/en/"]).come_dict()
    with dati.app.state.sessioni() as s:
        id = dati_siti.aggiungi(s, "https://sito.it/", vecchio, "ok").id

    async def non_trova_niente(client, profilo):
        return None

    monkeypatch.setattr(siti, "rigenera", non_trova_niente)
    finestra = dati.post(f"/impostazioni/siti/{id}/rigenera", headers=HTMX).text
    assert "tengo il profilo di prima" in finestra  # decisione 21, anche dal bottone
    with dati.app.state.sessioni() as s:
        sito = s.get(Sito, id)
        assert (json.loads(sito.profilo), sito.profilo_precedente, sito.stato) == (vecchio, None, "ok")

    async def trova(client, profilo):
        return siti.Profilo(url=profilo.url, strategie=["sitemap"])

    monkeypatch.setattr(siti, "rigenera", trova)
    dati.post(f"/impostazioni/siti/{id}/rigenera", headers=HTMX)
    with dati.app.state.sessioni() as s:
        sito = s.get(Sito, id)
        assert (json.loads(sito.profilo)["strategie"], sito.stato) == (["sitemap"], "profilo rigenerato")

    with dati.app.state.sessioni() as s:
        dati_siti.salva_profilo(s, id, vecchio)
    finestra = dati.post(
        f"/impostazioni/siti/{id}/includi", data={"indirizzo": "https://sito.it/en/"}, headers=HTMX
    ).text
    assert "nessuno" in finestra.split("<dt>Esclusi</dt>")[1].split("</dd>")[0]
    with dati.app.state.sessioni() as s:
        profilo = json.loads(s.get(Sito, id).profilo)
    assert (profilo["esclusi"], profilo["modificati"]) == ([], ["esclusi"])


def test_aiuto_dell_llm_al_profilo_mostra_le_differenze_e_applica_le_scelte(dati, monkeypatch):
    """ADR 0012: la dashboard chiama il modulo del backend, mai il provider; l'utente approva le proposte."""
    import json

    from gradiens.dati.modelli import Sito
    from gradiens.esecuzione import aiuto_profilo
    from gradiens.fonti import siti
    from gradiens.fonti.siti.aiuto import Proposta

    vecchio = siti.Profilo(
        url="https://sito.it/", perimetro="sito.it", strategie=["feed"], sezioni=["https://sito.it/eventi/"]
    ).come_dict()
    with dati.app.state.sessioni() as s:
        id = dati_siti.aggiungi(s, "https://sito.it/", vecchio, "ok").id
    assert (
        "https://sito.it/eventi/" in dati.get("/impostazioni/siti").text.split("<dt>Sezioni</dt>")[1].split("</dd>")[0]
    )

    risposte = []

    async def aiuta(s, client, profilo):
        risposta = risposte.pop(0)
        if isinstance(risposta, Exception):
            raise risposta
        return risposta

    monkeypatch.setattr(aiuto_profilo, "aiuta", aiuta)
    proposta = Proposta(
        ["https://sito.it/notizie/"],
        ["https://sito.it/eventi/"],
        ["https://sito.it/offerte/"],
        "Gli <b>eventi</b> non sono notizie.",
    )
    risposte.append(aiuto_profilo.Aiuto(proposta, 4321, 2))
    finestra = dati.post(f"/impostazioni/siti/{id}/aiuto", headers=HTMX).text
    assert "Gli &lt;b&gt;eventi&lt;/b&gt; non sono notizie." in finestra  # testo dell'LLM: escapato
    assert 'name="aggiungi" value="https://sito.it/notizie/" checked' in finestra
    # Togliere una sezione si rifà solo con un'altra richiesta all'LLM: la casella parte senza spunta.
    assert 'name="togli" value="https://sito.it/eventi/">' in finestra
    assert 'name="escludi" value="https://sito.it/offerte/" checked' in finestra
    assert "4.321 token" in finestra and "oltre il tetto" not in finestra
    assert "2 gruppi di link" in finestra  # lasciati fuori per stare nel tetto
    with dati.app.state.sessioni() as s:
        assert json.loads(s.get(Sito, id).profilo) == vecchio  # niente cambia prima di "Applica"

    dati.post(
        f"/impostazioni/siti/{id}/aiuto/applica",
        headers=HTMX,
        data={
            "aggiungi": ["https://sito.it/notizie/"],
            "togli": ["https://sito.it/eventi/"],
            "escludi": ["https://sito.it/offerte/"],
        },
    )
    with dati.app.state.sessioni() as s:
        profilo = json.loads(s.get(Sito, id).profilo)
    assert (profilo["sezioni"], profilo["esclusi"]) == (["https://sito.it/notizie/"], ["https://sito.it/offerte/"])
    assert set(profilo["modificati"]) == {"sezioni", "esclusi"}  # restano dopo una rigenerazione (WEB-25)
    assert "html" in profilo["strategie"]  # una sezione rende attiva la strategia che la usa

    errore = dati.post(
        f"/impostazioni/siti/{id}/aiuto/applica", headers=HTMX, data={"aggiungi": ["https://altro.example/x/"]}
    ).text
    assert "fuori dal sito" in errore

    risposte.append(aiuto_profilo.Aiuto(Proposta([], [], []), 10_500, 0))
    finestra = dati.post(f"/impostazioni/siti/{id}/aiuto", headers=HTMX).text
    assert "non propone modifiche" in finestra and "oltre il tetto" in finestra and "Applica" not in finestra

    risposte.append(aiuto_profilo.AiutoNonDisponibile("Quota esaurita."))
    assert "https://sito.it/: Quota esaurita." in dati.post(f"/impostazioni/siti/{id}/aiuto", headers=HTMX).text
    assert dati.post("/impostazioni/siti/999/aiuto", headers=HTMX).status_code == 404


def test_impostazioni_avvio(client, monkeypatch):
    registrato = []

    def attiva(radice):
        registrato.append(radice)
        monkeypatch.setattr(avvio_sistema, "_cache", (float("inf"), avvio_sistema.StatoAvvio(True)))

    monkeypatch.setattr(avvio_sistema, "attiva_avvio", attiva)
    monkeypatch.setattr(avvio_sistema, "disattiva_avvio", lambda radice: registrato.clear())
    assert "Avvio a mano" in client.get("/impostazioni/avvio").text
    pagina = client.post("/impostazioni/avvio", data={"attivo": "true"}, headers=HTMX).text
    assert registrato and "accensione registrato" in pagina and "checked" in pagina
    pagina = client.post("/impostazioni/avvio", headers=HTMX).text  # interruttore spento: nessun campo
    assert not registrato and "si avvia a mano" in pagina

    def negato(radice):
        raise avvio_sistema.ErroreAvvio("La conferma di amministratore è stata negata.", "Register-ScheduledTask …")

    monkeypatch.setattr(avvio_sistema, "attiva_avvio", negato)
    pagina = client.post("/impostazioni/avvio", data={"attivo": "true"}, headers=HTMX).text
    assert "negata" in pagina and '<pre class="comando">Register-ScheduledTask …</pre>' in pagina


def test_segnale_dell_avvio_da_rifare(client, monkeypatch):
    stato = avvio_sistema.StatoAvvio(True, "Il servizio non è abilitato.", "sudo loginctl enable-linger io")
    monkeypatch.setattr(avvio_sistema, "_cache", (float("inf"), stato))
    pagina = client.get("/impostazioni/avvio").text
    assert "Il servizio non è abilitato." in pagina and "sudo loginctl enable-linger io" in pagina
    assert "evidenziata" in pagina


def test_aiuto(client):
    pagina = client.get("/aiuto").text
    for sezione in (
        "esecuzione",
        "fonti",
        "siti",
        "interessi",
        "cuore",
        "argomenti",
        "stati",
        "impostazioni-e-segnali",
        "avvio",
        "fuori-casa",
        "cli",
        "telegram",
    ):
        assert f'id="{sezione}"' in pagina and f'href="#{sezione}"' in pagina  # UI-12, con l'indice
    # Un solo #impostazioni, la finestra: un titolo con lo stesso id riceveva le Impostazioni al posto del <dialog>.
    assert pagina.count('id="impostazioni"') == 1
    assert f"tailscale serve --bg {client.app.state.conf.porta_remota}" in pagina  # ADR 0013, con la porta vera
    assert "<code>/riprendi</code>" in pagina and "Windows" in pagina and "Linux" in pagina
    assert 'aria-current="page"' in pagina.split("Aiuto</span>")[0].rsplit("<a", 1)[1]  # voce attiva nella sidebar


def test_il_simbolo_di_gradiens_fissa_e_sblocca_la_sidebar(client):
    """UI-01, decisione 68: lo stato vale per tutte le pagine, quindi sta nel database e non nella pagina."""
    assert "data-sidebar-fissa" not in client.get("/").text
    risposta = client.post("/sidebar", headers=HTMX)
    assert risposta.status_code == 204 and risposta.headers["HX-Trigger"] == '{"sidebar-cambiata": true}'
    pagina = client.get("/notizie").text
    assert "data-sidebar-fissa" in pagina and 'aria-pressed="true"' in pagina
    assert client.post("/sidebar", headers=HTMX).headers["HX-Trigger"] == '{"sidebar-cambiata": false}'
    assert "data-sidebar-fissa" not in client.get("/aiuto").text


def test_interruttore_dell_icona_del_pannello(client, monkeypatch):
    create = []
    monkeypatch.setattr(avvio_sistema, "crea_icone", lambda radice: create.append(radice))
    monkeypatch.setattr(avvio_sistema, "togli_icone", lambda: create.clear())
    assert "Icona Gradiens sul desktop e nel menu" in client.get("/impostazioni/avvio", headers=HTMX).text
    assert (
        "Icona Gradiens creata" in client.post("/impostazioni/avvio/icone", data={"attivo": "true"}, headers=HTMX).text
    )
    assert create
    assert "Icona Gradiens tolta" in client.post("/impostazioni/avvio/icone", headers=HTMX).text and not create


def test_i_file_statici_hanno_la_versione_nell_indirizzo(client):
    # Senza, dopo un aggiornamento il browser usava il vecchio stile.css dalla cache.
    pagina = client.get("/").text
    for nome in ("stile.css", "app.js", "htmx.min.js", "gradiens.png"):
        assert f"/static/{nome}?v=" in pagina
    indirizzo = pagina.split('<link rel="stylesheet" href="')[1].split('"')[0]
    assert client.get(indirizzo).status_code == 200


def test_avviso_del_login_di_claude_code_nella_home(client, monkeypatch):
    from gradiens.dashboard import rotte

    assert "Login di Claude Code" not in client.get("/").text
    monkeypatch.setattr(rotte.claude_code, "avviso_login", lambda: "Il login di Claude Code scade il 10/11 alle 04:23")
    assert "Il login di Claude Code scade il 10/11 alle 04:23" in client.get("/").text


def test_cambio_di_versione_di_claude_code_nella_home(client):
    versione = {"provider": "claude-code", "versione": "2.1.316", "precedente": None, "provata": True}
    with client.app.state.sessioni() as s:
        e = esecuzioni.inizia(s, "cli")
        esecuzioni.termina(s, e.id, "completata", {"versione_llm": versione})
    assert "Claude Code è passato" not in client.get("/").text
    with client.app.state.sessioni() as s:
        e = esecuzioni.inizia(s, "cli")
        esecuzioni.termina(
            s, e.id, "completata", {"versione_llm": {**versione, "versione": "2.1.325", "precedente": "2.1.316"}}
        )
    assert "Claude Code è passato dalla versione 2.1.316 alla 2.1.325" in client.get("/").text


def test_ricerca_nella_pagina_notizie(dati):
    pagina = dati.get("/notizie/arxiv", params={"q": "parola-che-non-esiste"}).text
    assert 'id="cerca"' in pagina and 'value="parola-che-non-esiste"' in pagina
    assert "Nessuna notizia contiene tutte le parole cercate" in pagina


def test_righe_compatte_delle_fonti(dati, monkeypatch):
    from gradiens.dati import impostazioni as imp
    from gradiens.dati import siti as dati_siti

    with dati.app.state.sessioni() as s:
        imp.aggiungi_canale(s, "UC123", "Lab di Sicurezza")
        id = dati_siti.aggiungi(s, "https://e.org/", {"url": "https://e.org/", "perimetro": "e.org"}, None).id
        dati_siti.registra_esito(s, id, "accesso bloccato", "Il sito rifiuta le richieste.", True)
    canali = dati.get("/impostazioni/canali-youtube", headers=HTMX).text
    assert (
        '<div class="titolo"><a href="https://www.youtube.com/channel/UC123"' in canali
        and ">Lab di Sicurezza</a>" in canali
    )
    assert "youtube.com/channel/UC123</a>" not in canali  # niente più link sotto il nome
    siti = dati.get("/impostazioni/siti", headers=HTMX).text.split("Siti seguiti")[1]
    assert 'class="riga evidenziata"' in siti  # il problema si vede dallo sfondo della riga
    riga, menu = siti.split("<details", 1)
    assert "accesso bloccato" not in riga and "accesso bloccato" in menu  # lo stato è nel menu
