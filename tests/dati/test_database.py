import pytest

from gradiens.dati import impostazioni
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra


@pytest.fixture
def sessioni(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    return fabbrica_sessioni(motore)


def test_database_nuovo_ha_le_impostazioni_predefinite(sessioni):
    with sessioni() as s:
        assert impostazioni.leggi(s).tema == "auto"


def test_migrare_di_nuovo_non_perde_i_dati(tmp_path, sessioni):
    with sessioni() as s:
        impostazioni.salva_tema(s, "dark")
    migra(crea_motore(tmp_path / "prova.db"))
    with sessioni() as s:
        assert impostazioni.leggi(s).tema == "dark"


def test_tema_non_valido_rifiutato(sessioni):
    with sessioni() as s, pytest.raises(ValueError):
        impostazioni.salva_tema(s, "viola")
