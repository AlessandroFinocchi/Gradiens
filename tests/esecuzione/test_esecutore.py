import asyncio
import json
from types import SimpleNamespace
from datetime import timedelta

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
from gradiens.llm.base import ErroreLLM, QuotaEsaurita
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
                "riassunto": "R", "titolo_it": ""}

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
    from gradiens.esecuzione import esecutore as modulo
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

    async def raccogli(client, profilo, dal):
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
        return risponditore(sistema, messaggio, schema)

    esecuzione, _, _, _ = esegui(sessioni, raccolta(candidata("sicurezza-alta")), provider=Finto(con_proposta))
    assert esecuzione.stato == "completata"
    with sessioni() as s:
        [p] = s.scalars(select(Proposta)).all()
        assert (p.interesse_id, p.testo, p.notizie) == (1, "Soprattutto ransomware nella sanità.", 3)

