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
│  ├─ llm/          interfaccia + claude + compatibile_openai  backend-engineer
│  ├─ fonti/
│  │  ├─ youtube/, arxiv/                                       backend-engineer
│  │  └─ siti/      profilo, strategie di scoperta ed
│  │                estrazione intercambiabili                  scraping-engineer
│  ├─ telegram/     bot e comandi                              backend-engineer
│  └─ dashboard/    rotte FastAPI, template Jinja2, CSS, htmx  frontend-engineer
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
- **Dati a runtime** solo in `.gradiens/` e `.env`, entrambi esclusi da git (`PER-02`, `PER-03`).
- **Comandi di sviluppo** con `uv` ([stack](stack.md)): `uv sync` crea l'ambiente `.venv` dentro la repo; `uv run pytest` esegue i test.
