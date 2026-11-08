"""Pannello di controllo (AMB-05): lo stato mostrato dalla finestrella. La finestra Tkinter si prova a mano."""

from gradiens.app.pannello import descrivi


def test_stato_mostrato():
    assert descrivi(None)[:2] == ("spento", "Gradiens è spento")
    acceso = {"prossima_esecuzione": "2026-11-09T07:00", "ultima_esecuzione": {"stato": "completata", "avviata_il": "2026-11-08T06:00:00"}}
    assert descrivi(acceso) == ("acceso", "Gradiens è acceso", "Prossima esecuzione: 09/11 alle 07:00.")
    assert descrivi({"prossima_esecuzione": None, "ultima_esecuzione": None})[2] == "La programmazione è in pausa."
    stato, titolo, _ = descrivi({"prossima_esecuzione": None, "ultima_esecuzione": {"stato": "in_corso", "avviata_il": "2026-11-08T06:00:00"}})
    assert (stato, titolo) == ("in_corso", "Esecuzione in corso")
