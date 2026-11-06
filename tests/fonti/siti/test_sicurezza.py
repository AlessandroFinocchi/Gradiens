import asyncio

import httpx

from gradiens.fonti.siti.indirizzi import normalizza
from gradiens.fonti.siti.rete import ERRORE_RETE, Navigatore


def test_indirizzi_della_rete_di_casa_rifiutati():
    for url in ["http://192.168.1.1/admin", "http://127.0.0.1:8765/api/stato", "http://localhost/x",
                "http://[::1]/x", "http://100.101.102.103/", "http://169.254.169.254/latest"]:
        assert normalizza(url) is None, url
    assert normalizza("https://www.redhotcyber.com/post/x?utm_source=a") == "https://www.redhotcyber.com/post/x"


def test_redirect_verso_la_rete_di_casa_rifiutato():
    richieste = []

    def risponde(request: httpx.Request) -> httpx.Response:
        richieste.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "http://192.168.1.1/admin"})

    async def prova():
        async with httpx.AsyncClient(transport=httpx.MockTransport(risponde)) as client:
            return await Navigatore(client).leggi("https://pubblico-ssrf.example/articolo")

    assert asyncio.run(prova()).codice == ERRORE_RETE
    assert not any("192.168" in r for r in richieste)
