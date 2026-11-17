"""Interfaccia comune dei provider LLM (PRD LLM-01): ogni provider sta dietro `Provider`."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Risposta:
    dati: dict  # JSON conforme allo schema richiesto
    token_ingresso: int  # compresi quelli letti o scritti nella cache
    token_uscita: int


class ErroreLLM(Exception):
    """Errore del provider; il messaggio è pensato per l'utente."""


class ErroreBloccante(ErroreLLM):
    """Errore che varrebbe anche per tutte le chiamate seguenti: l'esecuzione si ferma subito, senza
    nuovi tentativi, invece di fallire notizia per notizia."""


class QuotaEsaurita(ErroreBloccante):
    """La quota dell'abbonamento è finita (LLM-06): l'esecuzione si interrompe."""


class LoginRifiutato(ErroreBloccante):
    """Il provider rifiuta il login, es. Claude Code che non usa più quello dell'abbonamento (doc 05, 4.5)."""


class Provider(Protocol):
    nome: str

    async def pronto(self) -> str | None:
        """Solleva ErroreLLM, con un messaggio per l'utente, se il provider non si può usare (ACC-15).
        Restituisce la versione del programma che fa da provider, se ne ha una (es. Claude Code): quando
        cambia, l'esecuzione lo prova prima di usarlo (decisione 45)."""
        ...

    async def chiedi(self, *, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
        """`sistema` è la parte fissa dell'esecuzione (va in cache), `messaggio` quella variabile."""
        ...
