"""Provider predefinito: Claude Code con l'abbonamento dell'utente (ADR 0006)."""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path

from gradiens.llm.base import ErroreLLM, QuotaEsaurita, Risposta

log = logging.getLogger(__name__)

# Chiamate isolate: ~700 token di contesto invece di ~36.000 (misure nell'ADR 0006).
OPZIONI_ISOLAMENTO = [
    "--output-format", "json",
    "--tools", "",
    "--strict-mcp-config",
    "--safe-mode",
    "--disable-slash-commands",
    "--no-session-persistence",
]
PAROLE_QUOTA = ("usage limit", "rate limit", "limit reached", "quota")


def trova_eseguibile() -> Path:
    """Percorso di claude.exe. Lo script npm `claude.cmd` passerebbe gli argomenti a cmd.exe,
    che reinterpreta virgolette, % e &: per sicurezza si lancia l'eseguibile nativo."""
    trovato = os.environ.get("GRADIENS_CLAUDE") or shutil.which("claude")
    if trovato is None:
        raise ErroreLLM("Claude Code non è installato o non è nel PATH.")
    percorso = Path(trovato)
    if percorso.suffix.lower() in (".cmd", ".bat"):
        percorso = percorso.parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    if not percorso.exists():
        raise ErroreLLM(f"Eseguibile di Claude Code non trovato: {percorso}")
    return percorso


def _ambiente() -> dict[str, str]:
    # Con ANTHROPIC_API_KEY nell'ambiente Claude Code userebbe l'API a pagamento, non l'abbonamento.
    return {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}


def interpreta(uscita: str) -> Risposta:
    """Legge il JSON di `claude -p --output-format json`."""
    try:
        d = json.loads(uscita)
    except json.JSONDecodeError:
        raise ErroreLLM(f"Risposta di Claude Code non leggibile: {uscita[:200]!r}") from None
    if d.get("is_error"):
        testo = str(d.get("result") or d.get("api_error_status") or "errore sconosciuto")
        if d.get("api_error_status") == 429 or any(p in testo.lower() for p in PAROLE_QUOTA):
            raise QuotaEsaurita(f"Quota dell'abbonamento esaurita: {testo}")
        raise ErroreLLM(f"Claude Code ha risposto con un errore: {testo}")
    dati = d.get("structured_output")
    if not isinstance(dati, dict):
        raise ErroreLLM("Claude Code non ha restituito la risposta strutturata richiesta.")
    usage = d.get("usage") or {}
    ingresso = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return Risposta(dati=dati, token_ingresso=ingresso, token_uscita=usage.get("output_tokens") or 0)


class ClaudeCode:
    nome = "claude-code"

    def __init__(self, comando: list[str] | None = None, parallelismo: int = 3, timeout: float = 300):
        self._comando = comando  # per i test: un finto `claude`
        self._limite = asyncio.Semaphore(parallelismo)
        self._timeout = timeout

    async def chiedi(self, *, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
        try:
            return await self._una_chiamata(sistema, messaggio, schema, modello)
        except QuotaEsaurita:
            raise
        except ErroreLLM as errore:  # un solo nuovo tentativo per gli errori temporanei
            log.warning("Claude Code, nuovo tentativo dopo: %s", errore)
            return await self._una_chiamata(sistema, messaggio, schema, modello)

    async def _una_chiamata(self, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
        comando = [
            *(self._comando or [str(trova_eseguibile())]), "-p",
            "--model", modello,
            "--system-prompt", sistema,
            "--json-schema", json.dumps(schema, ensure_ascii=False),
            *OPZIONI_ISOLAMENTO,
        ]
        async with self._limite:
            processo = await asyncio.create_subprocess_exec(
                *comando, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=_ambiente(),
            )
            try:
                # Il messaggio passa da stdin: niente limiti di lunghezza della riga di comando.
                uscita, errori = await asyncio.wait_for(processo.communicate(messaggio.encode("utf-8")), self._timeout)
            except TimeoutError:
                processo.kill()
                await processo.wait()
                raise ErroreLLM(f"Claude Code non ha risposto entro {self._timeout:.0f} secondi.") from None
            except BaseException:  # cancellata (es. spegnimento): Claude non deve continuare a consumare quota
                processo.kill()
                raise
        if not uscita.strip():
            raise ErroreLLM(f"Claude Code è uscito senza risposta: {errori.decode('utf-8', 'replace')[:300]}")
        return interpreta(uscita.decode("utf-8", "replace"))
