"""Provider predefinito: Claude Code con l'abbonamento dell'utente (ADR 0006)."""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from gradiens.app.avvio_sistema import eseguibile_claude
from gradiens.llm.base import ErroreBloccante, ErroreLLM, LoginRifiutato, QuotaEsaurita, Risposta

log = logging.getLogger(__name__)

# Chiamate isolate: ~700 token di contesto invece di ~36.000 (misure nell'ADR 0006).
OPZIONI_ISOLAMENTO = [
    "--output-format",
    "json",
    "--tools",
    "",
    "--strict-mcp-config",
    "--safe-mode",
    "--disable-slash-commands",
    "--no-session-persistence",
]
PAROLE_QUOTA = ("usage limit", "rate limit", "limit reached", "quota")
# Il testo degli errori di login non è documentato (ipotesi dai messaggi visti): conta anche il codice HTTP.
PAROLE_LOGIN = ("/login", "not logged in", "invalid api key", "authentication", "unauthorized")
# `authMethod` di `claude auth status` (CLI reference) diverso da "claude.ai", l'abbonamento.
COLLEGAMENTI = {
    "api_key": "collegato con una chiave API",
    "api_key_helper": "collegato con una chiave API",
    "oauth_token": "collegato con un token",
    "third_party": "collegato tramite un altro fornitore",
}
_cartella_config: Path | None = None  # `configDirectory` dell'ultimo `claude auth status` (per `scadenza_login`)


def trova_eseguibile() -> Path:
    """Percorso dell'eseguibile di Claude Code: `GRADIENS_CLAUDE` oppure quello nel PATH."""
    trovato = os.environ.get("GRADIENS_CLAUDE") or shutil.which("claude")
    if trovato is None:
        raise ErroreLLM("Claude Code non è installato o non è nel PATH.")
    percorso = eseguibile_claude(Path(trovato))
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
        d = None
    if not isinstance(d, dict):  # anche `null` o `[]` (S-04)
        raise ErroreLLM(f"Risposta di Claude Code non leggibile: {uscita[:200]!r}")
    if d.get("is_error"):
        testo = str(d.get("result") or d.get("api_error_status") or "errore sconosciuto")
        if d.get("api_error_status") == 429 or any(p in testo.lower() for p in PAROLE_QUOTA):
            raise QuotaEsaurita(f"Quota dell'abbonamento esaurita: {testo}")
        if d.get("api_error_status") in (401, 403) or any(p in testo.lower() for p in PAROLE_LOGIN):
            raise LoginRifiutato(f"Claude Code ha rifiutato il login ({testo}): {RIMEDIO_LOGIN}")
        raise ErroreLLM(f"Claude Code ha risposto con un errore: {testo}")
    dati = d.get("structured_output")
    if not isinstance(dati, dict):
        raise ErroreLLM("Claude Code non ha restituito la risposta strutturata richiesta.")
    usage = d.get("usage") or {}
    ingresso = sum(
        usage.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )
    return Risposta(dati=dati, token_ingresso=ingresso, token_uscita=usage.get("output_tokens") or 0)


class ClaudeCode:
    nome = "claude-code"

    def __init__(self, comando: list[str] | None = None, parallelismo: int = 3, timeout: float = 300):
        self._comando = comando  # per i test: un finto `claude`
        self._limite = asyncio.Semaphore(parallelismo)
        self._timeout = timeout

    async def pronto(self) -> str | None:
        """Claude Code installato e collegato a un account (UI-11, ACC-15); restituisce la sua versione."""
        await asyncio.to_thread(stato_account, self._comando)
        versione_ = await asyncio.to_thread(versione, self._comando)
        log.info("Claude Code %s", versione_ or "di versione sconosciuta")
        return versione_

    async def chiedi(self, *, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
        try:
            return await self._una_chiamata(sistema, messaggio, schema, modello)
        except ErroreBloccante:
            raise
        except ErroreLLM as errore:  # un solo nuovo tentativo per gli errori temporanei
            log.warning("Claude Code, nuovo tentativo dopo: %s", errore)
            return await self._una_chiamata(sistema, messaggio, schema, modello)

    async def _una_chiamata(self, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
        comando = [
            *(self._comando or [str(trova_eseguibile())]),
            "-p",
            "--model",
            modello,
            "--system-prompt",
            sistema,
            "--json-schema",
            json.dumps(schema, ensure_ascii=False),
            *OPZIONI_ISOLAMENTO,
        ]
        async with self._limite:
            processo = await asyncio.create_subprocess_exec(
                *comando,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_ambiente(),
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


RIMEDIO_LOGIN = "apri un terminale, scrivi claude e poi /login (su un PC senza browser: claude setup-token)."
GIORNI_AVVISO_LOGIN = 3


def stato_account(comando: list[str] | None = None) -> str:
    """UI-11: descrizione del collegamento di Claude Code a un account, per esempio "abbonamento Pro".
    Solleva ErroreLLM, con un messaggio per l'utente, se Claude Code manca o non è collegato.

    Decide solo con ciò che la CLI reference documenta (doc 05, 4.5 punto 4): il codice di uscita (0 collegato,
    1 no), `authMethod` e `configDirectory`. `subscriptionType`, non documentato, serve solo per il testo."""
    global _cartella_config
    try:
        risultato = subprocess.run(
            [*(comando or [str(trova_eseguibile())]), "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=_ambiente(),
        )
    except OSError, subprocess.TimeoutExpired:
        raise ErroreLLM("Claude Code non risponde: prova ad aprirlo in un terminale con il comando claude.") from None
    try:
        dati = json.loads(risultato.stdout)
    except json.JSONDecodeError:
        dati = None
    dati = dati if isinstance(dati, dict) else {}
    metodo = dati.get("authMethod")
    if risultato.returncode != 0 or metodo == "none":
        raise ErroreLLM(f"Claude Code non è collegato a un account: {RIMEDIO_LOGIN}")
    if isinstance(cartella := dati.get("configDirectory"), str) and cartella:
        _cartella_config = Path(cartella)
    abbonamento = dati.get("subscriptionType")
    if metodo == "claude.ai" or (metodo is None and abbonamento):  # senza `authMethod`: versioni prima della 2.1.268
        return f"abbonamento {str(abbonamento).capitalize()}" if abbonamento else "abbonamento"
    return COLLEGAMENTI.get(metodo, "collegato a un account")


def versione(comando: list[str] | None = None) -> str | None:
    """`claude --version` (opzione documentata, non chiama il modello), es. "2.1.316". None se non si legge:
    l'esecuzione va avanti, manca solo il confronto con la versione precedente."""
    try:
        risultato = subprocess.run(
            [*(comando or [str(trova_eseguibile())]), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=_ambiente(),
        )
    except OSError, subprocess.TimeoutExpired, ErroreLLM:
        return None
    trovata = re.match(r"\d+(\.\d+)+", risultato.stdout.strip()) if risultato.returncode == 0 else None
    return trovata and trovata.group()


def scadenza_login() -> datetime | None:
    """Quando scade il rinnovo del login di Claude Code (`refreshTokenExpiresAt` nelle sue credenziali, ora
    del PC). Dopo quella data Claude Code non rinnova più il login da solo e le esecuzioni falliscono. Si legge
    solo la data: i token non si usano né si copiano. None se il file non c'è (es. login tenuto nel Keychain)."""
    # La cartella detta da `claude auth status`; prima del suo primo controllo, quella che usa Claude Code.
    cartella = _cartella_config or Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    try:
        millisecondi = json.loads((cartella / ".credentials.json").read_text(encoding="utf-8"))["claudeAiOauth"][
            "refreshTokenExpiresAt"
        ]
        return datetime.fromtimestamp(millisecondi / 1000) if millisecondi else None
    except OSError, ValueError, KeyError, TypeError:
        return None


def avviso_login(adesso: datetime | None = None) -> str | None:
    """Testo per l'utente se il login di Claude Code scade entro pochi giorni, o è già scaduto."""
    scadenza, adesso = scadenza_login(), adesso or datetime.now()
    if scadenza is None or scadenza - adesso > timedelta(days=GIORNI_AVVISO_LOGIN):
        return None
    if scadenza <= adesso:
        return f"Il login di Claude Code è scaduto il {scadenza:%d/%m alle %H:%M}: {RIMEDIO_LOGIN}"
    return (
        f"Il login di Claude Code scade il {scadenza:%d/%m alle %H:%M}: "
        f"per non far fallire le esecuzioni, {RIMEDIO_LOGIN}"
    )
