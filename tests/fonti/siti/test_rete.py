"""Rete dei siti: per quanto si ricorda il verdetto di robots.txt (scheda 14 di docs/miglioramenti/04-debugging.md)."""

from types import SimpleNamespace

import httpx
import pytest

from gradiens.fonti.siti import rete

ROBOTS = "https://e.org/robots.txt"
PAGINA = "https://e.org/pagina"


@pytest.fixture
def orologio(monkeypatch):
    """`time.monotonic` finto solo per `rete`: le esecuzioni si spostano avanti nel tempo senza aspettare."""
    ora = [1000.0]
    monkeypatch.setattr(rete, "time", SimpleNamespace(monotonic=lambda: ora[0]))
    return ora


def _esecuzione(s, letture: int = 1) -> list[rete.Pagina]:
    """Un'esecuzione: un Navigatore nuovo che legge la pagina `letture` volte."""
    async def leggi(client):
        navigatore = rete.Navigatore(client)
        return [await navigatore.leggi(PAGINA) for _ in range(letture)]

    return s.esegui(leggi)


def test_un_robots_txt_503_non_vieta_la_seconda_esecuzione_a_venti_minuti(sito, orologio):
    s = sito({ROBOTS: httpx.Response(503), PAGINA: "<html>ok</html>"})

    prima = _esecuzione(s, letture=2)
    orologio[0] += 60
    stessa_esecuzione = _esecuzione(s)  # l'estrazione usa un Navigatore nuovo per ogni articolo

    assert [p.codice for p in prima + stessa_esecuzione] == [rete.VIETATA] * 3
    assert s.richieste.count(ROBOTS) == 2  # 503 e il suo nuovo tentativo, poi a ogni pagina non si richiede
    assert PAGINA not in s.richieste
    s.rotte[ROBOTS] = "User-agent: *\nAllow: /\n"
    orologio[0] += 20 * 60

    assert _esecuzione(s)[0].ok  # il server si è ripreso: la seconda esecuzione rilegge robots.txt


def test_un_robots_txt_429_vieta_il_sito_per_un_ora(sito, orologio):
    """WEB-18: il sito ha chiesto di rallentare, quindi il verdetto si ricorda anche tra le esecuzioni."""
    s = sito({ROBOTS: httpx.Response(429), PAGINA: "<html>ok</html>"})

    assert _esecuzione(s)[0].codice == rete.VIETATA
    s.rotte[ROBOTS] = "User-agent: *\nAllow: /\n"
    richieste = len(s.richieste)
    orologio[0] += 20 * 60

    assert _esecuzione(s)[0].codice == rete.VIETATA
    assert len(s.richieste) == richieste  # nessuna richiesta al sito
    orologio[0] += rete.DURATA_ROBOTS

    assert _esecuzione(s)[0].ok
