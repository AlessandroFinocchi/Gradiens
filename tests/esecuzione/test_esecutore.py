import asyncio
import json
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from gradiens.dati import impostazioni, interessi, notizie
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.dati.modelli import CategoriaArxiv, Esecuzione, Notizia
from gradiens.esecuzione import prompt
from gradiens.esecuzione.esecutore import Esecutore, GiaInCorso
from gradiens.fonti import Candidata
from gradiens.llm.base import QuotaEsaurita
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
    async def raccogli(client, categorie, dal):
        assert categorie == ["cs.CR"]
        return list(candidate)
    return raccogli


def risponditore(sistema, messaggio, schema):
    """Pre-filtro: passano i titoli con "sicurezza". Valutazione: "alta" 90, altrimenti 30."""
    if schema is prompt.SCHEMA_PREFILTRO:
        voci = json.loads(messaggio)
        return {"pertinenti": [v["id"] for v in voci if "sicurezza" in v["titolo"]]}
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
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda nome: finto, raccogli_arxiv=raccogli)
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
    a = metriche["arxiv"]
    assert (a["esaminate"], a["scartate_prefiltro"], a["scartate_valutazione"], a["mostrate"]) == (3, 1, 1, 1)
    assert metriche["token"]["prefiltro"]["ingresso"] > 0
    with sessioni() as s:  # tutte le notizie esaminate sono ora nel registro (ESE-07)
        assert len(notizie.gia_viste(s, [f"https://arxiv.org/abs/{n}" for n in ("sicurezza-alta", "sicurezza-bassa", "cucina")])) == 3
    # Pre-filtro: una sola chiamata a blocchi. La parte fissa (interessi) sta nel prompt di sistema.
    assert sum("pre-filtro" in sistema for sistema, _ in finto.chiamate) == 1
    assert all("attacchi informatici" in sistema for sistema, _ in finto.chiamate)


def test_tetto_arxiv_elabora_solo_i_piu_recenti(sessioni):
    _, metriche, salvate, _ = esegui(sessioni, raccolta(
        candidata("sicurezza-alta-vecchia", ore_fa=5), candidata("sicurezza-alta-recente", ore_fa=1)), tetto_arxiv=1)
    assert [n.titolo for n in salvate] == ["sicurezza-alta-recente"]
    assert metriche["arxiv"]["oltre_tetto"] == 1


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
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Finto(risponditore), raccogli_arxiv=raccolta())
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
    assert "categoria arXiv" in esecuzione.motivo


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
    assert metriche["arxiv"]["errori"] == 1
    with sessioni() as s:  # il blocco fallito si riprova alla prossima esecuzione
        assert notizie.gia_viste(s, ["https://arxiv.org/abs/sicurezza-rotto"]) == set()


def test_spegnimento_durante_l_esecuzione_la_registra_come_interrotta(sessioni):
    class Lento:
        nome = "lento"

        async def chiedi(self, **_):
            await asyncio.sleep(60)

    async def prova():
        esecutore = Esecutore(sessioni, fabbrica_provider=lambda n: Lento(),
                              raccogli_arxiv=raccolta(candidata("sicurezza-alta")))
        esecutore.avvia("cli")
        await asyncio.sleep(0.1)
        await esecutore.ferma()
        assert esecutore.avanzamento is None

    asyncio.run(prova())
    with sessioni() as s:
        esecuzione = s.scalars(select(Esecuzione)).one()
        assert esecuzione.stato == "interrotta" and "spento" in esecuzione.motivo
