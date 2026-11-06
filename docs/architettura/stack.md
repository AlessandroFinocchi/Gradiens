# Stack tecnologico

Riepilogo delle scelte della fase 2. Le decisioni difficili da invertire hanno un ADR.

| Area | Scelta | Decisione |
|---|---|---|
| Linguaggio | Python 3.14 | [ADR 0002](../adr/0002-python-come-linguaggio.md) |
| Dashboard | FastAPI + Jinja2 + htmx, un unico processo con bot e programmazione | [ADR 0003](../adr/0003-dashboard-generata-dal-server.md) |
| Database | SQLite con SQLAlchemy 2.0 e migrazioni Alembic | [ADR 0004](../adr/0004-sqlite-con-sqlalchemy-e-alembic.md) |
| Avvio all'accensione | Windows: attività pianificata in modalità S4U. Linux: servizio utente di systemd con lingering | [ADR 0005](../adr/0005-avvio-all-accensione-con-attivita-pianificata.md), [ADR 0007](../adr/0007-avvio-all-accensione-su-linux-con-systemd.md) |

## Librerie

| Compito | Libreria | Alternativa scartata e perché |
|---|---|---|
| Server web e template | `fastapi`, `uvicorn`, `jinja2`, `htmx` (file salvato nella repo) | vedi ADR 0003 |
| Database | `sqlalchemy`, `alembic` | vedi ADR 0004 |
| Richieste HTTP | `httpx` (asincrono) | `requests`: una richiesta alla volta |
| Testo e data degli articoli | `trafilatura` (con `htmldate`) | `newspaper4k`: meno affidabile sulle date |
| Feed RSS/Atom e API di arXiv | `feedparser` | libreria `arxiv`: l'API è già un feed Atom |
| robots.txt | `urllib.robotparser` (libreria standard) | — |
| YouTube | `youtube-transcript-api` (trascrizioni), `yt-dlp` (elenco, short, dirette, date) | API ufficiale: serve una chiave Google con quota e non dà le trascrizioni |
| LLM | CLI di Claude Code (`claude -p`, predefinito, [ADR 0006](../adr/0006-claude-code-come-provider-predefinito.md)), `anthropic`, `openai`, ognuno dietro l'interfaccia di provider del progetto | `litellm`: sostituirebbe l'interfaccia richiesta da CLAUDE.md e porta molte dipendenze |
| Telegram | `python-telegram-bot` | `aiogram`: meno documentato |
| Configurazione | `pydantic-settings` per `.env` (segreti, porta, nomi host consentiti); le impostazioni modificabili dalla dashboard stanno nel database, tabella `impostazioni` | — |
| Form HTML | `python-multipart`, richiesto da FastAPI per leggere i campi delle form | — |
| Programmazione giornaliera | ciclo `asyncio` del progetto (un orario al giorno più la pausa) | `APScheduler`: troppo per un solo orario |
| Test | `pytest`, con pagine e feed salvati come file di prova; `httpx2` per il client di test di Starlette | — |

Tutte le librerie hanno pacchetti pronti per Python 3.14 su Windows (verificato il 4 novembre 2026) e su Linux. `uv.lock` vale per entrambi i sistemi.

## Note

- `yt-dlp` va aggiornato periodicamente, perché YouTube cambia spesso. Un canale che va in errore viene mostrato con il suo stato.
- Nessun browser headless nella prima versione (PRD, sezione 11).
