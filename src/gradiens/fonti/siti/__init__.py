"""Fonte siti web (PRD 4.3): profilo del sito, cascata di strategie di scoperta, estrazione.

Nessuna chiamata a un LLM: analisi e raccolta usano solo euristiche deterministiche e le regole salvate
nel profilo (WEB-04).
"""

import asyncio
import copy
from dataclasses import dataclass, replace
from datetime import datetime

import httpx

from gradiens.fonti import Candidata
from gradiens.fonti.siti.date import da_url, nella_finestra
from gradiens.fonti.siti.estrazione import completa, estrai
from gradiens.fonti.siti.indirizzi import normalizza
from gradiens.fonti.siti.pagine import albero, collegati, commerciali, piattaforma, richiede_js, sezioni
from gradiens.fonti.siti.profilo import STRATEGIA_DEL_CAMPO, Profilo, perimetro_di
from gradiens.fonti.siti.rete import Navigatore
from gradiens.fonti.siti.strategie import STRATEGIE

__all__ = ["EsitoSito", "Profilo", "analizza", "completa", "raccogli", "rigenera"]

PAGINE_ANALISI = 40
OK, NESSUN_NUOVO = "ok", "nessun articolo nuovo"
BLOCCATO, JAVASCRIPT, NESSUNA = "accesso bloccato", "richiede JavaScript", "nessuna strategia funzionante"
SUGGERIMENTI = {
    BLOCCATO: "Il sito rifiuta le richieste automatiche e le protezioni non si aggirano. Se il sito ha un feed RSS "
              "ufficiale, inseriscine a mano l'indirizzo nel profilo.",
    JAVASCRIPT: "Il sito mostra gli articoli solo tramite JavaScript, che Gradiens non esegue. Inserisci a mano "
                "l'indirizzo di un feed nel profilo.",
    NESSUNA: "Non ho trovato feed, sitemap o elenchi di articoli leggibili. Inserisci a mano l'indirizzo di un feed "
             "o di una sezione nel profilo.",
}


@dataclass
class EsitoSito:
    candidate: list[Candidata]
    stato: str  # WEB-26
    guasto: bool  # guasto vero (WEB-24): conta per la rigenerazione automatica; "nessun articolo nuovo" non lo è
    dettaglio: str  # per l'utente: cosa è successo e cosa può fare


async def analizza(client: httpx.AsyncClient, url: str) -> Profilo:
    """Crea il profilo di un sito dal solo indirizzo (WEB-01, WEB-02). Solleva ValueError se l'indirizzo non è valido."""
    url = normalizza(url if "://" in url else "https://" + url.strip())
    if not url:
        raise ValueError("indirizzo non valido")
    profilo = Profilo(url=url, perimetro=perimetro_di(url))
    nav = Navigatore(client, PAGINE_ANALISI)
    pagina = await nav.leggi(url)
    if (doc := albero(pagina)) is not None:
        profilo.piattaforma = piattaforma(pagina)
        profilo.esclusi = commerciali(doc, pagina.url, profilo)
        profilo.sezioni = [s for s in sezioni(doc, pagina.url, profilo) if await nav.consentito(s)]
        profilo.siti_collegati = dict.fromkeys(collegati(doc, pagina.url, profilo), False)
    for nome, strategia in STRATEGIE.items():
        # shortcut: quando nessuna euristica funziona, qui un LLM potrebbe riconoscere l'elenco degli articoli (WEB-04).
        if dove := await strategia.analizza(nav, profilo, pagina if pagina.ok else None):
            profilo.strategie.append(nome)
            profilo.data_da = profilo.data_da or dove
    if not profilo.strategie:
        profilo.diagnosi = BLOCCATO if pagina.bloccata else JAVASCRIPT if richiede_js(pagina) else NESSUNA
    return profilo


async def rigenera(client: httpx.AsyncClient, vecchio: Profilo) -> Profilo:
    """Nuovo profilo dallo stesso indirizzo che conserva i campi modificati dall'utente (WEB-25)."""
    nuovo = await analizza(client, vecchio.url)
    for campo in vecchio.modificati:
        setattr(nuovo, campo, copy.deepcopy(getattr(vecchio, campo)))
        if campo in STRATEGIA_DEL_CAMPO and getattr(nuovo, campo):
            nuovo.attiva(STRATEGIA_DEL_CAMPO[campo])
    nuovo.modificati = list(vecchio.modificati)
    return nuovo


async def raccogli(client: httpx.AsyncClient, profilo: Profilo, dal: datetime) -> EsitoSito:
    """Articoli pubblicati da `dal` (UTC senza fuso): cascata di strategie che combina i risultati (WEB-10)."""
    if not profilo.strategie:
        stato = profilo.diagnosi or NESSUNA
        return EsitoSito([], stato, True, SUGGERIMENTI.get(stato, SUGGERIMENTI[NESSUNA]))
    nav = Navigatore(client, profilo.pagine_massime)
    trovate: dict[str, Candidata] = {}
    guasti: list[str] = []
    usate: list[str] = []
    riuscita = bloccata = feed_fermo = False
    for nome, strategia in STRATEGIE.items():
        if nome not in profilo.strategie:
            continue
        r = await strategia.raccogli(nav, profilo, dal)
        guasti += r.guasti
        riuscita |= r.riuscita
        bloccata |= r.bloccata
        nuove = [c for c in r.candidate if not profilo.escluso(c.url)]
        if nome == "feed" and r.riuscita and not nuove:
            feed_fermo = True  # da confermare: lo è se una strategia successiva trova articoli recenti
        elif feed_fermo and any(not c.data_incerta for c in nuove):
            guasti.append("il feed non ha articoli recenti mentre la sitemap o il sito ne mostrano: forse è fermo")
            feed_fermo = False
        if nuove:
            usate.append(nome)
        for c in nuove:
            _unisci(trovate, c)
        if r.copre and (trovate or nome != "feed"):
            break  # finestra coperta: le strategie più costose non servono
    candidate = sorted(trovate.values(), key=lambda c: c.pubblicata_il, reverse=True)
    candidate.sort(key=lambda c: c.data_incerta)
    oltre_il_tetto = len(candidate) > profilo.articoli_massimi
    candidate = await _date_incerte(nav, candidate[:profilo.articoli_massimi], dal)

    note = []
    if candidate:
        stato = OK
        note.append(f"{len(candidate)} articoli trovati con: {', '.join(usate)}.")
    elif riuscita:
        stato = NESSUN_NUOVO
        note.append("Nessun articolo pubblicato nella finestra di raccolta: è un esito normale.")
    else:
        stato = BLOCCATO if bloccata else NESSUNA
        note.append(SUGGERIMENTI[stato])
    if oltre_il_tetto:
        note.append(f"Raggiunto il tetto di {profilo.articoli_massimi} articoli: tenuti i più recenti.")
    if nav.letture >= profilo.pagine_massime:
        note.append(f"Raggiunto il tetto di {profilo.pagine_massime} pagine.")
    if guasti:
        note.append("Problemi: " + "; ".join(guasti) + ".")
    return EsitoSito(candidate, stato, bool(guasti) or not riuscita, " ".join(note))


def _unisci(trovate: dict[str, Candidata], c: Candidata) -> None:
    """Lo stesso articolo da più strategie: vince la prima, completata con data e sommario delle altre."""
    prima = trovate.setdefault(c.url, c)
    if prima.data_incerta and not c.data_incerta:
        prima.pubblicata_il, prima.data_incerta = c.pubblicata_il, False
    if not prima.sommario:
        prima.sommario = c.sommario


async def _date_incerte(nav: Navigatore, candidate: list[Candidata], dal: datetime) -> list[Candidata]:
    """Data mancante (WEB-15): dall'URL, poi dai metadati della pagina, entro il tetto di pagine; altrimenti resta incerta."""
    risultato = []
    for c in candidate:
        if c.data_incerta:
            data = da_url(c.url)
            if not data and (estratto := await asyncio.to_thread(estrai, await nav.leggi(c.url))):
                data = estratto.data
                c = replace(c, sommario=c.sommario or estratto.descrizione, titolo=c.titolo or estratto.titolo)
            if data:
                if not nella_finestra(data, dal):
                    continue
                c = replace(c, pubblicata_il=data, data_incerta=False)
        risultato.append(c)
    return risultato
