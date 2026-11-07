# Gradiens
App per raccogliere, filtrare con LLM e riassumere notizie da YouTube, arXiv e siti web
in base agli interessi dell'utente. Requisiti: docs/requisiti/prd.md (prevale sul prompt
originale docs/requisiti/prompt-originale.md). Glossario: CONTEXT.md.
Stack: docs/architettura/stack.md. Cartelle e proprietari: docs/architettura/struttura.md.
Ambiente Python con uv (`uv sync`, `uv run pytest`, `uv run gradiens avvia|esegui|stato|spegni`).
Gira su Windows e su Linux: niente codice specifico di un sistema fuori da `app/avvio_sistema.py`
(ADR 0007); i test girano su entrambi (`.github/workflows/test.yml`).

## Portabilità (Windows e Linux)
- Lo sviluppo avviene su entrambi i sistemi: ogni modifica deve funzionare su Windows e su Linux.
- Percorsi con `pathlib`, file aperti con `encoding="utf-8"`, processi lanciati con liste di argomenti
  (mai `shell=True`), nessun eseguibile dato per scontato nel `PATH` di un solo sistema.
- La documentazione va di pari passo: dove i passi cambiano (installazione, avvio all'accensione,
  percorsi) si scrivono le istruzioni per Windows e per Linux, una accanto all'altra.

## Regole di lavoro
- Lavora SOLO dentro questa cartella.
- Documentazione in italiano. Decisioni importanti → un ADR in docs/adr/.
- A ogni fase fai domande e proposte prima di procedere (una domanda alla volta).
- Fasi: 1) requisiti 2) stack 3) preview HTML 4) codice. Non anticipare le fasi.
- Mai scrivere chiavi API in file versionati: usa .env (in .gitignore).
- L'app salva configurazione e dati solo dentro questa cartella, in `.gradiens/` e `.env`,
  esclusi da git; mai fuori (PRD PER-02, PER-03).

## Stato dei lavori e abitudini
- Fase 4 in corso, a fette verticali: stato, note e problemi aperti in
  docs/architettura/piano-fase-4.md. Leggilo prima di riprendere il lavoro.
- I commit li fa l'utente: Claude committa o fa merge solo su richiesta esplicita, mai push.
- Si lavora direttamente su `main`, senza worktree (`.claude/settings.json`).

## Vincoli di architettura (NON semplificare via)
- Provider LLM intercambiabili (Claude Code con l'abbonamento come default, API di Claude,
  poi OpenAI/Gemini/locale). ADR 0006.
- Strategie di scoperta/estrazione dei siti come moduli intercambiabili.

## Definizione di "fatto"
Test verdi, /ponytail-review eseguito, review con ocr senza problemi gravi, commit.

## Lavoro in team
Ogni membro del team possiede cartelle diverse: mai due membri sullo stesso file.