"""Funzioni senza LLM per l'aiuto dell'LLM al profilo di un sito (ADR 0012, scheda 6a-12).

Qui non ci sono prompt né chiamate: `leggi_albero` riduce la pagina iniziale a un albero di link da dare
all'LLM, `convalida` controlla la sua risposta. Prompt, tetto di token e provider stanno in
`esecuzione/aiuto_profilo.py`.
"""

import re
from dataclasses import dataclass, field

import httpx

from gradiens.fonti.siti.indirizzi import chiave, dentro, di_servizio, host, normalizza, segmenti
from gradiens.fonti.siti.pagine import SEZIONI_MASSIME, albero, collegamenti, nel_menu, spazi
from gradiens.fonti.siti.profilo import Profilo
from gradiens.fonti.siti.rete import REDIRECT_MASSIMI, Navigatore

ESEMPI = 2  # link mostrati all'LLM per un gruppo senza link del menu
ESEMPI_DEL_MENU = 20  # dei link del menu si mostrano tutti, fino a questo numero: tra loro ci sono le sezioni
TESTO_MASSIMO = 60
NOTA_MASSIMA = 600  # caratteri: nella prova vera l'LLM ne ha scritti circa 560
PAROLA = re.compile(r"[^\W\d_]{1,20}")  # un segmento come "news" o "categoria", non uno slug o un numero
FILE = re.compile(r"\.(?!html?$|php$|aspx?$)\w{2,5}$")  # feed, immagini, PDF: non sono pagine


@dataclass
class Gruppo:
    """Link interni della pagina con la stessa forma dell'indirizzo, es. "/categoria/*"."""

    forma: str
    link: list[tuple[str, str]] = field(default_factory=list)  # (indirizzo, testo), nell'ordine della pagina
    nel_menu: int = 0

    def come_dict(self) -> dict:
        quanti = min(max(ESEMPI, self.nel_menu), ESEMPI_DEL_MENU)
        return {"forma": self.forma, "link": len(self.link), "nel_menu": self.nel_menu,
                "esempi": [[url, testo] for url, testo in self.link[:quanti]]}


@dataclass
class Proposta:
    """Risposta dell'LLM già convalidata, come differenze rispetto al profilo: l'utente sceglie cosa applicare."""

    sezioni_aggiunte: list[str]
    sezioni_tolte: list[str]
    esclusi_nuovi: list[str]
    nota: str = ""

    @property
    def cambia_qualcosa(self) -> bool:
        return bool(self.sezioni_aggiunte or self.sezioni_tolte or self.esclusi_nuovi)


async def leggi_albero(client: httpx.AsyncClient, profilo: Profilo) -> list[Gruppo] | None:
    """Rilegge la pagina iniziale (robots.txt compreso) e la riduce ai link interni raggruppati per forma.
    None se la pagina non si legge."""
    pagina = await Navigatore(client, 1 + REDIRECT_MASSIMI).leggi(profilo.url)  # ogni redirect conta come lettura
    if (doc := albero(pagina)) is None:
        return None
    gruppi: dict[str, Gruppo] = {}
    visti = {chiave(pagina.url), chiave(profilo.url)}
    for url, a in collegamenti(doc, pagina.url):
        parti = segmenti(url)
        if chiave(url) in visti or not profilo.nel_perimetro(url) or profilo.escluso(url) or di_servizio(url) \
                or (parti and FILE.search(parti[-1])):
            continue
        visti.add(chiave(url))
        forma = _forma(url, profilo)
        gruppo = gruppi.setdefault(forma, Gruppo(forma))
        gruppo.link.append((url, _testo(a)))
        gruppo.nel_menu += nel_menu(a)
    # Prima i gruppi con link del menu (le sezioni), nell'ordine della pagina; poi gli altri, dal più numeroso.
    return sorted(gruppi.values(), key=lambda g: (g.nel_menu == 0, 0 if g.nel_menu else -len(g.link)))


def _forma(url: str, profilo: Profilo) -> str:
    """Il primo segmento resta se è una parola; gli altri, e gli slug o i numeri in cima, diventano "*"."""
    parti = ["*" if i or not PAROLA.fullmatch(s) else s for i, s in enumerate(segmenti(url))]
    h = host(url)
    return ("" if h == profilo.dominio else h) + "/" + "/".join(parti)


def _testo(a) -> str:
    return spazi(a.text_content() or a.get("title") or a.get("aria-label") or "")[:TESTO_MASSIMO]


def convalida(dati: dict, gruppi: list[Gruppo], profilo: Profilo) -> Proposta:
    """La risposta è un dato esterno (6a-12): si tengono solo indirizzi dell'albero e del perimetro.

    `sezioni` è l'elenco completo che l'LLM consiglia; `esclusi` sono prefissi nuovi che coprono almeno un link
    dell'albero, senza escludere la pagina iniziale."""
    nell_albero = {chiave(url).rstrip("/"): url for g in gruppi for url, _ in g.link}
    sezioni = []
    for voce in _indirizzi(dati.get("sezioni")):
        url = nell_albero.get(chiave(voce).rstrip("/"))
        if url and profilo.nel_perimetro(url) and not profilo.escluso(url) and url not in sezioni:
            sezioni.append(url)
    sezioni = sezioni[:SEZIONI_MASSIME]
    esclusi = []
    for prefisso in _indirizzi(dati.get("esclusi")):
        if profilo.nel_perimetro(prefisso) and not dentro(profilo.url, prefisso) and prefisso not in profilo.esclusi \
                and prefisso not in esclusi and any(dentro(url, prefisso) for url in nell_albero.values()):
            esclusi.append(prefisso)
    nota = dati.get("nota")
    visti = set(nell_albero.values())  # una sezione che l'LLM non ha visto non si propone di toglierla
    return Proposta(
        sezioni_aggiunte=[u for u in sezioni if u not in profilo.sezioni],
        sezioni_tolte=[u for u in profilo.sezioni if u not in sezioni and u in visti],
        esclusi_nuovi=esclusi,
        nota=spazi(nota)[:NOTA_MASSIMA] if isinstance(nota, str) else "",
    )


def _indirizzi(voci) -> list[str]:
    if not isinstance(voci, list):
        return []
    return [url for voce in voci if isinstance(voce, str) and (url := normalizza(voce))]
