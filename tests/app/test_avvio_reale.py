from gradiens.app import cli


def test_avvia_stato_spegni_con_un_processo_vero(conf, monkeypatch):
    # Il processo staccato legge la configurazione dall'ambiente, che prevale sul .env vero.
    monkeypatch.setenv("GRADIENS_PORTA", str(conf.porta))
    monkeypatch.setenv("GRADIENS_CARTELLA_DATI", str(conf.cartella_dati))
    try:
        assert cli.avvia(conf, primo_piano=False) == 0
        assert cli.stato(conf) == 0
        assert cli.avvia(conf, primo_piano=False) == 0  # già in esecuzione: nessun secondo processo
        assert conf.percorso_database.exists()
    finally:
        assert cli.spegni(conf) == 0
    assert cli.stato(conf) == 1
