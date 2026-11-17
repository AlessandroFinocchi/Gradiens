"""Provider LLM intercambiabili (PRD LLM-01, LLM-02). Per aggiungerne uno basta registrarlo qui."""

from gradiens.llm.base import ErroreLLM, Provider
from gradiens.llm.claude_code import ClaudeCode

PROVIDER = {"claude-code": ClaudeCode}
NOMI = {"claude-code": "Claude Code"}  # per l'utente


def nome_provider(nome: str) -> str:
    return NOMI.get(nome, nome)


def crea_provider(nome: str) -> Provider:
    if nome not in PROVIDER:
        raise ErroreLLM(f"Provider LLM sconosciuto: {nome}")
    return PROVIDER[nome]()
