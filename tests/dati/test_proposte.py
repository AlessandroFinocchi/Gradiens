from datetime import timedelta

import pytest

from gradiens.dashboard.comune import evidenzia
from gradiens.dati import impostazioni, interessi, notizie, proposte
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Interesse, Notizia, Pertinenza, Proposta
from gradiens.dati.notizie import adesso


@pytest.fixture
def s(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    with fabbrica_sessioni(motore)() as sessione:
        yield sessione


def con_cuore(s, url, punteggi):
    n = Notizia(tipo="sito", url=url, fonte="e.org", titolo=url, riassunto="r", pubblicata_il=adesso(),
                scoperta_il=adesso(), pertinenze=[Pertinenza(interesse_id=i, punteggio=p) for i, p in punteggi])
    s.add(n)
    s.commit()
    notizie.imposta_cuore(s, n.id, True)
    return n


def test_raffinamento_dopo_3_cuori_nuovi_e_una_proposta_alla_volta(s):
    a = interessi.aggiungi(s, "Sicurezza", "attacchi")
    con_cuore(s, "1", [(a.id, 80)])
    con_cuore(s, "2", [(a.id, 70)])
    con_cuore(s, "3", [(a.id, 40)])  # sotto la soglia per questo interesse: non conta
    assert proposte.da_raffinare(s, 60) == []
    con_cuore(s, "4", [(a.id, 90)])
    [(interesse, cuori)] = proposte.da_raffinare(s, 60)
    assert [n.url for n in cuori] == ["4", "2", "1"]  # dal cuore più recente
    proposte.registra_raffinamento(s, interesse, "Soprattutto ransomware.", len(cuori))
    assert proposte.da_raffinare(s, 60) == []  # proposta in sospeso, e i cuori ripartono da zero
    proposte.scarta(s, proposte.pendenti(s)[0].id)
    assert proposte.da_raffinare(s, 60) == []  # servono 3 cuori nuovi dopo l'ultima proposta


def test_approvare_cambia_il_raffinamento_ma_non_la_descrizione(s):
    a = interessi.aggiungi(s, "Sicurezza", "attacchi")
    proposte.registra_raffinamento(s, a, "Soprattutto ransomware.", 3)
    proposte.registra_raffinamento(s, a, "", 3)  # niente da aggiungere: nessuna proposta
    [p] = proposte.pendenti(s)
    with pytest.raises(ImpostazioneNonValida):
        proposte.approva(s, p.id, testo="  ")
    proposte.approva(s, p.id, testo="Ransomware nella sanità.")  # versione modificata
    a = s.get(Interesse, a.id)
    assert (a.descrizione, a.raffinamento) == ("attacchi", "Ransomware nella sanità.")
    assert proposte.pendenti(s) == []


def test_nuovo_interesse_dai_cuori_senza_interesse(s):
    a = interessi.aggiungi(s, "Sicurezza", "attacchi")
    for url in ("1", "2"):
        con_cuore(s, url, [(a.id, 30)])
    con_cuore(s, "pertinente", [(a.id, 90)])
    assert proposte.senza_interesse(s, 60) == []
    con_cuore(s, "3", [])  # es. il suo interesse è stato eliminato
    assert len(proposte.senza_interesse(s, 60)) == 3
    proposte.registra_interesse(s, "Corsa", "Allenamento per la mezza maratona.", 3)
    assert proposte.senza_interesse(s, 60) == []
    [p] = proposte.pendenti(s)
    proposte.approva(s, p.id, nome="Corsa e salute", testo="Allenamento e prevenzione.")
    assert [i.nome for i in interessi.elenca(s)] == ["Corsa e salute", "Sicurezza"]
    assert s.query(Proposta).count() == 0


def test_parole_nuove_evidenziate():
    assert evidenzia("Agenti con strumenti.", "agenti con strumenti e cache dei prompt") == [
        ("agenti con strumenti", False), ("e cache dei prompt", True)]  # punteggiatura e maiuscole non contano
