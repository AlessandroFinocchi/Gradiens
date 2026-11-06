"""Verifica sui 13 siti di esempio (ACC-01), sui siti veri: NON fa parte dei test automatici.

Esegui con `python -m uv run python tests/fonti/siti/verifica_reale.py [indirizzi…]` (senza argomenti: tutti
e 13). Rispetta robots.txt e le pause per dominio come l'applicazione, perché usa lo stesso codice.
"""

import asyncio
import sys
from datetime import timedelta

import httpx

from gradiens.fonti.siti import analizza, raccogli
from gradiens.fonti.siti.date import adesso

SITI = [
    "https://www.nature.com/",
    "https://www.hwupgrade.it/",
    "https://www.ilsoftware.it/",
    "https://www.redhotcyber.com/",
    "https://e3rehab.com/articles/",
    "https://chipsandcheese.com/",
    "https://projectdiscovery.io/research",
    "https://gamesbeat.com/",
    "https://www.freecodecamp.org/news",
    "https://www.acn.gov.it/portale/csirt-italia/",
    "https://thehackernews.com/",
    "https://www.3blue1brown.com/",
    "https://www.evilsocket.net/",
]


async def verifica(client: httpx.AsyncClient, url: str) -> str:
    try:
        profilo = await analizza(client, url)
        esito = await raccogli(client, profilo, adesso() - timedelta(days=7))
    except Exception as e:  # una verifica manuale: si riporta e si va avanti
        return f"## {url}\nECCEZIONE {type(e).__name__}: {e}\n"
    incerte = sum(c.data_incerta for c in esito.candidate)
    righe = [
        f"## {url}",
        f"strategie={profilo.strategie} data_da={profilo.data_da!r} piattaforma={profilo.piattaforma!r} "
        f"diagnosi={profilo.diagnosi!r}",
        f"feed={profilo.feed}",
        f"sitemap={profilo.sitemap}",
        f"sezioni={profilo.sezioni}",
        f"esclusi={profilo.esclusi} collegati={list(profilo.siti_collegati)}",
        f"ESITO: stato={esito.stato!r} guasto={esito.guasto} articoli={len(esito.candidate)} (data incerta: {incerte})",
        f"dettaglio: {esito.dettaglio}",
    ]
    righe += [f"  - {c.pubblicata_il:%Y-%m-%d %H:%M}{' ?' if c.data_incerta else ''} {c.titolo[:80]} <{c.url}>"
              for c in esito.candidate[:5]]
    return "\n".join(righe) + "\n"


async def main() -> None:
    async with httpx.AsyncClient() as client:
        # siti diversi in parallelo: le pause valgono per dominio
        for testo in await asyncio.gather(*(verifica(client, u) for u in sys.argv[1:] or SITI)):
            print(testo)


if __name__ == "__main__":
    asyncio.run(main())
