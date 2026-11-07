from gradiens.app import cli


def test_stato_senza_servizio(conf, capsys):
    assert cli.stato(conf) == 1
    assert "non è in esecuzione" in capsys.readouterr().out


def test_stato_mostra_la_prossima_esecuzione_o_la_pausa(conf, monkeypatch, capsys):
    stato = {"avviato_alle": "2026-11-07T08:00:00", "prossima_esecuzione": "2026-11-08T07:00",
             "ultima_esecuzione": {"stato": "completata", "avviata_il": "2026-11-07T06:00:00"}}
    monkeypatch.setattr(cli, "leggi_stato", lambda c: stato)
    assert cli.stato(conf) == 0
    uscita = capsys.readouterr().out
    assert "Prossima esecuzione programmata: 08/11 alle 07:00" in uscita and "Ultima esecuzione: completata" in uscita
    stato["prossima_esecuzione"] = None
    cli.stato(conf)
    assert "Programmazione in pausa." in capsys.readouterr().out


def test_spegni_senza_servizio(conf, capsys):
    assert cli.spegni(conf) == 0
    assert "non è in esecuzione" in capsys.readouterr().out


def test_esegui_quando_il_servizio_smette_di_rispondere(conf, monkeypatch, capsys):
    import httpx

    monkeypatch.setattr(cli, "leggi_stato", lambda c: {"avviato_alle": "x"})
    monkeypatch.setattr(cli.time, "sleep", lambda s: None)
    monkeypatch.setattr(cli.httpx, "post", lambda *a, **k: httpx.Response(200, json={"esecuzione_id": 1}, request=httpx.Request("POST", "http://x")))

    def non_risponde(*a, **k):
        raise httpx.ConnectError("rifiutata")

    monkeypatch.setattr(cli.httpx, "get", non_risponde)
    assert cli.esegui(conf) == 1
    assert "non risponde più" in capsys.readouterr().err
