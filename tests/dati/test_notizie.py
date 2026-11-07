from datetime import timedelta

import pytest

from gradiens.dati import esecuzioni, impostazioni, interessi, notizie
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.dati.impostazioni import ImpostazioneNonValida
from gradiens.dati.modelli import Esecuzione, Notizia, Pertinenza
from gradiens.dati.notizie import Filtri, adesso


@pytest.fixture
def s(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    with fabbrica_sessioni(motore)() as sessione:
        yield sessione


def notizia(s, url, tipo="arxiv", giorni_fa=1, cuore=False, punteggi=(), fonte="cs.CR"):
    quando = adesso() - timedelta(days=giorni_fa)
    n = Notizia(tipo=tipo, url=url, fonte=fonte, titolo=url, riassunto="r", pubblicata_il=quando,
                scoperta_il=quando, cuore=cuore)
    n.pertinenze = [Pertinenza(interesse_id=i, punteggio=p) for i, p in punteggi]
    s.add(n)
    s.commit()
    return n


def titoli(lista):
    return [n.url for n in lista]


def test_notizie_mostrate_solo_sopra_soglia_e_negli_ultimi_7_giorni(s):
    sic = interessi.aggiungi(s, "Sicurezza", "attacchi")
    notizia(s, "alta", punteggi=[(sic.id, 90)])
    notizia(s, "bassa", punteggi=[(sic.id, 40)])
    notizia(s, "vecchia", giorni_fa=8, punteggi=[(sic.id, 95)])
    notizia(s, "sulla-soglia", punteggi=[(sic.id, 60)])
    assert titoli(notizie.elenca(s, Filtri(), soglia=60)) == ["alta", "sulla-soglia"]


def test_ordinamento_per_interesse_filtrato_e_per_data(s):
    a = interessi.aggiungi(s, "A", "a")
    b = interessi.aggiungi(s, "B", "b")
    notizia(s, "forte-in-a", giorni_fa=3, punteggi=[(a.id, 95), (b.id, 61)])
    notizia(s, "forte-in-b", giorni_fa=1, punteggi=[(a.id, 70), (b.id, 99)])
    assert titoli(notizie.elenca(s, Filtri(), 60)) == ["forte-in-b", "forte-in-a"]
    assert titoli(notizie.elenca(s, Filtri(interesse_id=a.id), 60)) == ["forte-in-a", "forte-in-b"]
    assert titoli(notizie.elenca(s, Filtri(ordine="data", crescente=True), 60)) == ["forte-in-a", "forte-in-b"]


def test_filtri_tipo_fonte_cuore(s):
    a = interessi.aggiungi(s, "A", "a")
    notizia(s, "paper", punteggi=[(a.id, 80)], cuore=True)
    notizia(s, "video", tipo="video", fonte="Lab", punteggi=[(a.id, 80)])
    assert titoli(notizie.elenca(s, Filtri(tipi=["video"]), 60)) == ["video"]
    assert titoli(notizie.elenca(s, Filtri(fonte="cs.CR"), 60)) == ["paper"]
    assert titoli(notizie.elenca(s, Filtri(solo_cuore=True), 60)) == ["paper"]


def test_fonti_dei_tipi_scelti_con_il_nome_delle_categorie(s):
    impostazioni.aggiungi_categoria(s, "cs.CR", "Crittografia e Sicurezza")
    notizia(s, "paper")
    notizia(s, "paper-ml", fonte="cs.LG")  # categoria principale non scelta: resta il codice
    notizia(s, "sito", tipo="sito", fonte="hwupgrade.it")
    notizia(s, "video", tipo="video", fonte="Lab")
    nomi = impostazioni.nomi_categorie(s)
    assert nomi == {"cs.CR": "Crittografia e Sicurezza"}
    tutte = {"cs.CR": "Crittografia e Sicurezza", "cs.LG": "cs.LG", "hwupgrade.it": "hwupgrade.it", "Lab": "Lab"}
    assert notizie.fonti(s, [], nomi) == tutte
    assert list(notizie.fonti(s, [], nomi)) == ["cs.CR", "cs.LG", "hwupgrade.it", "Lab"]  # in ordine di nome
    assert notizie.fonti(s, ["arxiv"], nomi) == {"cs.CR": "Crittografia e Sicurezza", "cs.LG": "cs.LG"}
    assert notizie.fonti(s, ["arxiv", "sito"], nomi).keys() == {"cs.CR", "cs.LG", "hwupgrade.it"}
    assert notizie.nome_fonte("sito", "cs.CR", nomi) == "cs.CR"  # il nome vale solo per arXiv


def test_archivio_tiene_le_notizie_con_cuore_anche_vecchie_e_senza_interesse(s):
    a = interessi.aggiungi(s, "A", "a")
    interessi.aggiungi(s, "B", "b")
    notizia(s, "vecchia-col-cuore", giorni_fa=40, cuore=True, punteggi=[(a.id, 80)])
    notizia(s, "senza-cuore", punteggi=[(a.id, 80)])
    interessi.elimina(s, a.id)  # INT-09: in archivio resta, senza punteggi
    s.expire_all()
    archivio = notizie.elenca(s, Filtri(archivio=True), 60)
    assert titoli(archivio) == ["vecchia-col-cuore"]
    assert archivio[0].pertinenze == []


def test_cuore(s):
    n = notizia(s, "x")
    assert notizie.imposta_cuore(s, n.id, True).cuore
    assert not notizie.imposta_cuore(s, n.id, False).cuore


def test_registro_delle_notizie_viste(s):
    notizie.segna_viste(s, ["u1", "u2", "u1"])
    s.commit()
    assert notizie.gia_viste(s, ["u1", "u3"]) == {"u1"}


def test_almeno_un_interesse_e_nomi_unici(s):
    unico = interessi.aggiungi(s, "Unico", "d")
    with pytest.raises(ImpostazioneNonValida):
        interessi.elimina(s, unico.id)
    with pytest.raises(ImpostazioneNonValida):
        interessi.aggiungi(s, "Unico", "altra")
    with pytest.raises(ImpostazioneNonValida):
        interessi.aggiungi(s, "  ", "d")


def test_categorie_arxiv_validate(s):
    impostazioni.aggiungi_categoria(s, " cs.CR ")
    impostazioni.aggiungi_categoria(s, "cs.CR", " Sicurezza ")  # già presente: cambia solo il nome
    assert [(c.codice, c.nome) for c in impostazioni.elenca_categorie(s)] == [("cs.CR", "Sicurezza")]
    with pytest.raises(ImpostazioneNonValida):
        impostazioni.aggiungi_categoria(s, "cs.AI", "x" * 101)
    assert impostazioni.categorie_arxiv(s) == ["cs.CR"]
    with pytest.raises(ImpostazioneNonValida):
        impostazioni.aggiungi_categoria(s, "cs.CR OR 1=1")
    with pytest.raises(ImpostazioneNonValida):  # ARX-01: almeno una categoria
        impostazioni.rimuovi_categoria(s, "cs.CR")


def test_esecuzioni_rimaste_in_corso_diventano_interrotte(s):
    e = esecuzioni.inizia(s, "cli")
    assert esecuzioni.segna_interrotte(s) == 1
    s.expire_all()
    assert s.get(Esecuzione, e.id).stato == "interrotta"
