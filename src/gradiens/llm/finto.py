"""Provider finto per i test: nessuna chiamata vera, nessun token consumato."""

from collections.abc import Callable

from gradiens.llm.base import Risposta


class Finto:
    nome = "finto"

    def __init__(self, risponditore: Callable[[str, str, dict], dict]):
        self._risponditore = risponditore
        self.chiamate: list[tuple[str, str]] = []

    async def chiedi(self, *, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
        self.chiamate.append((sistema, messaggio))
        dati = self._risponditore(sistema, messaggio, schema)
        return Risposta(dati=dati, token_ingresso=(len(sistema) + len(messaggio)) // 4, token_uscita=50)
