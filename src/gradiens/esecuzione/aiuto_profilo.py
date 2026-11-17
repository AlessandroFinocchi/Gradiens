"""Aiuto dell'LLM al profilo di un sito, su richiesta dell'utente (ADR 0012, decisioni 19 e 33).

È l'unica chiamata LLM fuori da un'esecuzione: la dashboard chiama `aiuta`, mai il provider. Il tetto di
token è una stima: prima della chiamata si accorcia l'albero dei link finché sta nel tetto, dopo si
confrontano i token veri restituiti dal provider. L'interfaccia dei provider non cambia.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from gradiens.dati import impostazioni
from gradiens.esecuzione import prompt
from gradiens.esecuzione.chiamata import chiedi
from gradiens.fonti.siti import Profilo
from gradiens.fonti.siti.aiuto import Proposta, convalida, leggi_albero
from gradiens.llm import crea_provider
from gradiens.llm.base import ErroreLLM, Provider

log = logging.getLogger(__name__)

TETTO = 10_000  # token per richiesta (decisione 19)
CARATTERI_PER_TOKEN = 2.35  # misurato dalla 6b su JSON in italiano: è una stima (scheda 6a-12)
CARICO_FISSO = 1_300  # token che il provider aggiunge a ogni chiamata (stima della 6a-12)
USCITA = 2_700  # token di risposta attesi: 2.658 nella prova vera con Haiku, contro i 700 stimati dalla 6a-12


class AiutoNonDisponibile(Exception):
    """L'aiuto non si può dare; il messaggio è pensato per l'utente."""


@dataclass
class Aiuto:
    proposta: Proposta
    token: int  # ingresso più uscita, come li restituisce il provider
    gruppi_tolti: int  # gruppi di link lasciati fuori per stare nel tetto

    @property
    def oltre_il_tetto(self) -> bool:
        return self.token > TETTO


async def aiuta(s: Session, client: httpx.AsyncClient, profilo: Profilo,
                fabbrica_provider: Callable[[str], Provider] | None = None) -> Aiuto:
    """Rilegge la pagina iniziale e chiede all'LLM dell'elaborazione quali sezioni usare e cosa escludere."""
    gruppi = await leggi_albero(client, profilo)
    if not gruppi:
        raise AiutoNonDisponibile("La pagina iniziale del sito non risponde o non ha link interni da esaminare.")
    sistema = prompt.sistema_aiuto_profilo()
    tolti = 0
    messaggio = prompt.messaggio_aiuto_profilo(profilo, gruppi)
    while len(gruppi) > 1 and _stima(sistema + messaggio) + CARICO_FISSO + USCITA > TETTO:
        gruppi, tolti = gruppi[:-1], tolti + 1  # si tolgono i gruppi meno utili, che stanno in fondo
        messaggio = prompt.messaggio_aiuto_profilo(profilo, gruppi)
    imp = impostazioni.leggi(s)
    try:
        provider = (fabbrica_provider or crea_provider)(imp.provider_elaborazione)
        await provider.pronto()
        risposta = await chiedi(provider, sistema=sistema, messaggio=messaggio, schema=prompt.SCHEMA_AIUTO_PROFILO,
                                modello=imp.modello_elaborazione)
    except ErroreLLM as errore:
        raise AiutoNonDisponibile(str(errore)) from errore
    aiuto = Aiuto(convalida(risposta.dati, gruppi, profilo), risposta.token_ingresso + risposta.token_uscita, tolti)
    livello = logging.WARNING if aiuto.oltre_il_tetto else logging.INFO
    log.log(livello, "Aiuto al profilo di %s: %d token (tetto %d), %d gruppi di link tolti",
            profilo.url, aiuto.token, TETTO, tolti)
    return aiuto


def _stima(testo: str) -> float:
    return len(testo) / CARATTERI_PER_TOKEN
