import sqlite3
from contextlib import closing

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
            "INSERT INTO notizie (id, tipo, url, fonte, titolo, riassunto, pubblicata_il, data_incerta,"
            " scoperta_il, cuore)"
            " VALUES (1, 'sito', 'https://a.it/1', 'a.it', 'T', 'R', '2026-11-06', 0, '2026-11-06', 1)"
        )
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


@pytest.mark.parametrize(("prima", "dopo"), [(None, 30), (50, 30), (10, 30), (20, 20)])
def test_il_tetto_arxiv_predefinito_e_30(tmp_path, prima, dopo):
    """ADR 0010, decisione 9: database nuovo, vecchio predefinito (50) e tetto di prima (10) passano a 30;
    un tetto scelto diverso resta com'è."""
    motore = crea_motore(tmp_path / "prova.db")
    if prima is not None:
        config = Config()
        config.set_main_option("script_location", str(CARTELLA_MIGRAZIONI))
        with motore.begin() as c:
            config.attributes["connection"] = c
            command.upgrade(config, "0011")
            c.exec_driver_sql("UPDATE impostazioni SET tetto_arxiv = ?", (prima,))
    migra(motore)
    with fabbrica_sessioni(motore)() as s:
        assert impostazioni.leggi(s).tetto_arxiv == dopo


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
    # closing: il `with` di sqlite3 fa commit o rollback, ma non chiude la connessione.
    with closing(sqlite3.connect(copia)) as c:  # la copia è il database prima della migrazione, con i dati
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


TABELLE = (
    "interessi",
    "siti",
    "esecuzioni",
    "argomenti",
    "notizie",
    "pertinenze",
    "proposte",
    "notizie_viste",
    "canali_youtube",
    "categorie_arxiv",
)


def test_la_migrazione_dei_siti_non_perde_dati_e_si_ripete_senza_errori(tmp_path):
    """T-01 (doc. 02, decisione 26): la 0013 (ADR 0011, "coperto fino a" in `siti`) su un database alla 0012 con
    dati in tutte le tabelle: non perde niente, i siti partono senza copertura e una seconda volta non fa niente."""
    import json

    motore = crea_motore(tmp_path / "gradiens.db")
    config = Config()
    config.set_main_option("script_location", str(CARTELLA_MIGRAZIONI))
    profili = [
        json.dumps(
            {
                "url": f"https://sito-{i}.it/",
                "strategie": ["feed"],
                "esclusi": ["/offerte/"],
                "note": "profilo con àccenti",
            },
            ensure_ascii=False,
        )
        for i in range(13)
    ]
    with motore.begin() as c:
        config.attributes["connection"] = c
        command.upgrade(config, "0012")
        sql = c.exec_driver_sql
        sql("INSERT INTO interessi (id, nome, descrizione) VALUES (1, 'Sicurezza', 'attacchi'), (2, 'Corsa', 'gare')")
        for i, profilo in enumerate(profili, start=1):
            sql(
                "INSERT INTO siti (id, url, profilo, profilo_precedente, stato, dettaglio, guasti_consecutivi)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (i, f"https://sito-{i - 1}.it/", profilo, profilo if i == 1 else None, "ok", "1 articolo", i % 3),
            )
        sql(
            "INSERT INTO esecuzioni (id, avviata_il, avviata_da, stato, metriche)"
            " VALUES (1, '2026-11-10 07:00:00', 'programmazione', 'completata', '{}')"
        )
        sql("INSERT INTO argomenti (id, nome, creato_il) VALUES (1, 'Attacco alla ASL', '2026-11-10 07:05:00')")
        for n in range(1, 6):
            sql(
                "INSERT INTO notizie (id, tipo, url, fonte, titolo, riassunto, pubblicata_il, data_incerta,"
                " scoperta_il, cuore, esecuzione_id, argomento_id)"
                " VALUES (?, 'sito', ?, 'sito-0.it', 'T', 'R', '2026-11-10', 0, '2026-11-10', ?, 1, ?)",
                (n, f"https://sito-0.it/{n}", n == 1, 1 if n < 3 else None),
            )
            sql("INSERT INTO pertinenze VALUES (?, 1, 80), (?, 2, 10)", (n, n))
            sql("INSERT INTO notizie_viste VALUES (?, '2026-11-10')", (f"https://sito-0.it/{n}",))
        sql("INSERT INTO notizie_viste VALUES ('https://sito-1.it/scartata', '2026-11-10')")
        sql("INSERT INTO proposte (interesse_id, testo, notizie, creata_il) VALUES (1, 'ransomware', 3, '2026-11-10')")
        sql("INSERT INTO canali_youtube VALUES ('UCaaaaaaaaaaaaaaaaaaaaaa', 'Lab')")
        sql("INSERT INTO categorie_arxiv VALUES ('cs.CR', 'Crittografia e Sicurezza')")

    def stato_dei_dati():
        with motore.connect() as c:
            return (
                {t: c.exec_driver_sql(f"SELECT COUNT(*) FROM {t}").scalar() for t in TABELLE},
                c.exec_driver_sql(
                    "SELECT id, url, profilo, profilo_precedente, stato, dettaglio, guasti_consecutivi"
                    " FROM siti ORDER BY id"
                ).all(),
            )

    prima = stato_dei_dati()
    migra(motore)
    assert stato_dei_dati() == prima and prima[0]["siti"] == 13
    with motore.connect() as c:
        assert c.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() >= "0013"
        colonne = [r[1] for r in c.exec_driver_sql("PRAGMA table_info(siti)")]
        assert {"coperto_fino_a", "coperto_con"} <= set(colonne)
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM siti WHERE coperto_fino_a IS NOT NULL OR coperto_con IS NOT NULL"
            ).scalar()
            == 0
        )  # prima raccolta: finestra intera
        assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    assert len(list((tmp_path / "backup").glob("gradiens-*-migrazione.db"))) == 1

    migra(motore)  # già aggiornato: niente errori e nessuna copia in più
    assert stato_dei_dati() == prima
    assert len(list((tmp_path / "backup").glob("gradiens-*-migrazione.db"))) == 1


def test_la_migrazione_dell_accesso_da_fuori_casa_lo_lascia_spento_e_non_tocca_il_resto(tmp_path):
    """0014 (ADR 0013): due colonne nuove in `impostazioni`, con `ADD COLUMN`, su un database alla 0013 con dati."""
    motore = crea_motore(tmp_path / "gradiens.db")
    config = Config()
    config.set_main_option("script_location", str(CARTELLA_MIGRAZIONI))
    with motore.begin() as c:
        config.attributes["connection"] = c
        command.upgrade(config, "0013")
        c.exec_driver_sql(
            "UPDATE impostazioni SET tema = 'dark', soglia = 75, telegram_chat_id = 4242, configurazione_completata = 1"
        )
        c.exec_driver_sql("INSERT INTO interessi (id, nome, descrizione) VALUES (1, 'Sicurezza', 'attacchi')")
    migra(motore)
    migra(motore)  # una seconda volta non fa niente
    with fabbrica_sessioni(motore)() as s:
        imp = impostazioni.leggi(s)
        assert (imp.tema, imp.soglia, imp.telegram_chat_id, imp.configurazione_completata) == ("dark", 75, 4242, True)
        assert (imp.accesso_remoto, imp.indirizzo_remoto) == (False, None)
        assert imp.sidebar_fissa is False  # 0015, sempre con `ADD COLUMN`
    with motore.connect() as c:
        assert c.exec_driver_sql("SELECT COUNT(*) FROM interessi").scalar() == 1
