# Piano della fase 4 (codice)

Deciso il 5 novembre 2026. Si costruisce per fette verticali: ogni fetta arriva fino a qualcosa che si vede e funziona, e si chiude con la definizione di "fatto" di CLAUDE.md (test verdi, `/ponytail-review`, review con ocr, commit).

| # | Fetta | Contenuto | Requisiti principali |
|---|---|---|---|
| 0 | Fondamenta | `.gitignore` per primo; `pyproject.toml` con uv; struttura delle cartelle; configurazione (`.env`, `.gradiens/`); database con la prima migrazione; `gradiens avvia`, `stato`, `spegni`; dashboard vuota con sidebar, stile e tema delle preview | AMB, PER, CLI-01/03/04, UI-01, UI-10 (Aspetto) |
| 1 | arXiv da capo a fondo | interessi nelle Impostazioni; interfaccia dei provider LLM con Claude e un provider finto per i test; pre-filtro, valutazione, riassunto; pagina Notizie, notizia specifica, cuore, archivio; `gradiens esegui` | ARX, INT, LLM-01/03, ESE-03..07, UI-04..08, UI-13, CLI-02 |
| 2 | YouTube | video, short, trascrizioni (anche automatiche), dirette | YT |
| 3 | Siti web | profilo del sito, cascata di strategie, stati, rigenerazione, verifica sui 13 siti di esempio | WEB, ACC-01 |
| 4 | Esecuzioni complete | programmazione e pausa, metriche, resoconto, Home, cancellazione dopo 7 giorni, duplicati, segnali delle Impostazioni | ESE, DUP, UI-02/03, UI-14 |
| 5 | Telegram | tutorial, messaggio di fine esecuzione, comandi, bottone ❤️ | TG |
| 6 | Argomenti e raffinamento | Timeline, pagina dell'argomento, proposte di raffinamento | ESE-08/10, UI-09, INT |
| 7 | Il resto | configurazione iniziale guidata, avvio all'accensione, Aiuto, collegamento compatibile OpenAI, verifica finale dei criteri `ACC-*` | UI-11/12, AMB-04, LLM-02 |

Le preview approvate in `mockup/` sono la base dei template Jinja2.
