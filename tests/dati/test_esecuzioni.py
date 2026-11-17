"""T-30: le chiavi delle metriche salvate (ESE-11) e chi le legge."""

import json
from dataclasses import asdict, fields
from types import SimpleNamespace

import pytest

from gradiens.app import cli
from gradiens.dati import esecuzioni
from gradiens.esecuzione.metriche import Contatori, Metriche
from gradiens.telegram import messaggi

# Campi interi di `Contatori` che `riepilogo` non somma nei totali: oggi nessuno (con la 6b-1, se accettata,
# `prefiltrate` e `promosse`).
DA_NON_SOMMARE: set[str] = set()

# Una metrica salvata prima della fetta 4b: senza `scartate_prefiltro`, `oltre_tetto` e altre chiavi.
VECCHIA = {
    "durata_s": 3.0,
    "fonti": {"arxiv": {"esaminate": 2, "mostrate": 1, "errori": 0}},
    "token": {"prefiltro": {"ingresso": 10, "uscita": 1}},
}


def test_le_chiavi_delle_metriche_e_chi_le_legge():
    """Chi toglie o rinomina una chiave rompe le metriche già salvate: qui si cambia solo per aggiunta."""
    assert list(asdict(Contatori())) == [
        "raccolta_s",
        "esaminate",
        "scartate_prefiltro",
        "oltre_tetto",
        "escluse",
        "senza_contenuto",
        "scartate_valutazione",
        "mostrate",
        "errori",
        "stati",
        "problemi",
        "notizie_escluse",
    ]
    assert Metriche().token == {"prefiltro": {"ingresso": 0, "uscita": 0}, "elaborazione": {"ingresso": 0, "uscita": 0}}


def test_i_totali_sommano_i_contatori_interi():
    interi = {f.name for f in fields(Contatori) if f.type in (int, "int")}
    assert set(esecuzioni.CONTATORI) <= interi
    assert interi - set(esecuzioni.CONTATORI) == DA_NON_SOMMARE


def test_una_metrica_vecchia_si_legge_tranne_che_nella_cli():
    r = esecuzioni.riepilogo(SimpleNamespace(metriche=json.dumps(VECCHIA)))
    assert (r["totali"]["esaminate"], r["totali"]["oltre_tetto"], r["totali"]["token"]) == (2, 0, 11)
    assert messaggi.riga_metriche(r).startswith("2 esaminate · 1 mostrate")
    with pytest.raises(KeyError):  # vedi S-28: la CLI indicizza chiavi che le metriche vecchie non hanno
        cli._riepilogo({"stato": "completata", "metriche": VECCHIA})
