# Struttura delle cartelle e ruoli

Ogni cartella ha un solo proprietario: chi ha bisogno di un cambiamento in una cartella altrui lo chiede a chi la possiede (CLAUDE.md, "Lavoro in team").

```
gradiens/
├─ pyproject.toml, uv.lock            architetto
├─ .env  (escluso da git)             chiavi API e token
├─ .gradiens/  (escluso da git)       database, configurazione, cache, log (PER-02)
├─ src/gradiens/
│  ├─ app/          avvio unico, CLI, avvio_windows.py        backend-engineer
│  ├─ dati/         modelli SQLAlchemy e migrazioni Alembic    backend-engineer
│  ├─ esecuzione/   orchestrazione, filtro, argomenti, duplicati,
│  │                metriche, pulizia, programmazione          backend-engineer
│  ├─ llm/          interfaccia (base.py), claude_code.py,
│  │                finto.py per i test, compatibile_openai    backend-engineer
│  ├─ fonti/
│  │  ├─ youtube/, arxiv/                                       backend-engineer
│  │  └─ siti/      profilo, strategie di scoperta ed
│  │                estrazione intercambiabili                  scraping-engineer
│  ├─ telegram/     bot e comandi                              backend-engineer
│  └─ dashboard/    comune.py, rotte.py, rotte_impostazioni.py,
│                   template Jinja2, CSS, htmx                 frontend-engineer
├─ tests/
│  ├─ <stessa struttura di src/gradiens>   test di unità di chi possiede la cartella
│  └─ accettazione/                        criteri ACC-*, siti di esempio   tester
├─ mockup/          preview HTML della fase 3                  frontend-engineer
└─ docs/            requisiti/ (analista-requisiti), adr/ e architettura/ (architetto),
                    test/ (tester)
```

## Regole

- **Nomi in italiano.** Moduli, classi e funzioni usano i termini di [CONTEXT.md](../../CONTEXT.md) (`notizia`, `esecuzione`, `interesse`, `argomento`…), così codice, PRD e dashboard parlano la stessa lingua. Restano in inglese solo i nomi imposti dalle librerie.
- **Confine dashboard / backend.** Il backend espone funzioni Python che restituiscono dati (es. "notizie con questi filtri"). Il frontend possiede tutta `dashboard/`, rotte comprese: con htmx ogni rotta restituisce un pezzo di HTML, quindi rotta e template stanno nelle stesse mani. La dashboard non scrive SQL e non chiama direttamente i provider LLM.
- **Confine fonti / esecuzione.** Ogni fonte (`youtube/`, `arxiv/`, `siti/`) restituisce notizie candidate in un formato comune. La normalizzazione degli indirizzi di un sito sta in `siti/`. Il riconoscimento dei duplicati tra fonti diverse (`DUP-*`) sta in `esecuzione/`.
- **Codice specifico per Windows** solo in `app/avvio_windows.py` ([ADR 0005](../adr/0005-avvio-all-accensione-con-attivita-pianificata.md)).
- **Dati a runtime** solo in `.gradiens/` e `.env`, entrambi esclusi da git (`PER-02`, `PER-03`). In `.env` vanno i segreti e le opzioni di avvio (prefisso `GRADIENS_`, es. `GRADIENS_PORTA`); le impostazioni che si cambiano dalla dashboard stanno nel database.
- **Sicurezza della dashboard**: risponde solo ai nomi host in `GRADIENS_HOST_CONSENTITI` (difesa dal DNS rebinding); le richieste che modificano qualcosa devono avere l'intestazione `HX-Request` (htmx) o `X-Gradiens-Cli` (CLI), che un altro sito non può aggiungere (difesa CSRF); lo spegnimento si accetta solo da `127.0.0.1`.
- **Comandi di sviluppo** con `uv` ([stack](stack.md)): `uv sync` crea l'ambiente `.venv` dentro la repo; `uv run pytest` esegue i test.

## Contratti

Regole fissate nella fetta 1 che le fette successive rispettano senza cambiarle.

**Fonti** (`fonti/__init__.py`). Ogni fonte espone `async def raccogli(client: httpx.AsyncClient, ..., dal: datetime) -> list[Candidata]`:
- `url` è l'indirizzo canonico, sempre `https://`: è la chiave del registro delle notizie viste e diventa un link nella dashboard, quindi la fonte scarta tutto ciò che non è un indirizzo web valido;
- le date sono in UTC senza fuso orario; con la data incerta si usa quella di scoperta e `data_incerta=True` (`WEB-15`);
- `sommario` serve al pre-filtro e viene accorciato a 1.500 caratteri; `contenuto` serve alla valutazione: testo pulito, senza HTML;
- `tipo` è uno di `arxiv`, `sito`, `video`, `short`; `stato` contiene stati come "contenuto parziale";
- le richieste usano `fonti.USER_AGENT`, generico e senza dati personali (`WEB-18`).

**Provider LLM** (`llm/base.py`). Un provider ha `nome` e `async def chiedi(*, sistema, messaggio, schema, modello) -> Risposta`:
- `sistema` è la parte fissa dell'esecuzione (va in cache), `messaggio` la parte variabile;
- risponde con un JSON conforme a `schema` (`Risposta.dati`) e con i token usati;
- solleva `QuotaEsaurita` quando la quota è finita (l'esecuzione si interrompe) ed `ErroreLLM` per tutto il resto (la notizia si riprova la volta dopo);
- un nuovo provider si registra in `llm/__init__.py` (`PROVIDER`).

**Esecuzione** (`esecuzione/esecutore.py`). `Esecutore.avvia(avviata_da)` è l'unico modo di far partire un'esecuzione (dashboard, CLI, Telegram, programmazione). Rifiuta la seconda con `GiaInCorso` (`ESE-02`). L'avanzamento sta in `Esecutore.avanzamento`, e lo spegnimento chiama `Esecutore.ferma()`. La risposta dell'LLM è un dato esterno: si accettano solo id di interessi esistenti e punteggi da 0 a 100.
