from datetime import timedelta

import pytest

from gradiens.dati import argomenti, esecuzioni, interessi, notizie
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Argomento, Notizia, Pertinenza
from gradiens.dati.notizie import adesso


@pytest.fixture
def s(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    with fabbrica_sessioni(motore)() as sessione:
        yield sessione


def notizia(s, url, argomento, giorni_fa=1, cuore=False, esecuzione_id=None):
    a = interessi.elenca(s)[0] if interessi.elenca(s) else interessi.aggiungi(s, "A", "a")
    quando = adesso() - timedelta(days=giorni_fa)
    n = Notizia(tipo="sito", url=url, fonte="e.org", titolo=url, riassunto="r", pubblicata_il=quando, scoperta_il=quando,
                cuore=cuore, argomento=argomento, esecuzione_id=esecuzione_id,
                pertinenze=[Pertinenza(interesse_id=a.id, punteggio=80)])
    s.add(n)
    s.commit()
    return n


def test_timeline_solo_con_almeno_2_notizie_le_piu_recenti_prima(s):
    e = esecuzioni.inizia(s, "cli")
    vecchio, recente, solo = argomenti.crea(s, "Vecchio"), argomenti.crea(s, "Recente"), argomenti.crea(s, "Solo")
    notizia(s, "v1", vecchio, giorni_fa=5)
    notizia(s, "v2", vecchio, giorni_fa=4, cuore=True)
    notizia(s, "r1", recente, giorni_fa=3)
    notizia(s, "r2", recente, giorni_fa=1, esecuzione_id=e.id)
    notizia(s, "s1", solo)
    elenco = argomenti.timeline(s, e.id)
    assert [r.argomento.nome for r in elenco] == ["Recente", "Vecchio"]  # "Solo" ha una notizia (UI-09)
    assert (elenco[0].notizie, elenco[0].nuove, elenco[1].in_archivio) == (2, 1, 1)
    assert argomenti.riassunto(s, solo.id, e.id).notizie == 1  # la sua pagina si apre comunque


def test_rinomina_unisci_elimina(s):
    a, b = argomenti.crea(s, "A"), argomenti.crea(s, "B")
    notizia(s, "a1", a)
    notizia(s, "b1", b)
    with pytest.raises(ImpostazioneNonValida):
        argomenti.rinomina(s, a.id, "   ")
    argomenti.rinomina(s, a.id, "Attacco alla ASL")
    with pytest.raises(ImpostazioneNonValida):
        argomenti.unisci(s, a.id, a.id)
    argomenti.unisci(s, b.id, a.id)
    assert s.get(Argomento, b.id) is None and len(s.get(Argomento, a.id).notizie) == 2
    argomenti.elimina(s, a.id)
    assert s.query(Argomento).count() == 0
    assert all(n.argomento_id is None for n in s.query(Notizia))  # le notizie restano


def test_argomento_senza_notizie_si_cancella_con_le_notizie_scadute(s):
    """ESE-10."""
    vuoto, vivo = argomenti.crea(s, "Vuoto"), argomenti.crea(s, "Vivo")
    notizia(s, "vecchia", vuoto, giorni_fa=9)
    notizia(s, "recente", vivo)
    notizie.cancella_scadute(s)
    assert [a.nome for a in s.query(Argomento)] == ["Vivo"]


def test_argomenti_per_il_prompt_solo_recenti(s):
    """ADR 0008: si mandano a Claude solo gli argomenti aggiornati negli ultimi 30 giorni."""
    recente, antico = argomenti.crea(s, "Recente"), argomenti.crea(s, "Antico")
    notizia(s, "r", recente)
    notizia(s, "a", antico, giorni_fa=40, cuore=True)
    assert [a.nome for a in argomenti.per_prompt(s)] == ["Recente"]
