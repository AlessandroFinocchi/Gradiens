import asyncio

import httpx

from gradiens.fonti.siti.indirizzi import normalizza
from gradiens.fonti.siti import rete
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


def test_il_redirect_di_robots_txt_verso_la_rete_di_casa_non_viene_seguito(sito):
    """S-32, scheda 8: anche il redirect di robots.txt passa dal controllo degli indirizzi, come quello delle pagine."""
    s = sito({"https://pubblico-ssrf.example/robots.txt": sito.redirect("http://192.168.1.1/riavvia-il-router"),
              "https://pubblico-ssrf.example/pagina": "<html>ok</html>"})

    pagina = s.esegui(lambda client: Navigatore(client).leggi("https://pubblico-ssrf.example/pagina"))

    assert not any("192.168" in r for r in s.richieste)
    assert pagina.codice == ERRORE_RETE


def test_un_redirect_di_robots_txt_verso_una_pagina_pubblica_si_segue(sito):
    s = sito({"https://e.org/robots.txt": sito.redirect("https://www.e.org/robots.txt"),
              "https://www.e.org/robots.txt": "User-agent: *\nDisallow: /privata\n",
              "https://e.org/privata": "<html>no</html>", "https://e.org/pagina": "<html>ok</html>"})

    async def leggi(client):
        navigatore = Navigatore(client)
        return await navigatore.leggi("https://e.org/privata"), await navigatore.leggi("https://e.org/pagina")

    privata, pagina = s.esegui(leggi)

    assert privata.codice == rete.VIETATA  # le regole lette dopo il redirect valgono per e.org
    assert pagina.ok
    assert "https://e.org/privata" not in s.richieste


def test_senza_rete_robots_txt_non_diventa_un_divieto(sito):
    """PC appena acceso: il robots.txt irraggiungibile non è "robots.txt ora vieta", e non si ricorda per un'ora."""
    s = sito({"https://e.org/robots.txt": "User-agent: *\nAllow: /\n", "https://e.org/pagina": "<html>ok</html>"})
    rete_ok = False

    def risponde(request):
        if not rete_ok:
            raise httpx.ConnectError("Temporary failure in name resolution")
        return s.risponde(request)

    async def leggi():
        async with httpx.AsyncClient(transport=httpx.MockTransport(risponde)) as client:
            return await rete.Navigatore(client).leggi("https://e.org/pagina")

    assert asyncio.run(leggi()).codice == rete.ERRORE_RETE
    assert "https://e.org" not in rete._robots
    rete_ok = True
    assert asyncio.run(leggi()).ok  # tornata la rete, il sito si legge subito
