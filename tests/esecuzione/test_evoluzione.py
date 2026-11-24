"""Riassunto dell'evoluzione di un argomento (decisione 72): racconto in ordine di tempo, salvato sull'argomento."""

import asyncio
import json
from datetime import timedelta

import pytest

from gradiens.dati import argomenti
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.dati.modelli import Argomento, Notizia
from gradiens.dati.notizie import adesso
from gradiens.esecuzione import evoluzione
from gradiens.esecuzione.evoluzione import RiassuntoNonDisponibile, riassumi
from gradiens.llm.base import QuotaEsaurita
from gradiens.llm.finto import Finto


@pytest.fixture
def s(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    with fabbrica_sessioni(motore)() as sessione:
        yield sessione


def notizia(s, titolo, argomento, giorni_fa=1):
    quando = adesso() - timedelta(days=giorni_fa)
    s.add(
        Notizia(
            tipo="sito",
            url=f"https://e.org/{titolo}",
            fonte="e.org",
            titolo=titolo,
            riassunto="r",
            pubblicata_il=quando,
            scoperta_il=quando,
            argomento=argomento,
        )
    )
    s.commit()


def _riassumi(s, id, provider):
    asyncio.run(riassumi(s, id, lambda nome: provider))


def test_racconto_dalla_notizia_piu_vecchia_e_salvato(s):
    a = argomenti.crea(s, "Attacco ASL")
    notizia(s, "recente", a, giorni_fa=1)
    notizia(s, "vecchia", a, giorni_fa=5)
    finto = Finto(lambda sistema, messaggio, schema: {"evoluzione": " Inizio.\n\nOggi. "})
    _riassumi(s, a.id, finto)
    inviato = json.loads(finto.chiamate[0][1])
    assert inviato["argomento"] == "Attacco ASL" and [n["titolo"] for n in inviato["notizie"]] == ["vecchia", "recente"]
    assert "racconto_precedente" not in inviato  # la prima volta non c'è
    a = s.get(Argomento, a.id)
    assert a.evoluzione == "Inizio.\n\nOggi." and a.evoluzione_notizie == 2
    r = argomenti.riassunto(s, a.id, None)
    assert not r.evoluzione_vecchia
    notizia(s, "nuova", a, giorni_fa=0)  # arriva dopo il riassunto
    assert argomenti.riassunto(s, a.id, None).evoluzione_vecchia

    # Aggiornando, l'LLM rilegge il racconto precedente: l'inizio della storia resta anche se le notizie scadono.
    _riassumi(s, a.id, finto)
    precedente = json.loads(finto.chiamate[1][1])["racconto_precedente"]
    assert precedente == {"scritto_il": adesso().date().isoformat(), "testo": "Inizio.\n\nOggi."}


def test_troppe_notizie_si_leggono_solo_le_piu_recenti(s, monkeypatch):
    monkeypatch.setattr(evoluzione, "MASSIMO_NOTIZIE", 2)
    a = argomenti.crea(s, "Lungo")
    for giorni in (3, 2, 1):
        notizia(s, f"n{giorni}", a, giorni_fa=giorni)
    finto = Finto(lambda sistema, messaggio, schema: {"evoluzione": "Testo."})
    _riassumi(s, a.id, finto)
    assert [n["titolo"] for n in json.loads(finto.chiamate[0][1])["notizie"]] == ["n2", "n1"]
    assert s.get(Argomento, a.id).evoluzione_notizie == 3  # conta tutte, così non risulta subito da aggiornare


def test_errori_per_l_utente_e_niente_salvato(s):
    a = argomenti.crea(s, "Evento")
    notizia(s, "sola", a)
    with pytest.raises(RiassuntoNonDisponibile, match="almeno un'altra notizia"):
        _riassumi(s, a.id, Finto(lambda *_: {"evoluzione": "x"}))
    notizia(s, "seconda", a)

    def quota(*_):
        raise QuotaEsaurita("Quota dell'abbonamento esaurita.")

    with pytest.raises(RiassuntoNonDisponibile, match="Quota"):
        _riassumi(s, a.id, Finto(quota))
    with pytest.raises(RiassuntoNonDisponibile, match="senza testo"):
        _riassumi(s, a.id, Finto(lambda *_: {"evoluzione": "  "}))
    assert s.get(Argomento, a.id).evoluzione is None
