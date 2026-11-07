from datetime import UTC, datetime, timedelta

import pytest

from gradiens.dati import esecuzioni, impostazioni
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.esecuzione.esecutore import GiaInCorso
from gradiens.esecuzione.programmatore import Programmatore


class EsecutoreFinto:
    def __init__(self):
        self.avviate = 0
        self.occupato = False

    def avvia(self, avviata_da: str) -> int:
        assert avviata_da == "programmazione"
        if self.occupato:
            raise GiaInCorso("Esecuzione già in corso.")
        self.avviate += 1
        return self.avviate


@pytest.fixture
def sessioni(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    return fabbrica_sessioni(motore)


def programmatore(sessioni, *ore: datetime):
    """Programmatore con un orologio che restituisce le ore date, una per controllo."""
    orologio = iter(ore)
    esecutore = EsecutoreFinto()
    return Programmatore(sessioni, esecutore, adesso=lambda: next(orologio)), esecutore


def ora(giorno: int, ore: int, minuti: int = 0) -> datetime:
    return datetime(2026, 11, giorno, ore, minuti)


def test_parte_quando_si_supera_l_orario_una_volta_al_giorno(sessioni):
    p, e = programmatore(sessioni, ora(7, 6, 0), ora(7, 6, 59), ora(7, 7, 0), ora(7, 7, 1), ora(8, 7, 0))
    p.controlla()
    p.controlla()
    assert e.avviate == 0
    p.controlla()
    p.controlla()
    assert e.avviate == 1
    p.controlla()  # il giorno dopo
    assert e.avviate == 2


def test_pc_sospeso_durante_l_orario(sessioni):
    p, e = programmatore(sessioni, ora(7, 1, 0), ora(7, 9, 30))  # sospeso dall'1 alle 9:30
    p.controlla()
    p.controlla()
    assert e.avviate == 1


def test_recupero_all_avvio_se_da_allora_non_e_partita_nessuna_esecuzione(sessioni):
    p, e = programmatore(sessioni, ora(7, 9, 0), ora(7, 9, 1))
    p.controlla()
    p.controlla()
    assert e.avviate == 1  # una sola volta


def test_niente_recupero_se_un_esecuzione_e_partita_dopo_l_orario(sessioni):
    with sessioni() as s:
        partita = esecuzioni.inizia(s, "cli")
        partita.avviata_il = ora(7, 8, 0).astimezone(UTC).replace(tzinfo=None)  # alle 8 locali
        s.commit()
    p, e = programmatore(sessioni, ora(7, 9, 0))
    p.controlla()
    assert e.avviate == 0


def test_niente_recupero_prima_dell_orario(sessioni):
    p, e = programmatore(sessioni, ora(7, 6, 0))
    p.controlla()
    assert e.avviate == 0


def test_in_pausa_non_parte_e_non_recupera(sessioni):
    with sessioni() as s:
        impostazioni.salva_esecuzione(s, 60, 7, in_pausa=True)
    p, e = programmatore(sessioni, ora(7, 9, 0), ora(8, 6, 0), ora(8, 7, 0))
    for _ in range(3):
        p.controlla()
    assert e.avviate == 0
    assert p.prossima() is None


def test_orario_spostato_nel_passato_vale_dal_giorno_dopo(sessioni):
    with sessioni() as s:
        impostazioni.salva_esecuzione(s, 60, 7, orario="22:00")
    p, e = programmatore(sessioni, ora(7, 9, 59), ora(7, 10, 0), ora(8, 6, 30))
    p.controlla()  # avvio prima delle 22: niente recupero
    with sessioni() as s:
        impostazioni.salva_esecuzione(s, 60, 7, orario="06:30")
    p.controlla()  # le 6:30 di oggi erano già passate prima dell'ultimo controllo
    assert e.avviate == 0
    p.controlla()
    assert e.avviate == 1


def test_esecuzione_gia_in_corso_all_orario(sessioni):
    p, e = programmatore(sessioni, ora(7, 6, 59), ora(7, 7, 0))
    e.occupato = True
    p.controlla()
    p.controlla()  # GiaInCorso non deve uscire dal controllo
    assert e.avviate == 0


def test_prossima_esecuzione(sessioni):
    p, _ = programmatore(sessioni, ora(7, 6, 0), ora(7, 8, 0))
    assert p.prossima() == ora(7, 7, 0)
    assert p.prossima() == ora(8, 7, 0) and ora(8, 7, 0) - ora(7, 7, 0) == timedelta(days=1)
