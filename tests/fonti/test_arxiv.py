import asyncio
from datetime import datetime

import httpx
import pytest

from gradiens.fonti import arxiv

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2611.01234v2</id>
    <published>2026-11-04T17:00:00Z</published>
    <title>Small Language Models
      as Pre-filters</title>
    <summary>  We use a small model
      to discard documents.  </summary>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CR" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2610.00001v1</id>
    <published>2026-10-20T09:00:00Z</published>
    <title>Old paper</title>
    <summary>Old.</summary>
    <arxiv:primary_category term="cs.CR"/>
  </entry>
</feed>"""


def test_interpreta_normalizza_url_titolo_e_data():
    nuova, vecchia = arxiv.interpreta(ATOM, ["cs.CL", "cs.CR"])
    assert nuova.url == "https://arxiv.org/abs/2611.01234"  # senza versione: v1 e v2 sono la stessa notizia
    assert nuova.titolo == "Small Language Models as Pre-filters"
    assert nuova.contenuto == nuova.sommario == "We use a small model to discard documents."
    assert nuova.fonte == "cs.CL"
    assert nuova.pubblicata_il == datetime(2026, 11, 4, 17, 0)
    assert vecchia.fonte == "cs.CR"


def test_la_fonte_e_la_categoria_seguita_non_la_primaria():
    nuova, _ = arxiv.interpreta(ATOM, ["cs.CR"])  # primaria cs.CL, trovato perché è anche in cs.CR
    assert nuova.fonte == "cs.CR"


def test_raccogli_tiene_solo_la_finestra_e_si_ferma():
    richieste = []

    def risponde(request: httpx.Request) -> httpx.Response:
        richieste.append(request)
        return httpx.Response(200, text=ATOM)

    async def prova():
        async with httpx.AsyncClient(transport=httpx.MockTransport(risponde)) as client:
            return await arxiv.raccogli(client, ["cs.CL", "cs.CR"], dal=datetime(2026, 11, 1))

    trovate = asyncio.run(prova())
    assert [c.url for c in trovate] == ["https://arxiv.org/abs/2611.01234"]
    assert len(richieste) == 1  # l'ultima voce è più vecchia della finestra: niente seconda pagina
    assert richieste[0].url.params["search_query"] == "cat:cs.CL OR cat:cs.CR"
    assert "Gradiens" in richieste[0].headers["User-Agent"]


def _raccogli_con(risposte: list[httpx.Response], monkeypatch) -> tuple[list, list[float]]:
    """Raccolta con risposte preparate e attese registrate invece di dormire."""
    attese = []

    async def dorme(secondi):
        attese.append(secondi)

    monkeypatch.setattr(arxiv.asyncio, "sleep", dorme)

    async def prova():
        trasporto = httpx.MockTransport(lambda _: risposte.pop(0))
        async with httpx.AsyncClient(transport=trasporto) as client:
            return await arxiv.raccogli(client, ["cs.CL"], dal=datetime(2026, 11, 1))

    return asyncio.run(prova()), attese


def test_dopo_un_429_aspetta_e_riprova(monkeypatch):
    risposte = [httpx.Response(429), httpx.Response(503), httpx.Response(200, text=ATOM)]
    trovate, attese = _raccogli_con(risposte, monkeypatch)
    assert [c.url for c in trovate] == ["https://arxiv.org/abs/2611.01234"]
    assert attese == list(arxiv.ATTESE[:2])


def test_rispetta_retry_after_ma_con_un_limite(monkeypatch):
    risposte = [
        httpx.Response(429, headers={"Retry-After": "7"}),
        httpx.Response(429, headers={"Retry-After": "86400"}),
        httpx.Response(200, text=ATOM),
    ]
    _, attese = _raccogli_con(risposte, monkeypatch)
    assert attese == [7.0, arxiv.ATTESA_MASSIMA]


def test_dopo_troppi_429_si_arrende(monkeypatch):
    risposte = [httpx.Response(429)] * (len(arxiv.ATTESE) + 1)
    with pytest.raises(httpx.HTTPStatusError, match="429"):
        _raccogli_con(risposte, monkeypatch)


def test_un_errore_4xx_non_si_riprova(monkeypatch):
    risposte = [httpx.Response(400)]
    with pytest.raises(httpx.HTTPStatusError, match="400"):
        _raccogli_con(risposte, monkeypatch)
