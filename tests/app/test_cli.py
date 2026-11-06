from gradiens.app import cli


def test_stato_senza_servizio(conf, capsys):
    assert cli.stato(conf) == 1
    assert "non è in esecuzione" in capsys.readouterr().out


def test_spegni_senza_servizio(conf, capsys):
    assert cli.spegni(conf) == 0
    assert "non è in esecuzione" in capsys.readouterr().out
