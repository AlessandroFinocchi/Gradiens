"""Chiamata a un provider LLM con il controllo della forma della risposta, uguale per ogni provider (ADR 0006)."""

from gradiens.llm.base import ErroreLLM, Provider, Risposta


async def chiedi(provider: Provider, *, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
    """Chiama il provider e controlla la forma della risposta, uguale per ogni provider (ADR 0006, S-05):
    una forma inattesa è un ErroreLLM, quindi il blocco o la notizia si riprova invece di perdersi."""
    risposta = await provider.chiedi(sistema=sistema, messaggio=messaggio, schema=schema, modello=modello)
    _controlla_forma(risposta.dati, schema, "risposta")
    return risposta


SEMPLICI = {"string": str, "integer": (int, float)}  # un 85.5 si arrotonda dopo


def _controlla_forma(dati, schema: dict, dove: str) -> None:
    """Severo su chiavi obbligatorie, contenitori (oggetti e liste) e tipo dei campi semplici, tollerante sui
    valori: si ripuliscono dopo, e un controllo severo farebbe ripetere la valutazione a ogni esecuzione (S-36).
    Le liste di numeri (es. `pertinenti`) si ripuliscono voce per voce, quindi le loro voci non si controllano."""
    tipo = schema.get("type")
    if tipo == "object":
        if not isinstance(dati, dict):
            raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: «{dove}» non è un oggetto.")
        for chiave in schema.get("required", []):
            if dati.get(chiave) is None:
                raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: manca «{chiave}».")
        for chiave, sotto in schema.get("properties", {}).items():
            if chiave not in dati:
                continue
            semplice = SEMPLICI.get(sotto.get("type"))
            if semplice and dati[chiave] is not None and not isinstance(dati[chiave], semplice):
                raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: «{chiave}» non è del tipo atteso.")
            _controlla_forma(dati[chiave], sotto, chiave)
    elif tipo == "array":
        if not isinstance(dati, list):
            raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: «{dove}» non è una lista.")
        for voce in dati:
            _controlla_forma(voce, schema.get("items", {}), dove)
