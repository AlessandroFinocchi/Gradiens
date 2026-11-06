from datetime import datetime

from gradiens.fonti.siti.date import da_iso, da_testo, da_url, nella_finestra
from gradiens.fonti.siti.indirizzi import normalizza, sembra_articolo
from gradiens.fonti.siti.profilo import Profilo, perimetro_di


def test_normalizza_protocollo_mancante_tracciamento_e_indirizzi_non_web():
    assert normalizza("//feeds.hwupgrade.it/rss_news.xml", "https://www.hwupgrade.it/") == \
        "https://feeds.hwupgrade.it/rss_news.xml"
    assert normalizza("/a?utm_source=rss&id=3#commenti", "http://Sito.IT/x/") == "https://sito.it/a?id=3"
    for cattivo in ("javascript:alert(1)", "mailto:a@b.it", "https://user:pw@sito.it/", "https://sito.it/a b", ""):
        assert normalizza(cattivo, "https://sito.it/") is None


def test_sembra_articolo():
    assert sembra_articolo("https://www.evilsocket.net/2026/04/02/titolo/")
    assert sembra_articolo("https://e3rehab.com/how-to-fix-knee-pain-when-squatting/")
    assert not sembra_articolo("https://e3rehab.com/programs/")
    assert not sembra_articolo("https://sito.it/tag/sicurezza-informatica-avanzata/")
    assert not sembra_articolo("https://sito.it/")
    assert not sembra_articolo("https://www.nature.com/naturecareers/jobs/berkeley/-100-000-149-999/")  # niente parole
    assert not sembra_articolo("https://www.freecodecamp.org/news/privacy-policy/")


def test_date():
    ora = datetime(2026, 11, 6, 12, 0)
    assert da_iso("2026-11-05T10:00:00+01:00") == datetime(2026, 11, 5, 9, 0)
    assert da_iso("non una data") is None
    assert da_url("https://www.evilsocket.net/2026/04/02/titolo/") == datetime(2026, 4, 2)
    assert da_testo("Pubblicato il 21 ottobre 2026", ora) == datetime(2026, 10, 21)
    assert da_testo("Oct 21, 2026", ora) == datetime(2026, 10, 21)
    assert da_testo("2 days ago", ora) == datetime(2026, 11, 4, 12, 0)
    assert da_testo("3 ore fa", ora) == datetime(2026, 11, 6, 9, 0)
    assert da_testo("ieri", ora) == datetime(2026, 11, 5)
    assert da_testo("31 febbraio 2026", ora) is None
    assert da_testo("Alert - 06/11/26 11:06", ora) == datetime(2026, 11, 6, 11, 6)  # giorno/mese, come ACN
    assert da_testo("11/25/2026", datetime(2026, 12, 1)) == datetime(2026, 11, 25)  # all'americana se l'altra è impossibile
    assert da_testo("nessuna data qui", ora) is None


def test_una_data_senza_ora_vale_tutto_il_giorno():
    dal = datetime(2026, 10, 30, 14, 0)
    assert nella_finestra(datetime(2026, 10, 30), dal)
    assert not nella_finestra(datetime(2026, 10, 30, 13, 0), dal)
    assert not nella_finestra(datetime(2026, 10, 29), dal)


def test_perimetro_di_home_e_sezione():
    home = Profilo(url="https://www.hwupgrade.it/", perimetro=perimetro_di("https://www.hwupgrade.it/"))
    assert home.perimetro == "hwupgrade.it"
    assert home.nel_perimetro("https://gaming.hwupgrade.it/news/x")
    assert not home.nel_perimetro("https://www.fotografidigitali.it/news/x")
    home.siti_collegati["fotografidigitali.it"] = True
    assert home.nel_perimetro("https://www.fotografidigitali.it/news/x")

    sezione = Profilo(url="https://projectdiscovery.io/research", perimetro=perimetro_di("https://projectdiscovery.io/research"))
    assert sezione.perimetro == "projectdiscovery.io/research"
    assert sezione.nel_perimetro("https://projectdiscovery.io/research/titolo")
    assert not sezione.nel_perimetro("https://projectdiscovery.io/researchers")
    assert not sezione.nel_perimetro("https://blog.projectdiscovery.io/research/titolo")  # niente sottodomini


def test_pagina_successiva_e_piattaforma():
    from gradiens.fonti.siti.pagine import piattaforma
    from gradiens.fonti.siti.rete import Pagina
    from gradiens.fonti.siti.strategie.html import successiva

    elenco = b'<html><body><a href="/articles/3/">3</a><a href="/2/">no</a><a href="/articles/2/">2</a></body></html>'
    assert successiva(Pagina("https://e3rehab.com/articles/", 200, elenco, "text/html")) == "https://e3rehab.com/articles/2/"
    generatori = b'<html><head><meta name="generator" content="Elementor 3.2"><meta name="generator" content="WordPress 6.7">'
    assert piattaforma(Pagina("https://e3rehab.com/", 200, generatori, "text/html")) == "wordpress"
