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


class QuotaEsaurita(ErroreLLM):
    """La quota dell'abbonamento è finita (LLM-06): l'esecuzione si interrompe."""


class Provider(Protocol):
    nome: str

    async def pronto(self) -> None:
        """Solleva ErroreLLM, con un messaggio per l'utente, se il provider non si può usare (ACC-15)."""
        ...

    async def chiedi(self, *, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
        """`sistema` è la parte fissa dell'esecuzione (va in cache), `messaggio` quella variabile."""
        ...
