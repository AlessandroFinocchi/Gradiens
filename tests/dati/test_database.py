import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from gradiens.dati import impostazioni
from gradiens.dati.database import CARTELLA_MIGRAZIONI, copia_giornaliera, crea_motore, fabbrica_sessioni, migra


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


def test_le_migrazioni_non_cancellano_le_pertinenze(tmp_path):
    # La 0009 ricrea la tabella notizie: con le chiavi esterne attive il DROP cancellava a cascata le pertinenze.
    motore = crea_motore(tmp_path / "prova.db")
    config = Config()
    config.set_main_option("script_location", str(CARTELLA_MIGRAZIONI))
    with motore.begin() as c:
        config.attributes["connection"] = c
        command.upgrade(config, "0008")
        c.exec_driver_sql("INSERT INTO interessi (id, nome, descrizione) VALUES (1, 'AI', 'AI')")
        c.exec_driver_sql(
            "INSERT INTO notizie (id, tipo, url, fonte, titolo, riassunto, pubblicata_il, data_incerta, scoperta_il, cuore)"
            " VALUES (1, 'sito', 'https://a.it/1', 'a.it', 'T', 'R', '2026-11-06', 0, '2026-11-06', 1)")
        c.exec_driver_sql("INSERT INTO pertinenze VALUES (1, 1, 80)")
    migra(motore)
    with motore.connect() as c:
        assert c.exec_driver_sql("SELECT punteggio FROM pertinenze").scalars().all() == [80]
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1  # riattivate dopo le migrazioni


@pytest.mark.parametrize("con_interessi", [True, False])
def test_un_gradiens_gia_in_uso_salta_la_configurazione_iniziale(tmp_path, con_interessi):
    motore = crea_motore(tmp_path / "prova.db")
    config = Config()
    config.set_main_option("script_location", str(CARTELLA_MIGRAZIONI))
    with motore.begin() as c:
        config.attributes["connection"] = c
        command.upgrade(config, "0010")
        if con_interessi:
            c.exec_driver_sql("INSERT INTO interessi (id, nome, descrizione) VALUES (1, 'AI', 'AI')")
    migra(motore)
    with fabbrica_sessioni(motore)() as s:
        assert impostazioni.leggi(s).configurazione_completata is con_interessi


def test_copia_prima_di_una_migrazione_ma_non_su_un_database_nuovo(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)  # database nuovo: niente da salvare
    assert not (tmp_path / "backup").exists()

    vecchio = crea_motore(tmp_path / "vecchio" / "gradiens.db")
    config = Config()
    config.set_main_option("script_location", str(CARTELLA_MIGRAZIONI))
    with vecchio.begin() as c:
        config.attributes["connection"] = c
        command.upgrade(config, "0010")
        c.exec_driver_sql("INSERT INTO interessi (id, nome, descrizione) VALUES (1, 'AI', 'AI')")
    migra(vecchio)
    [copia] = (tmp_path / "vecchio" / "backup").glob("gradiens-*-migrazione.db")
    with sqlite3.connect(copia) as c:  # la copia è il database prima della migrazione, con i dati
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0010",)
        assert c.execute("SELECT nome FROM interessi").fetchall() == [("AI",)]
    migra(vecchio)  # già aggiornato: nessuna copia in più
    assert len(list((tmp_path / "vecchio" / "backup").iterdir())) == 1


def test_copie_giornaliere_una_al_giorno_e_al_massimo_sette(tmp_path):
    motore = crea_motore(tmp_path / "gradiens.db")
    migra(motore)
    cartella = tmp_path / "backup"
    cartella.mkdir()
    for giorno in range(1, 10):  # copie di giorni passati
        (cartella / f"gradiens-202610{giorno:02d}-070000-giornaliera.db").write_bytes(b"")
    assert copia_giornaliera(motore) is not None
    assert copia_giornaliera(motore) is None  # stesso giorno, anche dopo un riavvio
    rimaste = sorted(p.name for p in cartella.glob("*-giornaliera.db"))
    assert len(rimaste) == 7 and rimaste[0] == "gradiens-20261004-070000-giornaliera.db"  # via le più vecchie
