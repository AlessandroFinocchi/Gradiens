# La dashboard è generata dal server con FastAPI, Jinja2 e htmx

La dashboard è fatta di pagine HTML composte dal server Python, con FastAPI e i template Jinja2. Per gli aggiornamenti parziali (cuore, filtri, avanzamento dell'esecuzione, approvazione delle proposte) si usa `htmx`, che sostituisce pezzi di pagina senza JavaScript scritto a mano. Dashboard, bot Telegram e programmazione giornaliera girano in un unico processo asincrono. Così `gradiens avvia` e `gradiens spegni` gestiscono una sola cosa, e il vincolo "una esecuzione alla volta" (`ESE-02`) si controlla in un solo punto.

## Opzioni considerate

- **API JSON + SPA (React o Svelte con Vite)**: scartata. Riporta Node e un passo di compilazione, duplica i modelli tra Python e TypeScript e costa molto di più da imparare.
- **Framework UI in solo Python (NiceGUI, Streamlit)**: scartata. Rende difficile ottenere l'aspetto richiesto (stile Claude Code, sidebar a icone espandibile, filtri combinati). Streamlit, inoltre, rilancia lo script a ogni interazione e si concilia male con le esecuzioni lunghe.

## Conseguenze

- Niente Node né passi di compilazione: `htmx` è un singolo file JavaScript salvato nella repository, non scaricato da una CDN, così la dashboard funziona anche senza internet.
- Le preview HTML della fase 3 diventano la base dei template Jinja2.
- Interazioni molto ricche nel browser costerebbero più fatica che in una SPA. Per un'app di lettura non si prevede che servano.
