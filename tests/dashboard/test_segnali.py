import pytest

from gradiens.dashboard import segnali
from gradiens.dati import esecuzioni, impostazioni, interessi
from gradiens.dati import siti as dati_siti
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.dati.modelli import CanaleYoutube


@pytest.fixture
def s(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    with fabbrica_sessioni(motore)() as sessione:
        yield sessione


def configura(s):
    """Tutti i dati obbligatori: nessun segnale."""
    interessi.aggiungi(s, "A", "a")
    impostazioni.aggiungi_categoria(s, "cs.CR")
    s.add(CanaleYoutube(id="UC" + "x" * 22, nome="Lab"))
    s.commit()
    sito = dati_siti.aggiungi(s, "https://buono.it/", {"url": "https://buono.it/"}, stato="ok")
    return sito


def test_dati_obbligatori_mancanti(s):
    trovati = segnali.segnali(s)
    assert {k: v.tipo for k, v in trovati.items()} == {
        "interessi": "avvertimento", "canali-youtube": "avvertimento", "siti": "avvertimento", "arxiv": "avvertimento"}
    assert trovati["arxiv"].voci == {"categorie"}
    configura(s)
    assert segnali.segnali(s) == {} and segnali.globale({}) is None


def test_siti_errore_rigenerato_e_collegati_nuovi(s):
    buono = configura(s)
    rotto = dati_siti.aggiungi(s, "https://rotto.it/", {"url": "https://rotto.it/"})
    dati_siti.registra_esito(s, rotto.id, "accesso bloccato", "", True)
    nuovo = dati_siti.aggiungi(s, "https://nuovo.it/", {"url": "https://nuovo.it/", "siti_collegati": {"blog.it": False}})
    dati_siti.salva_rigenerato(s, buono.id, {"url": "https://buono.it/"})
    siti = segnali.segnali(s)["siti"]
    assert siti.tipo == "avvertimento" and siti.motivi == ["https://rotto.it/: accesso bloccato"]  # prevale
    assert siti.voci == {f"sito-{rotto.id}", f"sito-{buono.id}", f"sito-{nuovo.id}"}
    dati_siti.registra_esito(s, rotto.id, "ok", "", False)
    dati_siti.registra_esito(s, nuovo.id, "ok", "", False)  # dopo la raccolta le proposte non si segnalano più
    siti = segnali.segnali(s)["siti"]
    assert siti.tipo == "novita" and siti.motivi == ["https://buono.it/: profilo rigenerato"]


def test_canale_irraggiungibile_senza_segnali_per_tetto_e_pausa(s):
    configura(s)
    e = esecuzioni.inizia(s, "programmazione")
    esecuzioni.termina(s, e.id, "completata", {"fonti": {
        "arxiv": {"oltre_tetto": 4},
        "youtube": {"stati": [{"fonte": "Lab", "stato": "non raggiungibile"}, {"fonte": "Tolto", "stato": "non raggiungibile"}]}}})
    esecuzioni.inizia(s, "cli")  # in corso: conta l'ultima conclusa
    impostazioni.salva_esecuzione(s, 60, 7, in_pausa=True)
    trovati = segnali.segnali(s)
    assert "arxiv" not in trovati  # tetto raggiunto: con molte categorie succede sempre (decisione 60)
    assert trovati["canali-youtube"].motivi == ["Lab: non raggiungibile"]  # solo i canali ancora seguiti
    assert "esecuzione" not in trovati  # la programmazione spenta è una scelta, non qualcosa da guardare
    sezione, segnale = segnali.globale(trovati)
    assert sezione == "canali-youtube" and segnale.tipo == "avvertimento"
    assert segnale.motivo == "Lab: non raggiungibile"
