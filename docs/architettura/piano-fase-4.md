# Piano della fase 4 (codice)

Deciso il 5 novembre 2026. Si costruisce per fette verticali: ogni fetta arriva fino a qualcosa che si vede e funziona, e si chiude con la definizione di "fatto" di CLAUDE.md (test verdi, `/ponytail-review`, review con ocr, commit).

| # | Fetta | Contenuto | Requisiti principali | Stato |
|---|---|---|---|---|
| 0 | Fondamenta | `.gitignore` per primo; `pyproject.toml` con uv; struttura delle cartelle; configurazione (`.env`, `.gradiens/`); database con la prima migrazione; `gradiens avvia`, `stato`, `spegni`; dashboard vuota con sidebar, stile e tema delle preview | AMB, PER, CLI-01/03/04, UI-01, UI-10 (Aspetto) | fatta (6 nov) |
| 1 | arXiv da capo a fondo | interessi nelle Impostazioni; interfaccia dei provider LLM con Claude e un provider finto per i test; pre-filtro, valutazione, riassunto; pagina Notizie, notizia specifica, cuore, archivio; `gradiens esegui` | ARX, INT, LLM-01/03, ESE-03..07, UI-04..08, UI-13, CLI-02 | fatta (6 nov) |
| 2 | YouTube | video, short, trascrizioni (anche automatiche), dirette | YT | da fare |
| 3 | Siti web | profilo del sito, cascata di strategie, stati, rigenerazione, verifica sui 13 siti di esempio | WEB, ACC-01 | da fare |
| 4 | Esecuzioni complete | programmazione e pausa, metriche, resoconto, Home, cancellazione dopo 7 giorni, duplicati, segnali delle Impostazioni | ESE, DUP, UI-02/03, UI-14 | da fare |
| 5 | Telegram | tutorial, messaggio di fine esecuzione, comandi, bottone ❤️ | TG | da fare |
| 6 | Argomenti e raffinamento | Timeline, pagina dell'argomento, proposte di raffinamento | ESE-08/10, UI-09, INT | da fare |
| 7 | Il resto | configurazione iniziale guidata, avvio all'accensione, Aiuto, collegamento compatibile OpenAI, verifica finale dei criteri `ACC-*` | UI-11/12, AMB-04, LLM-02 | da fare |

Le preview approvate in `mockup/` sono la base dei template Jinja2.

## Note per le fette successive

- **Nuova fonte (fette 2 e 3)**: una funzione `raccogli(...)` che restituisce `Candidata` (vedi [struttura.md](struttura.md), "Contratti"), registrata nell'esecutore accanto ad arXiv. Il pre-filtro, la valutazione e il salvataggio restano invariati. Le metriche vanno divise per tipo di fonte (oggi c'è solo `arxiv`).
- **Fetta 3, siti web**: può partire in parallelo allo `scraping-engineer` in `fonti/siti/`, perché il contratto delle fonti è fissato. Il `tester` prepara intanto le verifiche dei 13 siti in `tests/accettazione/`.
- **Fetta 4**: la Home sostituisce il segnaposto in `dashboard/rotte.py` (`IN_ARRIVO`); la programmazione giornaliera usa `Esecutore.avvia("programmazione")`.
- **Fetta 6**: alla modifica di un interesse va aggiunta la rivalutazione delle notizie degli ultimi 7 giorni (`INT-07`), che nella fetta 1 non c'è.
- **Quota**: alla prima esecuzione la finestra è di 7 giorni. Con categorie arXiv molto attive (es. `cs.AI`, migliaia di paper a settimana) il pre-filtro costa molte chiamate: conviene scegliere categorie precise o un modello locale per il pre-filtro (`LLM-03`).
