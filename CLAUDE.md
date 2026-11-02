# Gradiens
App per raccogliere, filtrare con LLM e riassumere notizie da YouTube, arXiv e siti web
in base agli interessi dell'utente. Requisiti originali: docs/requisiti/prompt-originale.md

## Regole di lavoro
- Lavora SOLO dentro questa cartella.
- Documentazione in italiano. Decisioni importanti → un ADR in docs/adr/.
- A ogni fase fai domande e proposte prima di procedere (una domanda alla volta).
- Fasi: 1) requisiti 2) stack 3) preview HTML 4) codice. Non anticipare le fasi.
- Mai scrivere chiavi API in file versionati: usa .env (in .gitignore).

## Vincoli di architettura (NON semplificare via)
- Provider LLM intercambiabili (Claude default, poi OpenAI/Gemini/locale).
- Strategie di scoperta/estrazione dei siti come moduli intercambiabili.

## Definizione di "fatto"
Test verdi, /ponytail-review eseguito, review con ocr senza problemi gravi, commit.

## Lavoro in team
Ogni membro del team possiede cartelle diverse: mai due membri sullo stesso file.