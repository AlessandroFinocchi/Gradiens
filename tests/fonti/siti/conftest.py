import asyncio
from pathlib import Path

import httpx
import pytest

from gradiens.fonti.siti import rete

FIXTURE = Path(__file__).parent / "fixture"


@pytest.fixture(autouse=True)
def rete_pulita(monkeypatch):
    """Niente pause nei test e nessuno stato condiviso (robots, turni, cache) tra un test e l'altro."""
    monkeypatch.setattr(rete, "PAUSA", 0.0)
    for stato in (rete._robots, rete._prossima, rete._cache):
        stato.clear()


class Sito:
    """Un sito finto: indirizzo -> risposta (testo, byte o httpx.Response). Gli indirizzi non elencati rispondono 404."""

    def __init__(self, rotte: dict):
        self.rotte = rotte
        self.richieste: list[str] = []

    def risponde(self, request: httpx.Request) -> httpx.Response:
        self.richieste.append(str(request.url))
        voce = self.rotte.get(str(request.url))
        if voce is None:
            return httpx.Response(404, text="non trovato")
        if isinstance(voce, httpx.Response):
            return voce
        corpo = voce if isinstance(voce, bytes) else voce.encode()
        inizio = corpo.lstrip()[:100].lower()
        tipo = "text/html" if b"html" in inizio else "application/json" if inizio[:1] in (b"[", b"{") else "application/xml"
        return httpx.Response(200, content=corpo, headers={"content-type": tipo})

    def esegui(self, funzione, *argomenti):
        async def prova():
            async with httpx.AsyncClient(transport=httpx.MockTransport(self.risponde)) as client:
                return await funzione(client, *argomenti)

        return asyncio.run(prova())

    @staticmethod
    def fixture(nome: str) -> bytes:
        return (FIXTURE / nome).read_bytes()

    @staticmethod
    def redirect(verso: str) -> httpx.Response:
        return httpx.Response(301, headers={"location": verso})


@pytest.fixture
def sito() -> type[Sito]:
    """Le prove non si importano a vicenda (import-mode=importlib): il sito finto arriva come fixture."""
    return Sito
