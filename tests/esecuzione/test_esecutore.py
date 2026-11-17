import asyncio
import json
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from gradiens.dati import impostazioni, interessi, notizie
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.dati.modelli import Argomento, CategoriaArxiv, Esecuzione, Notizia, Pertinenza, Proposta
from gradiens.esecuzione import prompt
from gradiens.esecuzione.esecutore import Esecutore, GiaInCorso
from gradiens.fonti import Candidata
from gradiens.llm.base import ErroreLLM, LoginRifiutato, QuotaEsaurita
from gradiens.llm.finto import Finto


@pytest.fixture
def sessioni(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    fabbrica = fabbrica_sessioni(motore)
    with fabbrica() as s:
        interessi.aggiungi(s, "Sicurezza", "attacchi informatici")
        impostazioni.aggiungi_categoria(s, "cs.CR")
    return fabbrica


def candidata(nome: str, ore_fa: int = 1) -> Candidata:
    return Candidata(tipo="arxiv", url=f"https://arxiv.org/abs/{nome}", fonte="cs.CR", titolo=nome,
                     sommario=f"sommario {nome}", contenuto=f"abstract {nome}",
                     pubblicata_il=notizie.adesso() - timedelta(hours=ore_fa))


def raccolta(*candidate):
    """Fonte arXiv finta, nel formato che l'esecutore si aspetta (modulo con `raccogli`)."""
    async def raccogli(client, categorie, dal):
        assert categorie == ["cs.CR"]
        return list(candidate)
    return {"arxiv": SimpleNamespace(raccogli=raccogli)}


def risponditore(sistema, messaggio, schema):
    """Pre-filtro: passano i titoli con "sicurezza", "offerta" è sponsorizzata se l'esclusione è attiva.
    Valutazione: "alta" 90, altrimenti 30."""
    if schema is prompt.SCHEMA_PREFILTRO:
        voci = json.loads(messaggio)
        sponsorizzate = [v["id"] for v in voci if "offerta" in v["titolo"]] if "sponsorizzati" in sistema else []
        return {"pertinenti": [v["id"] for v in voci if "sicurezza" in v["titolo"]], "sponsorizzate": sponsorizzate}
    if schema is prompt.SCHEMA_ARGOMENTI:  # le notizie "attacco" vanno in un argomento solo
        return {"assegnazioni": [{"notizia": v["id"], "nuovo": "Attacco alla ASL"} for v in json.loads(messaggio)
                                 if "attacco" in v["titolo"]]}
    titolo = json.loads(messaggio)["titolo"]
    return {"punteggi": [{"interesse": 1, "pertinenza": 90 if "alta" in titolo else 30}],
            "riassunto": f"Riassunto di {titolo}.", "titolo_it": f"IT {titolo}"}


def esegui(sessioni, raccogli, provider=None, **imp):
    finto = provider or Finto(risponditore)
    with sessioni() as s:
        valori = impostazioni.leggi(s)
        for chiave, valore in imp.items():
            setattr(valori, chiave, valore)
        s.commit()

    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda nome: finto, fonti=raccogli)
        esecutore.avvia("cli")
        await esecutore.attendi()

    asyncio.run(prova())
    with sessioni() as s:
        esecuzione = s.scalars(select(Esecuzione)).one()
        return esecuzione, json.loads(esecuzione.metriche), list(s.scalars(select(Notizia).options(selectinload(Notizia.pertinenze)))), finto


def test_esecuzione_completa(sessioni):
    with sessioni() as s:
        notizie.segna_viste(s, ["https://arxiv.org/abs/sicurezza-vista"])
        s.commit()
    esecuzione, metriche, salvate, finto = esegui(sessioni, raccolta(
        candidata("sicurezza-alta"), candidata("sicurezza-bassa"), candidata("cucina"), candidata("sicurezza-vista")))

    assert esecuzione.stato == "completata"
    assert [n.titolo for n in salvate] == ["sicurezza-alta"]
    assert salvate[0].titolo_it == "IT sicurezza-alta"
    assert salvate[0].pertinenze[0].punteggio == 90
    a = metriche["fonti"]["arxiv"]
    assert (a["esaminate"], a["scartate_prefiltro"], a["scartate_valutazione"], a["mostrate"]) == (3, 1, 1, 1)
    assert metriche["token"]["prefiltro"]["ingresso"] > 0
    with sessioni() as s:  # tutte le notizie esaminate sono ora nel registro (ESE-07)
        assert len(notizie.gia_viste(s, [f"https://arxiv.org/abs/{n}" for n in ("sicurezza-alta", "sicurezza-bassa", "cucina")])) == 3
    # Pre-filtro: una sola chiamata a blocchi. La parte fissa (interessi) sta nel prompt di sistema.
    assert sum("pre-filtro" in sistema for sistema, _ in finto.chiamate) == 1
    assert all("attacchi informatici" in sistema for sistema, _ in finto.chiamate if "passo degli argomenti" not in sistema)


def test_tetto_arxiv_elabora_solo_i_piu_recenti(sessioni):
    _, metriche, salvate, _ = esegui(sessioni, raccolta(
        candidata("sicurezza-alta-vecchia", ore_fa=5), candidata("sicurezza-alta-recente", ore_fa=1)), tetto_arxiv=1)
    assert [n.titolo for n in salvate] == ["sicurezza-alta-recente"]
    assert metriche["fonti"]["arxiv"]["oltre_tetto"] == 1


def test_quota_esaurita_interrompe_e_lascia_le_notizie_per_la_prossima(sessioni):
    def senza_quota(sistema, messaggio, schema):
        if schema is prompt.SCHEMA_VALUTAZIONE:
            raise QuotaEsaurita("Quota dell'abbonamento esaurita")
        return risponditore(sistema, messaggio, schema)

    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")), provider=Finto(senza_quota))
    assert esecuzione.stato == "interrotta"
    assert "Quota" in esecuzione.motivo
    assert salvate == []
    with sessioni() as s:  # non segnata come vista: verrà valutata alla prossima esecuzione
        assert notizie.gia_viste(s, ["https://arxiv.org/abs/sicurezza-alta"]) == set()


def test_risposta_llm_non_valida_viene_ripulita(sessioni):
    def sbagliato(sistema, messaggio, schema):
        if schema is prompt.SCHEMA_PREFILTRO:
            return {"pertinenti": [0, 7, "x"]}  # 7 e "x" non esistono
        return {"punteggi": [{"interesse": 99, "pertinenza": 100}, {"interesse": 1, "pertinenza": 150}],
                "riassunto": "R", "titolo_it": "\"\""}  # due virgolette al posto della stringa vuota

    _, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-x")), provider=Finto(sbagliato))
    assert [(p.interesse_id, p.punteggio) for p in salvate[0].pertinenze] == [(1, 100)]
    assert salvate[0].titolo_it is None


def test_una_sola_esecuzione_alla_volta(sessioni):
    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Finto(risponditore), fonti=raccolta())
        esecutore.avvia("dashboard")
        with pytest.raises(GiaInCorso):
            esecutore.avvia("telegram")
        await esecutore.attendi()
        esecutore.avvia("cli")  # finita la prima, se ne può avviare un'altra
        await esecutore.attendi()

    asyncio.run(prova())


def test_senza_interessi_o_categorie_l_esecuzione_fallisce_con_il_motivo(sessioni):
    with sessioni() as s:  # configurazione incompleta, come prima della configurazione iniziale
        s.query(CategoriaArxiv).delete()
        s.commit()
    esecuzione, _, _, _ = esegui(sessioni, raccolta())
    assert esecuzione.stato == "fallita"
    assert "almeno una fonte" in esecuzione.motivo


def test_un_blocco_del_prefiltro_fallito_non_ferma_l_esecuzione(sessioni, monkeypatch):
    from gradiens.esecuzione import prefiltro as modulo
    from gradiens.llm.base import ErroreLLM

    monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 1)  # un blocco per notizia

    def rotto(sistema, messaggio, schema):
        if schema is prompt.SCHEMA_PREFILTRO and "rotto" in messaggio:
            raise ErroreLLM("timeout")
        return risponditore(sistema, messaggio, schema)

    esecuzione, metriche, salvate, _ = esegui(
        sessioni, raccolta(candidata("sicurezza-alta"), candidata("sicurezza-rotto")), provider=Finto(rotto))
    assert esecuzione.stato == "completata"
    assert [n.titolo for n in salvate] == ["sicurezza-alta"]
    assert metriche["fonti"]["arxiv"]["errori"] == 1
    with sessioni() as s:  # il blocco fallito si riprova alla prossima esecuzione
        assert notizie.gia_viste(s, ["https://arxiv.org/abs/sicurezza-rotto"]) == set()


def test_spegnimento_durante_l_esecuzione_la_registra_come_interrotta(sessioni):
    class Lento:
        nome = "lento"

        async def pronto(self):
            pass

        async def chiedi(self, **_):
            await asyncio.sleep(60)

    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Lento(),
                              fonti=raccolta(candidata("sicurezza-alta")))
        esecutore.avvia("cli")
        await asyncio.sleep(0.1)
        await esecutore.ferma()
        assert esecutore.avanzamento is None

    asyncio.run(prova())
    with sessioni() as s:
        esecuzione = s.scalars(select(Esecuzione)).one()
        assert esecuzione.stato == "interrotta" and "spento" in esecuzione.motivo


def test_youtube_short_trascrizione_assente_diretta_e_canale_irraggiungibile(sessioni):
    from gradiens.fonti import ContenutoAssente, NonAncoraDisponibile

    with sessioni() as s:
        impostazioni.aggiungi_canale(s, "UC" + "a" * 22, "Lab di Sicurezza")
        impostazioni.aggiungi_canale(s, "UC" + "b" * 22, "Canale rotto")

    def video(nome):
        c = candidata(nome)
        c.tipo, c.url, c.fonte, c.contenuto = "video", f"https://www.youtube.com/watch?v={nome}", "Lab di Sicurezza", ""
        return c

    async def raccogli_yt(client, canale, dal):
        if canale.nome == "Canale rotto":
            raise httpx.ConnectError("irraggiungibile")
        return [video("sicurezza-alta-short"), video("sicurezza-muto"), video("sicurezza-diretta"), video("sicurezza-alta-lungo")]

    async def completa(client, c):
        if "muto" in c.titolo:
            raise ContenutoAssente("trascrizione assente")
        if "diretta" in c.titolo:
            raise NonAncoraDisponibile("diretta non ancora disponibile")
        c.tipo = "short" if "short" in c.titolo else "video"
        c.contenuto = "parola " * (20_000 if "lungo" in c.titolo else 10)
        return c

    fonti = {**raccolta(candidata("sicurezza-alta-paper")), "youtube": SimpleNamespace(raccogli=raccogli_yt, completa=completa)}
    finto = Finto(risponditore)

    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: finto, fonti=fonti)
        esecutore.avvia("cli")
        await esecutore.attendi()

    asyncio.run(prova())
    with sessioni() as s:
        esecuzione = s.scalars(select(Esecuzione)).one()
        salvate = {n.titolo: n for n in s.scalars(select(Notizia))}
        metriche = json.loads(esecuzione.metriche)
        viste = notizie.gia_viste(s, [f"https://www.youtube.com/watch?v=sicurezza-{n}" for n in ("muto", "diretta")])

    assert esecuzione.stato == "completata"
    assert salvate["sicurezza-alta-short"].tipo == "short"
    assert salvate["sicurezza-alta-lungo"].stato == "contenuto parziale"  # trascrizione oltre il tetto
    assert "sicurezza-alta-paper" in salvate  # arXiv non risente del canale irraggiungibile
    yt = metriche["fonti"]["youtube"]
    assert (yt["esaminate"], yt["senza_contenuto"], yt["mostrate"], yt["errori"]) == (4, 1, 2, 1)
    assert [p["stato"] for p in yt["problemi"]] == ["trascrizione assente"]
    assert {st["stato"] for st in yt["stati"]} == {"ok", "non raggiungibile"}  # un canale per stato
    assert metriche["token"]["elaborazione"]["provider"] == "claude-code" and "raccolta_s" in yt
    assert viste == {"https://www.youtube.com/watch?v=sicurezza-muto"}  # la diretta si riprende la volta dopo
    assert all(len(m) < 70_000 for _, m in finto.chiamate)  # contenuto troncato prima di Claude


def test_siti_stato_guasti_e_rigenerazione_dopo_tre(sessioni):
    from gradiens.dati import siti as dati_siti
    from gradiens.dati.modelli import Sito
    from gradiens.fonti import siti

    with sessioni() as s:
        dati_siti.aggiungi(s, "https://redhotcyber.com/", siti.Profilo(url="https://redhotcyber.com/", strategie=["feed"]).come_dict())
        dati_siti.aggiungi(s, "https://bloccato.example/", siti.Profilo(url="https://bloccato.example/").come_dict())

    rigenerati = []

    async def raccogli(client, profilo, dal, inizio_finestra=None):
        if "bloccato" in profilo.url:
            return siti.EsitoSito([], "accesso bloccato", True, "Il sito rifiuta le richieste.")
        articolo = candidata("sicurezza-alta-articolo")
        articolo.tipo, articolo.url, articolo.fonte, articolo.contenuto = "sito", "https://redhotcyber.com/articolo", "redhotcyber.com", ""
        return siti.EsitoSito([articolo], "ok", False, "1 articolo")

    async def rigenera(client, profilo):
        rigenerati.append(profilo.url)
        return siti.Profilo(url=profilo.url, strategie=["html"])

    async def completa(client, c):
        c.contenuto = "testo dell'articolo"
        return c

    fonti = {**raccolta(), "siti": SimpleNamespace(raccogli=raccogli, rigenera=rigenera, completa=completa)}

    async def tre_esecuzioni():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Finto(risponditore), fonti=fonti)
        for _ in range(3):
            esecutore.avvia("programmazione")
            await esecutore.attendi()

    asyncio.run(tre_esecuzioni())
    with sessioni() as s:
        bloccato = s.scalars(select(Sito).where(Sito.url.contains("bloccato"))).one()
        buono = s.scalars(select(Sito).where(Sito.url.contains("redhotcyber"))).one()
        salvate = list(s.scalars(select(Notizia)))
        ultima = json.loads(s.scalars(select(Esecuzione).order_by(Esecuzione.id.desc())).first().metriche)

    assert rigenerati == ["https://bloccato.example/"]  # solo al terzo guasto di fila (WEB-24)
    assert (bloccato.stato, bloccato.guasti_consecutivi) == ("profilo rigenerato", 0)
    assert json.loads(bloccato.profilo)["strategie"] == ["html"] and bloccato.profilo_precedente
    assert (buono.stato, buono.guasti_consecutivi) == ("ok", 0)
    assert [(n.tipo, n.url) for n in salvate] == [("sito", "https://redhotcyber.com/articolo")]
    stati = {st["fonte"]: st for st in ultima["fonti"]["siti"]["stati"]}
    assert stati["bloccato.example"]["stato"] == "profilo rigenerato"
    assert "Il sito rifiuta le richieste." in stati["bloccato.example"]["dettaglio"]
    assert (stati["redhotcyber.com"]["stato"], stati["redhotcyber.com"]["nuove"]) == ("ok", 0)  # già visto


def test_sito_che_non_risponde_tiene_il_profilo_vecchio_e_riprova_ogni_tre_guasti(sessioni):
    """Decisione 21: se la nuova analisi non trova strategie, il profilo resta quello di prima e il problema si vede."""
    from gradiens.dati import siti as dati_siti
    from gradiens.dati.modelli import Sito
    from gradiens.fonti import siti

    vecchio = siti.Profilo(url="https://giu.example/", strategie=["feed"], feed=["https://giu.example/feed/"]).come_dict()
    with sessioni() as s:
        dati_siti.aggiungi(s, "https://giu.example/", vecchio)

    rigenerati = []

    async def raccogli(client, profilo, dal, inizio_finestra=None):
        return siti.EsitoSito([], "nessuna strategia funzionante", True, "Il feed non si legge (errore di rete).")

    async def rigenera(client, profilo):
        rigenerati.append(profilo.url)
        return None  # l'analisi non ha trovato niente

    fonti = {**raccolta(), "siti": SimpleNamespace(raccogli=raccogli, rigenera=rigenera, completa=None)}

    async def esecuzioni(quante):
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Finto(risponditore), fonti=fonti)
        for _ in range(quante):
            esecutore.avvia("programmazione")
            await esecutore.attendi()

    asyncio.run(esecuzioni(3))
    with sessioni() as s:
        sito = s.scalars(select(Sito)).one()
        ultima = json.loads(s.scalars(select(Esecuzione).order_by(Esecuzione.id.desc())).first().metriche)
        assert json.loads(sito.profilo) == vecchio and sito.profilo_precedente is None
        assert (sito.stato, sito.guasti_consecutivi) == ("nessuna strategia funzionante", 3)  # resta tra gli avvisi
        assert "tengo il profilo di prima" in sito.dettaglio
    stato = ultima["fonti"]["siti"]["stati"][0]
    assert stato["stato"] == "nessuna strategia funzionante" and "tengo il profilo di prima" in stato["dettaglio"]
    assert rigenerati == ["https://giu.example/"]

    asyncio.run(esecuzioni(3))
    assert len(rigenerati) == 2  # di nuovo al sesto guasto di fila, non a ogni esecuzione


@pytest.mark.parametrize("escludi", [True, False])
def test_articoli_a_pagamento_e_sponsorizzati_secondo_gli_interruttori(sessioni, escludi):
    def a_pagamento(nome):
        c = candidata(nome)
        c.stato = "contenuto parziale (paywall)"
        return c

    esecuzione, metriche, salvate, finto = esegui(
        sessioni, raccolta(a_pagamento("sicurezza-alta-paywall"), candidata("offerta-sconto")),
        escludi_pagamento=escludi, escludi_sponsorizzati=escludi)
    assert (salvate == []) is escludi  # con l'esclusione non si valuta nemmeno (niente quota)
    arxiv = metriche["fonti"]["arxiv"]
    assert arxiv["escluse"] == (2 if escludi else 0)
    assert [e["motivo"] for e in arxiv["notizie_escluse"]] == (["sponsorizzato o offerta", "a pagamento"] if escludi else [])
    assert arxiv["scartate_prefiltro"] == (0 if escludi else 1)
    prefiltro = next(sistema for sistema, _ in finto.chiamate if "pre-filtro" in sistema)
    assert ("sponsorizzati" in prefiltro) is escludi


def test_un_video_segnalato_come_sponsorizzato_si_valuta_comunque(sessioni):
    """S-01, decisione 36: l'esclusione degli sponsorizzati non vale per i video; per i siti sì."""
    from gradiens.dati import siti as dati_siti
    from gradiens.fonti import siti

    with sessioni() as s:
        impostazioni.aggiungi_canale(s, "UC" + "a" * 22, "Lab di Sicurezza")
        dati_siti.aggiungi(s, "https://buono.it/", siti.Profilo(url="https://buono.it/").come_dict())

    def di_tipo(nome, tipo, url, fonte):
        c = candidata(nome)
        c.tipo, c.url, c.fonte = tipo, url, fonte
        return c

    async def raccogli_yt(client, canale, dal):
        return [di_tipo("offerta-alta-video", "video", "https://www.youtube.com/watch?v=v1", "Lab di Sicurezza")]

    async def raccogli_sito(client, profilo, dal, inizio_finestra=None):
        return siti.EsitoSito([di_tipo("offerta-alta-sconto", "sito", "https://buono.it/sconto", "buono.it")], "ok", False, "")

    fonti = {**raccolta(), "youtube": SimpleNamespace(raccogli=raccogli_yt), "siti": SimpleNamespace(raccogli=raccogli_sito)}
    _, metriche, salvate, _ = esegui(sessioni, fonti)

    assert [(n.tipo, n.titolo) for n in salvate] == [("video", "offerta-alta-video")]
    assert metriche["fonti"]["youtube"]["escluse"] == 0
    assert [e["motivo"] for e in metriche["fonti"]["siti"]["notizie_escluse"]] == ["sponsorizzato o offerta"]
    with sessioni() as s:
        assert notizie.gia_viste(s, ["https://buono.it/sconto"]) == {"https://buono.it/sconto"}


def test_avviso_di_fine_esecuzione_ma_non_allo_spegnimento(sessioni):
    avvisate = []

    async def al_termine(id):
        avvisate.append(id)

    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Finto(risponditore), fonti=raccolta(candidata("sicurezza-alta")))
        esecutore.al_termine = al_termine
        prima = esecutore.avvia("telegram")
        await esecutore.attendi()

        async def lenta(client, categorie, dal):
            await asyncio.sleep(10)
            return []
        esecutore._fonti = {"arxiv": SimpleNamespace(raccogli=lenta)}
        esecutore.avvia("dashboard")
        await asyncio.sleep(0.05)
        await esecutore.ferma()  # spegnimento durante l'esecuzione (ESE-12): nessun messaggio
        return prima

    assert avvisate == [asyncio.run(prova())]


def test_argomenti_a_fine_esecuzione(sessioni):
    """ESE-08, ADR 0008: le notizie dello stesso evento finiscono in un argomento solo, anche in blocchi diversi."""
    esecuzione, metriche, salvate, finto = esegui(sessioni, raccolta(
        candidata("sicurezza-alta-attacco-1"), candidata("sicurezza-alta-attacco-2"), candidata("sicurezza-alta-guida")))
    assert esecuzione.stato == "completata"
    with sessioni() as s:
        notizie_salvate = {n.titolo: n for n in s.scalars(select(Notizia))}
        assert notizie_salvate["sicurezza-alta-attacco-1"].argomento_id == notizie_salvate["sicurezza-alta-attacco-2"].argomento_id
        assert notizie_salvate["sicurezza-alta-attacco-1"].argomento.nome == "Attacco alla ASL"
        assert notizie_salvate["sicurezza-alta-guida"].argomento_id is None
    # Un'esecuzione dopo: l'argomento esistente compare nel prompt con il suo id.
    sistema = next(sis for sis, _ in finto.chiamate if "passo degli argomenti" in sis)
    assert "(nessuno)" in sistema


def test_passo_degli_argomenti_fallito_non_ferma_l_esecuzione(sessioni):
    def guasto(sistema, messaggio, schema):
        if schema is prompt.SCHEMA_ARGOMENTI:
            raise ErroreLLM("Claude non risponde")
        return risponditore(sistema, messaggio, schema)

    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta-attacco")), provider=Finto(guasto))
    assert esecuzione.stato == "completata" and len(salvate) == 1


def test_nuovo_argomento_con_il_nome_di_uno_esistente_non_crea_doppioni(sessioni):
    async def due_esecuzioni():
        for nome in ("sicurezza-alta-attacco-1", "sicurezza-alta-attacco-2"):  # il Claude finto risponde sempre "nuovo"
            esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Finto(risponditore), fonti=raccolta(candidata(nome)))
            esecutore.avvia("cli")
            await esecutore.attendi()

    asyncio.run(due_esecuzioni())
    with sessioni() as s:
        assert [a.nome for a in s.scalars(select(Argomento))] == ["Attacco alla ASL"]
        assert len(s.scalars(select(Argomento)).one().notizie) == 2


def test_proposta_di_raffinamento_a_fine_esecuzione(sessioni):
    """INT-04: 3 cuori nuovi su notizie pertinenti, e alla fine dell'esecuzione c'è una proposta."""
    with sessioni() as s:
        for nome in ("a", "b", "c"):
            s.add(Notizia(tipo="arxiv", url=f"https://arxiv.org/abs/cuore-{nome}", fonte="cs.CR", titolo=nome, riassunto="r",
                          pubblicata_il=notizie.adesso(), scoperta_il=notizie.adesso(), cuore=True, cuore_il=notizie.adesso(),
                          pertinenze=[Pertinenza(interesse_id=1, punteggio=90)]))
        s.commit()

    def con_proposta(sistema, messaggio, schema):
        if schema is prompt.SCHEMA_RAFFINAMENTO:
            assert "attacchi informatici" in sistema  # descrizione dell'utente, da non cambiare
            return {"raffinamento": "Soprattutto ransomware nella sanità."}
        if schema is prompt.SCHEMA_NUOVO_INTERESSE:  # INT-06: gli stessi cuori, con i punteggi per interesse
            assert '"punteggi": {"' in messaggio and ": 90}" in messaggio
            return {"nome": "", "descrizione": ""}  # tutto già coperto: nessun interesse nuovo
        return risponditore(sistema, messaggio, schema)

    esecuzione, _, _, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")), provider=Finto(con_proposta))
    assert esecuzione.stato == "completata"
    with sessioni() as s:
        [p] = s.scalars(select(Proposta)).all()
        assert (p.interesse_id, p.testo, p.notizie) == (1, "Soprattutto ransomware nella sanità.", 3)



def test_senza_claude_code_collegato_l_esecuzione_non_parte(sessioni):
    """ACC-15: prima si fallivano tutti i blocchi del pre-filtro e l'esecuzione risultava "completata"."""
    class Scollegato(Finto):
        async def pronto(self):
            raise ErroreLLM("Claude Code non è collegato a un account.")

    provider = Scollegato(risponditore)
    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")), provider=provider)
    assert (esecuzione.stato, esecuzione.motivo) == ("fallita", "Claude Code non è collegato a un account.")
    assert salvate == [] and provider.chiamate == []  # nessuna quota consumata


def test_aspetta_la_rete_prima_di_raccogliere(sessioni, monkeypatch):
    """All'accensione la rete arriva dopo Gradiens: l'esecuzione recuperata falliva su tutte le fonti."""
    from gradiens.esecuzione import esecutore as modulo

    risposte = iter([False, False, True])
    monkeypatch.setattr(modulo, "rete_disponibile", lambda: next(risposte))
    monkeypatch.setattr(modulo, "PAUSA_RETE", 0)
    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")))
    assert esecuzione.stato == "completata" and len(salvate) == 1

    monkeypatch.setattr(modulo, "rete_disponibile", lambda: False)
    monkeypatch.setattr(modulo, "ATTESA_RETE", 0)
    with sessioni() as s:
        s.query(Esecuzione).delete()
        s.commit()
    esecuzione, _, _, _ = esegui(sessioni, raccolta(candidata("sicurezza-altra")))
    assert (esecuzione.stato, esecuzione.motivo) == ("fallita", "Nessuna connessione a internet: controlla la rete e riprova.")


def test_aspetta_la_rete_fino_a_quindici_minuti(sessioni, monkeypatch):
    """Scheda 13 (I-4) del documento 04, decisione 40: all'accensione la rete è arrivata anche dopo 5-10 minuti."""
    from gradiens.esecuzione import esecutore as modulo

    tempo = [0.0]  # orologio finto: ogni controllo della rete dura 5 secondi

    def rete_disponibile():
        tempo[0] += 5
        return tempo[0] >= 14 * 60  # la rete arriva dopo 14 minuti

    monkeypatch.setattr(modulo, "time", SimpleNamespace(monotonic=lambda: tempo[0]))
    monkeypatch.setattr(modulo, "rete_disponibile", rete_disponibile)
    monkeypatch.setattr(modulo, "PAUSA_RETE", 0)
    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")))
    assert esecuzione.stato == "completata" and len(salvate) == 1


# Test di caratterizzazione T-02…T-07 (docs/miglioramenti/02-test-e-copertura.md, decisione 26): fissano il
# comportamento di oggi prima di ADR 0010 e 0011. Dove sembra sbagliato restano verdi con "vedi S-nn" (decisione 24).


def di_sito(nome: str, url: str) -> Candidata:
    c = candidata(nome)
    c.tipo, c.url, c.fonte, c.contenuto = "sito", url, "buono.it", ""
    return c


async def completa_finta(client, c):
    """`completa` di una fonte: "muto" non ha contenuto (YT-05), "diretta" non è ancora disponibile (YT-04)."""
    from gradiens.fonti import ContenutoAssente, NonAncoraDisponibile

    if "muto" in c.titolo:
        raise ContenutoAssente("trascrizione assente")
    if "diretta" in c.titolo:
        raise NonAncoraDisponibile("diretta non ancora disponibile")
    return c


def guasto_su(parola: str, schema_guasto: dict, errore: Exception) -> Finto:
    """Finto che solleva `errore` quando il messaggio di quello schema contiene `parola`."""
    def risponde(sistema, messaggio, schema):
        if schema is schema_guasto and parola in messaggio:
            raise errore
        return risponditore(sistema, messaggio, schema)
    return Finto(risponde)


def esecuzioni_di_fila(sessioni, fonti, provider, volte: int) -> list[tuple[Esecuzione, dict]]:
    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda nome: provider, fonti=fonti)
        for _ in range(volte):
            esecutore.avvia("cli")
            await esecutore.attendi()

    asyncio.run(prova())
    with sessioni() as s:
        return [(e, json.loads(e.metriche)) for e in s.scalars(select(Esecuzione).order_by(Esecuzione.id))]


class Concorrente(Finto):
    """Finto che cede il controllo a ogni chiamata e conta quante chiamate di pre-filtro sono in corso insieme."""

    def __init__(self, risponditore):
        super().__init__(risponditore)
        self.in_corso = self.massimo = 0

    async def chiedi(self, *, sistema, messaggio, schema, modello):
        prefiltro = schema is prompt.SCHEMA_PREFILTRO
        self.in_corso += prefiltro
        self.massimo = max(self.massimo, self.in_corso)
        try:
            await asyncio.sleep(0)
            return await super().chiedi(sistema=sistema, messaggio=messaggio, schema=schema, modello=modello)
        finally:
            self.in_corso -= prefiltro


def blocchi_prefiltro(provider: Finto) -> list[list[str]]:
    """I titoli di ogni chiamata di pre-filtro, nell'ordine delle chiamate."""
    return [[v["titolo"] for v in json.loads(m)] for sistema, m in provider.chiamate if sistema.startswith("Sei il pre-filtro")]


# ADR 0010: i paper passano dal pre-filtro dal più recente, a giri, finché i promossi riempiono il tetto.
# Sostituiscono T-02, che fissava il comportamento precedente (tutti i paper pre-filtrati, poi il tetto).

def test_prefiltro_arxiv_si_ferma_quando_i_promossi_riempiono_il_tetto(sessioni):
    paper = [candidata(f"sicurezza-alta-{i:02d}", ore_fa=i + 1) for i in range(100)]  # 00 è il più recente
    provider = Finto(risponditore)
    _, _, salvate, _ = esegui(sessioni, raccolta(*paper), provider=provider, tetto_arxiv=5)

    assert blocchi_prefiltro(provider) == [[f"sicurezza-alta-{i:02d}" for i in range(30)]]  # 1 chiamata, non 4
    assert sorted(n.titolo for n in salvate) == [f"sicurezza-alta-{i:02d}" for i in range(5)]


def test_i_paper_non_prefiltrati_sono_visti_e_contano_come_oltre_il_tetto(sessioni):
    paper = [candidata(f"sicurezza-alta-{i:02d}", ore_fa=i + 1) for i in range(100)]
    _, metriche, _, _ = esegui(sessioni, raccolta(*paper), tetto_arxiv=5)

    a = metriche["fonti"]["arxiv"]  # 25 promossi in eccesso + 70 mai pre-filtrati
    assert (a["esaminate"], a["scartate_prefiltro"], a["oltre_tetto"], a["mostrate"]) == (100, 0, 95, 5)
    with sessioni() as s:  # non si valutano e non tornano (ARX-02, ARX-03)
        assert notizie.gia_viste(s, [c.url for c in paper]) == {c.url for c in paper}


def test_con_pochi_promossi_i_giri_continuano_fino_all_ultimo_paper(sessioni, monkeypatch):
    """Ogni giro lancia solo i blocchi che potrebbero riempire il tetto, al massimo GIRO_PREFILTRO insieme."""
    from gradiens.esecuzione import prefiltro as modulo

    monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 1)
    nomi = ["sicurezza-alta-0", "sicurezza-alta-1", "cucina-2", "cucina-3", "sicurezza-alta-4", "cucina-5",
            "cucina-6", "cucina-7", "sicurezza-alta-8"]
    provider = Concorrente(risponditore)
    _, metriche, salvate, _ = esegui(sessioni, raccolta(*(candidata(n, ore_fa=i + 1) for i, n in enumerate(nomi))),
                                     provider=provider, tetto_arxiv=4)

    # giro 1: 3 blocchi (mancano 4, al massimo 3 insieme), 2 promossi; giro 2: 2 blocchi, 1 promosso;
    # giri 3-5: 1 blocco, nessun promosso; giro 6: 1 blocco, il quarto promosso.
    assert blocchi_prefiltro(provider) == [[n] for n in nomi]
    assert provider.massimo == 3
    assert sorted(n.titolo for n in salvate) == ["sicurezza-alta-0", "sicurezza-alta-1", "sicurezza-alta-4",
                                                 "sicurezza-alta-8"]
    a = metriche["fonti"]["arxiv"]
    assert (a["scartate_prefiltro"], a["oltre_tetto"]) == (5, 0)


def test_i_paper_valutati_sono_i_piu_recenti_tra_i_promossi(sessioni, monkeypatch):
    """Elenco atteso scritto a mano. La raccolta non è in ordine di data: il pre-filtro parte dal più recente."""
    from gradiens.esecuzione import prefiltro as modulo

    monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 2)
    ore = {"sicurezza-alta-a": 2, "cucina-b": 1, "sicurezza-alta-c": 5, "sicurezza-alta-d": 3, "cucina-e": 4,
           "sicurezza-alta-f": 6, "sicurezza-alta-g": 7}
    provider = Finto(risponditore)
    _, metriche, salvate, _ = esegui(sessioni, raccolta(*(candidata(n, ore_fa=o) for n, o in ore.items())),
                                     provider=provider, tetto_arxiv=3)

    # giro 1: due blocchi, promossi a e d; giro 2: un blocco, promossi c e f (uno in eccesso); g mai pre-filtrato.
    assert blocchi_prefiltro(provider) == [["cucina-b", "sicurezza-alta-a"], ["sicurezza-alta-d", "cucina-e"],
                                           ["sicurezza-alta-c", "sicurezza-alta-f"]]
    assert sorted(n.titolo for n in salvate) == ["sicurezza-alta-a", "sicurezza-alta-c", "sicurezza-alta-d"]
    assert metriche["fonti"]["arxiv"]["oltre_tetto"] == 2  # f promosso in eccesso, g non pre-filtrato
    with sessioni() as s:
        assert notizie.gia_viste(s, ["https://arxiv.org/abs/sicurezza-alta-f", "https://arxiv.org/abs/sicurezza-alta-g"]) == {
            "https://arxiv.org/abs/sicurezza-alta-f", "https://arxiv.org/abs/sicurezza-alta-g"}


def test_dopo_un_blocco_fallito_non_partono_giri_nuovi(sessioni, monkeypatch):
    """I paper mai pre-filtrati restano non visti e contano come errori: si riprendono la volta dopo (ADR 0010)."""
    from gradiens.esecuzione import prefiltro as modulo

    monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 1)
    paper = [candidata("sicurezza-alta-rotto" if i == 1 else f"sicurezza-alta-{i}", ore_fa=i + 1) for i in range(6)]
    provider = guasto_su("rotto", prompt.SCHEMA_PREFILTRO, ErroreLLM("timeout"))
    esecuzione, metriche, salvate, _ = esegui(sessioni, raccolta(*paper), provider=provider, tetto_arxiv=5)

    assert esecuzione.stato == "completata"
    assert blocchi_prefiltro(provider) == [["sicurezza-alta-0"], ["sicurezza-alta-rotto"], ["sicurezza-alta-2"]]
    assert sorted(n.titolo for n in salvate) == ["sicurezza-alta-0", "sicurezza-alta-2"]
    a = metriche["fonti"]["arxiv"]
    assert (a["errori"], a["oltre_tetto"]) == (4, 0)  # il blocco fallito più i tre paper mai pre-filtrati
    with sessioni() as s:
        assert notizie.gia_viste(s, [c.url for c in paper[1:2] + paper[3:]]) == set()


def test_siti_e_youtube_si_prefiltrano_tutti_e_non_si_mescolano_ai_paper(sessioni):
    from gradiens.dati import siti as dati_siti
    from gradiens.fonti import siti

    with sessioni() as s:
        impostazioni.aggiungi_canale(s, "UC" + "a" * 22, "Lab di Sicurezza")
        dati_siti.aggiungi(s, "https://buono.it/", siti.Profilo(url="https://buono.it/").come_dict())

    def video(i):
        c = candidata(f"sicurezza-alta-video-{i:02d}")
        c.tipo, c.url, c.fonte = "video", f"https://www.youtube.com/watch?v=v{i:02d}", "Lab di Sicurezza"
        return c

    async def raccogli_yt(client, canale, dal):
        return [video(i) for i in range(35)]

    async def raccogli_sito(client, profilo, dal, inizio_finestra=None):
        return siti.EsitoSito([di_sito("sicurezza-alta-articolo", "https://buono.it/articolo")], "ok", False, "")

    paper = [candidata(f"sicurezza-alta-paper-{i}", ore_fa=i + 1) for i in range(5)]
    fonti = {**raccolta(*paper), "youtube": SimpleNamespace(raccogli=raccogli_yt),
             "siti": SimpleNamespace(raccogli=raccogli_sito)}
    provider = Finto(risponditore)
    _, metriche, salvate, _ = esegui(sessioni, fonti, provider=provider, tetto_arxiv=1)

    blocchi = blocchi_prefiltro(provider)
    di_paper = [b for b in blocchi if any("paper" in t for t in b)]
    assert di_paper == [[c.titolo for c in paper]]  # un blocco di soli paper
    assert sorted(len(b) for b in blocchi if b not in di_paper) == [6, 30]  # 35 video e un articolo, tutti
    assert len(salvate) == 35 + 1 + 1
    assert metriche["fonti"]["arxiv"]["oltre_tetto"] == 4


ESITI = ("scartate_prefiltro", "escluse", "oltre_tetto", "senza_contenuto", "scartate_valutazione", "mostrate", "errori")


@pytest.mark.parametrize("scenario", ["tetto", "tetto con paper non pre-filtrati", "esclusioni e senza contenuto",
                                      "blocco fallito", "valutazione fallita", "diretta"])
def test_i_contatori_di_una_fonte_tornano(sessioni, monkeypatch, scenario):
    """T-03, ESE-11: `esaminate` è la somma degli esiti. Non vale con le dirette (YT-04: non entrano in nessun
    contatore) e quando `errori` conta anche errori di fonte o di sito (`_raccogli`, `_raccogli_sito`)."""
    from gradiens.esecuzione import prefiltro as modulo

    candidate = [candidata("sicurezza-alta", 1), candidata("sicurezza-alta-vecchia", 5), candidata("sicurezza-bassa", 3),
                 candidata("cucina")]
    imp, provider, esito_atteso = {}, None, "errori"
    if scenario == "tetto":
        imp, esito_atteso = {"tetto_arxiv": 1}, "oltre_tetto"
    elif scenario == "tetto con paper non pre-filtrati":  # ADR 0010: un paper a blocco, ci si ferma al primo promosso
        monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 1)
        imp, esito_atteso = {"tetto_arxiv": 1}, "oltre_tetto"
    elif scenario == "esclusioni e senza contenuto":
        a_pagamento = candidata("sicurezza-alta-paywall")
        a_pagamento.stato = "contenuto parziale (paywall)"
        candidate += [a_pagamento, candidata("offerta-sconto"), candidata("sicurezza-alta-muto")]
        imp, esito_atteso = {"escludi_pagamento": True, "escludi_sponsorizzati": True}, "senza_contenuto"
    elif scenario == "blocco fallito":
        monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 1)
        provider = guasto_su("sicurezza-bassa", prompt.SCHEMA_PREFILTRO, ErroreLLM("timeout"))
    elif scenario == "valutazione fallita":
        provider = guasto_su("sicurezza-alta-vecchia", prompt.SCHEMA_VALUTAZIONE, ErroreLLM("timeout"))
    else:
        candidate.append(candidata("sicurezza-alta-diretta"))
        esito_atteso = "mostrate"
    fonti = raccolta(*candidate)
    fonti["arxiv"].completa = completa_finta

    esecuzione, metriche, _, _ = esegui(sessioni, fonti, provider=provider, **imp)
    c = metriche["fonti"]["arxiv"]
    assert esecuzione.stato == "completata" and c[esito_atteso] > 0  # lo scenario prova davvero il suo esito
    if scenario == "esclusioni e senza contenuto":
        assert c["escluse"] == 2
    if scenario == "diretta":
        assert (c["esaminate"], sum(c[k] for k in ESITI)) == (5, 4)  # la diretta non è contata da nessuna parte
    else:
        assert c["esaminate"] == sum(c[k] for k in ESITI)


def test_una_valutazione_fallita_non_segna_vista_la_notizia_e_la_rimanda_al_prefiltro(sessioni):
    """T-04. Vedi S-36: la notizia ripassa da pre-filtro e valutazione a ogni esecuzione, fino a 7 giorni."""
    errori = iter([ErroreLLM("timeout"), RuntimeError("risposta inattesa")])

    def rotta(sistema, messaggio, schema):
        if schema is prompt.SCHEMA_VALUTAZIONE and "rotta" in messaggio:
            raise next(errori)
        return risponditore(sistema, messaggio, schema)

    provider = Finto(rotta)
    (prima, m1), (seconda, m2) = esecuzioni_di_fila(
        sessioni, raccolta(candidata("sicurezza-alta"), candidata("sicurezza-alta-rotta")), provider, volte=2)

    assert (prima.stato, seconda.stato) == ("completata", "completata")
    assert (m1["fonti"]["arxiv"]["mostrate"], m1["fonti"]["arxiv"]["errori"]) == (1, 1)
    assert (m2["fonti"]["arxiv"]["esaminate"], m2["fonti"]["arxiv"]["errori"]) == (1, 1)  # solo la notizia fallita
    rotta_in = [sistema.split(" di Gradiens")[0] for sistema, messaggio in provider.chiamate if "rotta" in messaggio]
    assert sorted(rotta_in) == ["Sei il pre-filtro"] * 2 + ["Sei il valutatore"] * 2
    with sessioni() as s:
        assert notizie.gia_viste(s, ["https://arxiv.org/abs/sicurezza-alta-rotta"]) == set()
        assert [n.titolo for n in s.scalars(select(Notizia))] == ["sicurezza-alta"]


class QuotaAlPrimoBlocco:
    """Provider: il primo blocco di pre-filtro trova la quota esaurita, gli altri restano in attesa."""
    nome = "finto"

    def __init__(self):
        self.chiamate = self.cancellate = self.finite = 0

    async def pronto(self):
        pass

    async def chiedi(self, *, sistema, messaggio, schema, modello):
        self.chiamate += 1
        if self.chiamate == 1:
            raise QuotaEsaurita("Quota dell'abbonamento esaurita")
        try:
            await asyncio.sleep(60)  # non finisce mai prima della cancellazione
        except asyncio.CancelledError:
            self.cancellate += 1
            raise
        self.finite += 1


def test_quota_esaurita_nel_prefiltro_interrompe_e_non_segna_viste_le_notizie(sessioni, monkeypatch):
    """T-05. L'ADR 0010 sostituisce i blocchi paralleli con giri in sequenza: questa semantica deve restare."""
    from gradiens.esecuzione import prefiltro as modulo

    monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 1)
    paper = [candidata(f"sicurezza-alta-{i}") for i in range(3)]
    provider = QuotaAlPrimoBlocco()
    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(*paper), provider=provider)

    assert esecuzione.stato == "interrotta" and "Quota" in esecuzione.motivo
    assert salvate == []
    assert provider.finite == 0 and provider.cancellate == provider.chiamate - 1  # i blocchi fratelli sono cancellati
    with sessioni() as s:
        assert notizie.gia_viste(s, [c.url for c in paper]) == set()


@pytest.mark.parametrize("giorni", [1, 3])
def test_l_esecutore_passa_a_ogni_fonte_la_finestra_di_raccolta(sessioni, giorni):
    """T-06, ESE-03: `dal = adesso - finestra_giorni` arriva a arXiv, YouTube e siti. Per i siti vale alla prima
    raccolta: dopo parte da "coperto fino a" (ADR 0011, test più in basso)."""
    from gradiens.dati import siti as dati_siti
    from gradiens.fonti import siti

    with sessioni() as s:
        impostazioni.aggiungi_canale(s, "UC" + "a" * 22, "Lab di Sicurezza")
        dati_siti.aggiungi(s, "https://buono.it/", siti.Profilo(url="https://buono.it/").come_dict())
    ricevuti = {}

    async def da_arxiv(client, categorie, dal):
        ricevuti["arxiv"] = dal
        return []

    async def da_youtube(client, canale, dal):
        ricevuti["youtube"] = dal
        return []

    async def da_sito(client, profilo, dal, inizio_finestra=None):
        ricevuti["siti"] = dal
        return siti.EsitoSito([], "nessun articolo nuovo", False, "")

    fonti = {"arxiv": SimpleNamespace(raccogli=da_arxiv), "youtube": SimpleNamespace(raccogli=da_youtube),
             "siti": SimpleNamespace(raccogli=da_sito)}
    prima = notizie.adesso()
    esecuzione, _, _, _ = esegui(sessioni, fonti, finestra_giorni=giorni)
    dopo = notizie.adesso()

    assert esecuzione.stato == "completata" and set(ricevuti) == {"arxiv", "youtube", "siti"}
    assert all(prima - timedelta(days=giorni) <= dal <= dopo - timedelta(days=giorni) for dal in ricevuti.values())


def test_lo_stato_del_sito_si_registra_alla_raccolta_anche_se_l_esecuzione_e_interrotta(sessioni):
    """T-07. Stato, dettaglio e guasti del sito si salvano subito dopo la raccolta, non a fine esecuzione.
    L'ADR 0011 salverà "coperto fino a" a fine esecuzione: questo contrasto deve restare voluto."""
    from gradiens.dati import siti as dati_siti
    from gradiens.dati.modelli import Sito
    from gradiens.fonti import siti

    with sessioni() as s:
        s.query(CategoriaArxiv).delete()  # solo il sito
        dati_siti.aggiungi(s, "https://buono.it/", siti.Profilo(url="https://buono.it/").come_dict())
    articolo = di_sito("sicurezza-alta-articolo", "https://buono.it/articolo")

    async def raccogli(client, profilo, dal, inizio_finestra=None):
        return siti.EsitoSito([articolo], "ok", True, "Problemi: il feed non ha articoli recenti.")

    provider = guasto_su("sicurezza-alta-articolo", prompt.SCHEMA_VALUTAZIONE, QuotaEsaurita("Quota esaurita"))
    esecuzione, _, salvate, _ = esegui(sessioni, {"siti": SimpleNamespace(raccogli=raccogli)}, provider=provider)

    assert esecuzione.stato == "interrotta" and salvate == []
    with sessioni() as s:
        sito = s.scalars(select(Sito)).one()
        assert (sito.stato, sito.dettaglio, sito.guasti_consecutivi) == (
            "ok", "Problemi: il feed non ha articoli recenti.", 1)
        assert notizie.gia_viste(s, [articolo.url]) == set()


# ADR 0011: raccolta incrementale dei siti. "coperto fino a" si salva a fine esecuzione e avanza fino alla notizia
# più vecchia del sito rimasta senza esito (decisione 34); niente margine di rilettura (decisione 37).


def sito_che_registra(*articoli: Candidata, guasto_alla_prima: bool = False):
    """Fonte siti finta: restituisce sempre gli stessi articoli e ricorda il `dal` ricevuto a ogni raccolta
    (l'inizio della finestra, che serve al controllo del feed fermo, in `finestre` della fonte)."""
    from gradiens.fonti import siti

    ricevuti, finestre = [], []

    async def raccogli(client, profilo, dal, inizio_finestra=None):
        ricevuti.append(dal)
        finestre.append(inizio_finestra)
        if guasto_alla_prima and len(ricevuti) == 1:
            return siti.EsitoSito([], "accesso bloccato", True, "Il sito rifiuta le richieste.")
        return siti.EsitoSito([replace(a) for a in articoli], "ok" if articoli else "nessun articolo nuovo", False, "")

    return {"siti": SimpleNamespace(raccogli=raccogli, completa=completa_finta, finestre=finestre)}, ricevuti


def con_un_sito(sessioni):
    from gradiens.dati import siti as dati_siti
    from gradiens.fonti import siti

    with sessioni() as s:
        s.query(CategoriaArxiv).delete()  # solo il sito
        impostazioni.leggi(s).finestra_giorni = 3
        s.commit()
        return dati_siti.aggiungi(s, "https://buono.it/", siti.Profilo(url="https://buono.it/").come_dict()).id


def test_la_seconda_esecuzione_cerca_nel_sito_solo_dopo_la_prima_raccolta(sessioni):
    con_un_sito(sessioni)
    fonti, ricevuti = sito_che_registra(di_sito("sicurezza-alta-articolo", "https://buono.it/articolo"))
    prima = notizie.adesso()
    esecuzioni_di_fila(sessioni, fonti, Finto(risponditore), volte=1)
    dopo = notizie.adesso()
    esecuzioni_di_fila(sessioni, fonti, Finto(risponditore), volte=1)

    assert prima - timedelta(days=3) <= ricevuti[0] <= dopo - timedelta(days=3)  # prima raccolta: finestra intera
    assert prima <= ricevuti[1] <= dopo  # poi da "coperto fino a": l'ora della prima raccolta
    assert ricevuti[1] - timedelta(days=3) <= fonti["siti"].finestre[1] <= notizie.adesso() - timedelta(days=3)


@pytest.mark.parametrize("errore", [ErroreLLM("timeout"), QuotaEsaurita("Quota esaurita")])
def test_una_notizia_rimasta_senza_esito_trattiene_il_sito_alla_sua_data(sessioni, errore):
    """Decisione 34: una valutazione fallita o un'esecuzione interrotta non fanno perdere la notizia."""
    con_un_sito(sessioni)
    rimasta = di_sito("sicurezza-alta-rotta", "https://buono.it/rotta")
    rimasta.pubblicata_il = notizie.adesso() - timedelta(hours=20)
    fonti, ricevuti = sito_che_registra(di_sito("sicurezza-alta-articolo", "https://buono.it/articolo"), rimasta)

    (esecuzione, _), = esecuzioni_di_fila(sessioni, fonti, guasto_su("rotta", prompt.SCHEMA_VALUTAZIONE, errore), volte=1)
    esecuzioni_di_fila(sessioni, fonti, Finto(risponditore), volte=1)

    assert esecuzione.stato == ("interrotta" if isinstance(errore, QuotaEsaurita) else "completata")
    assert ricevuti[1] == rimasta.pubblicata_il


@pytest.mark.parametrize("cambio", ["guasto", "finestra", "profilo"])
def test_dopo_un_guasto_o_un_cambio_si_riparte_dalla_finestra_intera(sessioni, cambio):
    """ADR 0011: dopo un guasto del sito, un cambio della finestra di raccolta o del profilo si cerca da capo."""
    from gradiens.dati import siti as dati_siti
    from gradiens.fonti import siti

    id = con_un_sito(sessioni)
    fonti, ricevuti = sito_che_registra(guasto_alla_prima=cambio == "guasto")
    esecuzioni_di_fila(sessioni, fonti, Finto(risponditore), volte=1)
    with sessioni() as s:
        if cambio == "finestra":
            impostazioni.leggi(s).finestra_giorni = 7
            s.commit()
        elif cambio == "profilo":
            profilo = siti.Profilo(url="https://buono.it/")
            profilo.aggiungi_feed("https://buono.it/feed")
            dati_siti.salva_profilo(s, id, profilo.come_dict())
    prima = notizie.adesso()
    esecuzioni_di_fila(sessioni, fonti, Finto(risponditore), volte=1)
    dopo = notizie.adesso()

    giorni = timedelta(days=7 if cambio == "finestra" else 3)
    assert prima - giorni <= ricevuti[1] <= dopo - giorni


def prefiltro_che_solleva(errori: dict[str, BaseException]) -> Finto:
    """Finto: il blocco di pre-filtro che contiene una delle parole solleva l'errore associato."""
    def risponde(sistema, messaggio, schema):
        for parola, errore in errori.items():
            if schema is prompt.SCHEMA_PREFILTRO and parola in messaggio:
                raise errore
        return risponditore(sistema, messaggio, schema)
    return Finto(risponde)


@pytest.mark.parametrize("errori, stato, motivo", [
    # T-27, S-02: la quota ha la precedenza anche se nello stesso gruppo c'è un altro errore.
    ({"quota": QuotaEsaurita("Quota dell'abbonamento esaurita"), "rotto": RuntimeError("guasto")},
     "interrotta", "Quota dell'abbonamento esaurita"),
    # S-07: il motivo è il testo dell'errore, non "unhandled errors in a TaskGroup".
    ({"rotto": RuntimeError("guasto")}, "fallita", "guasto"),
    ({"rotto": RuntimeError("guasto"), "quota": KeyError("chiave")}, "fallita", "guasto; 'chiave'"),
])
def test_quota_insieme_ad_un_altro_errore_nello_stesso_gruppo(sessioni, monkeypatch, errori, stato, motivo):
    from gradiens.esecuzione import prefiltro as modulo

    monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 1)  # un blocco per paper, tutti nello stesso giro
    paper = [candidata("sicurezza-alta-rotto", ore_fa=1), candidata("sicurezza-alta-quota", ore_fa=2)]
    esecuzione, _, _, _ = esegui(sessioni, raccolta(*paper), provider=prefiltro_che_solleva(errori))
    assert (esecuzione.stato, esecuzione.motivo) == (stato, motivo)


FORME_INATTESE = {  # T-28, S-05: (schema alterato, alterazione) -> il blocco o la notizia si riprova, non si perde
    "pre-filtro {}": (prompt.SCHEMA_PREFILTRO, lambda d: {}),
    "pertinenti null": (prompt.SCHEMA_PREFILTRO, lambda d: {**d, "pertinenti": None}),
    "pertinenti stringa": (prompt.SCHEMA_PREFILTRO, lambda d: {**d, "pertinenti": "tutti"}),
    "punteggi non oggetti": (prompt.SCHEMA_VALUTAZIONE, lambda d: {**d, "punteggi": ["x"]}),
    "riassunto null": (prompt.SCHEMA_VALUTAZIONE, lambda d: {**d, "riassunto": None}),
    # Valori semplici del tipo sbagliato: prima facevano fallire l'esecuzione intera in `_salva`.
    "titolo_it numero": (prompt.SCHEMA_VALUTAZIONE, lambda d: {**d, "titolo_it": 5}),
    "interesse lista": (prompt.SCHEMA_VALUTAZIONE, lambda d: {**d, "punteggi": [{"interesse": [1], "pertinenza": 90}]}),
}


@pytest.mark.parametrize("forma", FORME_INATTESE)
def test_risposte_llm_di_forma_inattesa(sessioni, monkeypatch, forma):
    """6 paper in 2 blocchi di pre-filtro da 3: si altera il primo blocco, oppure ogni valutazione."""
    from gradiens.esecuzione import prefiltro as modulo

    monkeypatch.setattr(modulo, "BLOCCO_PREFILTRO", 3)
    schema_alterato, altera = FORME_INATTESE[forma]
    chiamate = []

    def risponde(sistema, messaggio, schema):
        dati = risponditore(sistema, messaggio, schema)
        chiamate.append(schema)
        if schema is schema_alterato and (schema is prompt.SCHEMA_VALUTAZIONE or chiamate.count(schema) == 1):
            return altera(dati)
        return dati

    paper = [candidata(f"sicurezza-alta-{i}", ore_fa=i + 1) for i in range(6)]
    esecuzione, metriche, salvate, _ = esegui(sessioni, raccolta(*paper), provider=Finto(risponde))

    prefiltro = schema_alterato is prompt.SCHEMA_PREFILTRO
    assert esecuzione.stato == "completata"
    assert (len(salvate), metriche["fonti"]["arxiv"]["errori"]) == ((3, 3) if prefiltro else (0, 6))
    with sessioni() as s:  # le notizie della risposta storta non sono viste: si riprovano la volta dopo
        assert len(notizie.gia_viste(s, [c.url for c in paper])) == (3 if prefiltro else 0)


def test_una_pertinenza_con_la_virgola_si_arrotonda(sessioni):
    """Scheda 4 (b): tolleranti sui valori. Prima 85.5 era ignorato e la notizia scartata e vista."""
    def con_virgola(sistema, messaggio, schema):
        dati = risponditore(sistema, messaggio, schema)
        if schema is prompt.SCHEMA_VALUTAZIONE:
            dati["punteggi"] = [{"interesse": 1, "pertinenza": 85.5}]
        return dati

    _, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")), provider=Finto(con_virgola))
    assert [p.punteggio for p in salvate[0].pertinenze] == [86]


@pytest.mark.parametrize("fallimenti, stato", [(2, "completata"), (3, "in_corso")])
def test_un_errore_di_database_alla_chiusura_non_lascia_l_esecuzione_in_corso(sessioni, monkeypatch, fallimenti, stato):
    """T-26, S-06 e S-08: `termina` si riprova 3 volte; comunque vada, se ne può avviare un'altra. Se fallisce
    sempre, la riga resta "in corso" fino al prossimo avvio del servizio (`segna_interrotte`), senza errori fuori."""
    from sqlalchemy.exc import OperationalError

    from gradiens.esecuzione import esecutore as modulo

    vera, chiamate = modulo.esecuzioni.termina, []

    def termina(*argomenti, **opzioni):
        chiamate.append(1)
        if len(chiamate) <= fallimenti:
            raise OperationalError("UPDATE esecuzioni", {}, Exception("database is locked"))
        return vera(*argomenti, **opzioni)

    monkeypatch.setattr(modulo.esecuzioni, "termina", termina)
    monkeypatch.setattr(modulo, "PAUSA_CHIUSURA", 0)
    avvisi = []

    async def al_termine(id):
        avvisi.append(id)

    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Finto(risponditore), fonti=raccolta())
        esecutore.al_termine = al_termine
        esecutore.avvia("cli")
        await esecutore.attendi()
        assert esecutore.avanzamento is None
        monkeypatch.setattr(modulo.esecuzioni, "termina", vera)
        esecutore.avvia("cli")  # non dà GiaInCorso
        await esecutore.attendi()

    asyncio.run(prova())
    with sessioni() as s:
        assert [e.stato for e in s.scalars(select(Esecuzione).order_by(Esecuzione.id))] == [stato, "completata"]
    assert len(chiamate) == min(fallimenti + 1, 3)
    assert avvisi == ([1, 2] if stato == "completata" else [2])  # nessun avviso per un'esecuzione non registrata


def test_un_argomento_del_tipo_sbagliato_non_fa_fallire_l_esecuzione(sessioni):
    """Prima `argomento: [1]` faceva fallire l'esecuzione in `_argomenti`; ora il passo degli argomenti non riesce."""
    def sbagliato(sistema, messaggio, schema):
        if schema is prompt.SCHEMA_ARGOMENTI:
            return {"assegnazioni": [{"notizia": 0, "argomento": [1]}]}
        return risponditore(sistema, messaggio, schema)

    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")), provider=Finto(sbagliato))
    assert esecuzione.stato == "completata"
    assert [(n.titolo, n.argomento_id) for n in salvate] == [("sicurezza-alta", None)]


@pytest.mark.parametrize("schema", [prompt.SCHEMA_PREFILTRO, prompt.SCHEMA_VALUTAZIONE])
def test_login_rifiutato_ferma_l_esecuzione(sessioni, schema):
    """Doc 05, 4.5 punto 2: un login rifiutato vale per tutte le chiamate. Prima l'esecuzione falliva notizia
    per notizia (con un nuovo tentativo ciascuna) e finiva "completata" senza notizie."""
    def rifiuta(sistema, messaggio, schema_chiesto):
        if schema_chiesto is schema:
            raise LoginRifiutato("Claude Code ha rifiutato il login")
        return risponditore(sistema, messaggio, schema_chiesto)

    paper = [candidata(f"sicurezza-alta-{i}") for i in range(3)]
    esecuzione, _, salvate, _ = esegui(sessioni, raccolta(*paper), provider=Finto(rifiuta))
    assert (esecuzione.stato, esecuzione.motivo) == ("fallita", "Claude Code ha rifiutato il login")
    assert salvate == []


class ConVersione(Finto):
    """Finto con una versione, come Claude Code (decisione 45)."""

    nome = "claude-code"

    def __init__(self, risponditore, versione="2.1.316"):
        super().__init__(risponditore)
        self.versione = versione

    async def pronto(self):
        return self.versione


def prove_di_fumo(provider: Finto) -> int:
    return sum(messaggio == "[]" for _, messaggio in provider.chiamate)  # pre-filtro di un elenco vuoto


def test_versione_registrata_e_prova_di_fumo_solo_quando_cambia(sessioni):
    """Decisione 45: una chiamata breve quando la versione di Claude Code cambia, non a ogni esecuzione."""
    provider = ConVersione(risponditore)
    esecuzioni_di_fila(sessioni, raccolta(), provider, volte=2)
    assert prove_di_fumo(provider) == 1  # alla prima esecuzione non c'è una versione già provata
    provider.versione = "2.1.325"
    tutte = esecuzioni_di_fila(sessioni, raccolta(), provider, volte=1)
    assert prove_di_fumo(provider) == 2

    assert [e.stato for e, _ in tutte] == ["completata"] * 3
    versione = {"provider": "claude-code", "versione": "2.1.316", "precedente": None, "provata": True}
    assert [m["versione_llm"] for _, m in tutte] == [
        versione, versione, {**versione, "versione": "2.1.325", "precedente": "2.1.316"}]
    assert tutte[2][1]["token"]["prefiltro"]["ingresso"] > 0  # i token della prova contano


def test_prova_di_fumo_fallita_ferma_l_esecuzione_e_si_ripete(sessioni):
    def rotto(sistema, messaggio, schema):
        if messaggio == "[]":
            return {}  # forma inattesa: per esempio un campo della risposta che cambia nome
        return risponditore(sistema, messaggio, schema)

    provider = ConVersione(rotto)
    (prima, metriche), (seconda, _) = esecuzioni_di_fila(sessioni, raccolta(candidata("sicurezza-alta")), provider, volte=2)

    assert prima.stato == seconda.stato == "fallita"
    assert prima.motivo.startswith("Claude Code 2.1.316: la prova di funzionamento non è riuscita")
    assert len(provider.chiamate) == 2  # solo le due prove: nessuna notizia esaminata con Claude Code guasto
    assert metriche["versione_llm"]["provata"] is False


def test_ordine_delle_fasi_e_avanzamento_con_valutazioni_intrecciate(sessioni):
    """T-24: fase, fatti e totale letti dall'avanzamento a ogni chiamata del provider. Con un po' di latenza le
    60 valutazioni si intrecciano sulla sessione condivisa e si salvano tutte (P44)."""
    letti: list[tuple[str, int, int]] = []

    class ConLatenza(Finto):
        async def chiedi(self, **kwargs):
            a = esecutore.avanzamento
            letti.append((a.fase, a.fatti, a.totale))
            await asyncio.sleep(0.001)
            return await super().chiedi(**kwargs)

    async def raccogli(client, categorie, dal):
        a = esecutore.avanzamento
        letti.append((a.fase, a.fatti, a.totale))
        return [candidata(f"sicurezza-alta-{i}", i) for i in range(60)]

    with sessioni() as s:
        impostazioni.leggi(s).tetto_arxiv = 60
        s.commit()

    async def prova():
        esecutore.avvia("cli")
        await esecutore.attendi()

    esecutore = Esecutore(sessioni, fabbrica_provider=lambda nome: ConLatenza(risponditore),
                          fonti={"arxiv": SimpleNamespace(raccogli=raccogli)})
    asyncio.run(prova())

    # 60 paper: un giro di due blocchi da 30 insieme; le valutazioni partono tutte prima che una finisca;
    # 60 notizie mostrate: due blocchi di argomenti, uno dopo l'altro.
    assert letti == ([("raccolta", 0, 0)] + [("pre-filtro", 0, 2)] * 2 + [("valutazione", 0, 60)] * 60
                     + [("argomenti", 0, 2), ("argomenti", 1, 2)])
    assert esecutore.avanzamento is None
    with sessioni() as s:
        esecuzione = s.scalars(select(Esecuzione)).one()
        assert esecuzione.stato == "completata"
        assert len(s.scalars(select(Notizia)).all()) == 60
