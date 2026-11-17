"""Aiuto dell'LLM al profilo di un sito (ADR 0012): tetto di token prima e dopo la chiamata, errori per l'utente."""

import asyncio
import json

import pytest

from gradiens.dati import impostazioni
from gradiens.dati.database import crea_motore, fabbrica_sessioni, migra
from gradiens.esecuzione import aiuto_profilo, prompt
from gradiens.esecuzione.aiuto_profilo import AiutoNonDisponibile, aiuta
from gradiens.fonti.siti import Profilo
from gradiens.fonti.siti.aiuto import Gruppo
from gradiens.llm.base import ErroreLLM, QuotaEsaurita, Risposta
from gradiens.llm.finto import Finto

PROFILO = Profilo(url="https://sito.it/", perimetro="sito.it", sezioni=["https://sito.it/eventi/"])
GRUPPI = [
    Gruppo("/notizie", [("https://sito.it/notizie/", "Notizie")], 1),
    Gruppo("/eventi", [("https://sito.it/eventi/", "Eventi")], 1),
    Gruppo("/offerte", [("https://sito.it/offerte/", "Offerte")], 1),
]


@pytest.fixture
def sessione(tmp_path):
    motore = crea_motore(tmp_path / "prova.db")
    migra(motore)
    with fabbrica_sessioni(motore)() as s:
        yield s


@pytest.fixture
def albero(monkeypatch):
    """La pagina iniziale già ridotta: la lettura vera è provata in tests/fonti/siti/test_aiuto_al_profilo.py."""
    letto = {"gruppi": GRUPPI}

    async def leggi_albero(client, profilo):
        return letto["gruppi"]

    monkeypatch.setattr(aiuto_profilo, "leggi_albero", leggi_albero)
    return letto


def _aiuta(sessione, provider):
    nomi = []

    def fabbrica(nome):
        nomi.append(nome)
        return provider

    risultato = asyncio.run(aiuta(sessione, None, PROFILO, fabbrica))
    return risultato, nomi


def test_proposta_convalidata_dal_provider_dell_elaborazione(sessione, albero):
    finto = Finto(
        lambda sistema, messaggio, schema: {
            "sezioni": ["https://sito.it/notizie/", "https://altro.example/notizie/"],
            "esclusi": ["https://sito.it/offerte/"],
            "nota": "Gli eventi non sono notizie.",
        }
    )
    aiuto, nomi = _aiuta(sessione, finto)
    assert nomi == [impostazioni.leggi(sessione).provider_elaborazione]
    assert (aiuto.proposta.sezioni_aggiunte, aiuto.proposta.sezioni_tolte) == (
        ["https://sito.it/notizie/"],
        ["https://sito.it/eventi/"],
    )
    assert aiuto.proposta.esclusi_nuovi == ["https://sito.it/offerte/"]
    assert not aiuto.oltre_il_tetto and aiuto.gruppi_tolti == 0
    sistema, messaggio = finto.chiamate[0]
    assert aiuto.token == (len(sistema) + len(messaggio)) // 4 + 50  # ingresso più uscita, come li conta il Finto
    assert sistema == prompt.sistema_aiuto_profilo()
    dati = json.loads(messaggio)
    assert (dati["indirizzo"], dati["sezioni_attuali"]) == ("https://sito.it/", ["https://sito.it/eventi/"])
    assert [g["forma"] for g in dati["gruppi"]] == ["/notizie", "/eventi", "/offerte"]


def test_l_albero_si_accorcia_per_stare_nel_tetto(sessione, albero):
    lungo = "https://sito.it/" + "x" * 150
    albero["gruppi"] = GRUPPI + [
        Gruppo(f"/g{i}/*", [(f"{lungo}/{i}/{j}", "testo " * 10) for j in range(3)]) for i in range(200)
    ]
    finto = Finto(lambda *_: {"sezioni": [], "esclusi": []})
    aiuto, _ = _aiuta(sessione, finto)
    sistema, messaggio = finto.chiamate[0]
    stima = (len(sistema) + len(messaggio)) / aiuto_profilo.CARATTERI_PER_TOKEN
    assert stima + aiuto_profilo.CARICO_FISSO + aiuto_profilo.USCITA <= aiuto_profilo.TETTO
    assert 0 < aiuto.gruppi_tolti < 200
    assert [g["forma"] for g in json.loads(messaggio)["gruppi"][:3]] == [
        "/notizie",
        "/eventi",
        "/offerte",
    ]  # si tolgono gli ultimi


class Costoso:
    nome = "costoso"

    async def pronto(self):
        return None

    async def chiedi(self, **_):
        return Risposta(dati={"sezioni": [], "esclusi": []}, token_ingresso=9_000, token_uscita=1_500)


def test_il_consumo_vero_oltre_il_tetto_si_segnala(sessione, albero):
    aiuto, _ = _aiuta(sessione, Costoso())
    assert (aiuto.token, aiuto.oltre_il_tetto) == (10_500, True)


def test_pagina_illeggibile_o_senza_link_non_chiama_l_llm(sessione, albero):
    finto = Finto(lambda *_: pytest.fail("non doveva chiamare l'LLM"))
    for gruppi in (None, []):
        albero["gruppi"] = gruppi
        with pytest.raises(AiutoNonDisponibile, match="pagina iniziale"):
            _aiuta(sessione, finto)
    assert finto.chiamate == []


class Rotto:
    nome = "rotto"

    def __init__(self, errore=None, dati=None, al_pronto=False):
        self.errore, self.dati, self.al_pronto = errore, dati, al_pronto

    async def pronto(self):
        if self.al_pronto:
            raise ErroreLLM("Claude Code non è collegato.")

    async def chiedi(self, **_):
        if self.errore:
            raise self.errore
        return Risposta(dati=self.dati, token_ingresso=10, token_uscita=10)


@pytest.mark.parametrize(
    "provider, messaggio",
    [
        (Rotto(al_pronto=True), "non è collegato"),
        (Rotto(QuotaEsaurita("Quota esaurita.")), "Quota esaurita"),
        (Rotto(dati={"esclusi": []}), "forma inattesa"),
    ],
)
def test_errori_del_provider_diventano_un_messaggio_per_l_utente(sessione, albero, provider, messaggio):
    with pytest.raises(AiutoNonDisponibile, match=messaggio):
        _aiuta(sessione, provider)
