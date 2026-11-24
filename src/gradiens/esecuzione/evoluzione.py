"""Riassunto dell'evoluzione di un argomento, su richiesta dell'utente (UI-09, decisione 72).

Come l'aiuto al profilo dei siti (ADR 0012), è una chiamata LLM fuori da un'esecuzione: la dashboard chiama
`riassumi`, mai il provider. Si usa il provider dell'elaborazione, perché il riassunto è il suo ruolo.
"""

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from gradiens.dati import argomenti, impostazioni
from gradiens.dati.modelli import Argomento
from gradiens.esecuzione import prompt
from gradiens.esecuzione.chiamata import chiedi
from gradiens.llm import crea_provider
from gradiens.llm.base import ErroreLLM, Provider

log = logging.getLogger(__name__)

# shortcut: oltre le 40 notizie si leggono solo le più recenti, per tenere la chiamata sotto i ~23.000 token
# (misurati 17.000 con 29 notizie, il 24 nov 2026). Se un argomento le supera, il racconto parte da lì.
MASSIMO_NOTIZIE = 40


class RiassuntoNonDisponibile(Exception):
    """Il riassunto non si può fare; il messaggio è pensato per l'utente."""


async def riassumi(s: Session, id: int, fabbrica_provider: Callable[[str], Provider] | None = None) -> None:
    """Chiede all'LLM dell'elaborazione come si è evoluto l'argomento e salva il testo sull'argomento."""
    argomento = s.get_one(Argomento, id)
    notizie = list(reversed(argomento.notizie[:MASSIMO_NOTIZIE]))  # dalla più vecchia, come un racconto
    if len(notizie) < 2:
        raise RiassuntoNonDisponibile("Serve almeno un'altra notizia per raccontare un'evoluzione.")
    imp = impostazioni.leggi(s)
    try:
        provider = (fabbrica_provider or crea_provider)(imp.provider_elaborazione)
        await provider.pronto()
        risposta = await chiedi(
            provider,
            sistema=prompt.sistema_evoluzione(),
            messaggio=prompt.messaggio_evoluzione(argomento, notizie),
            schema=prompt.SCHEMA_EVOLUZIONE,
            modello=imp.modello_elaborazione,
        )
    except ErroreLLM as errore:
        raise RiassuntoNonDisponibile(str(errore)) from errore
    testo = risposta.dati["evoluzione"].strip()
    if not testo:
        raise RiassuntoNonDisponibile("L'LLM ha risposto senza testo: riprova.")
    argomenti.salva_evoluzione(s, id, testo, len(argomento.notizie))
    log.info(
        "Evoluzione dell'argomento %d: %d notizie, %d token",
        id,
        len(notizie),
        risposta.token_ingresso + risposta.token_uscita,
    )
