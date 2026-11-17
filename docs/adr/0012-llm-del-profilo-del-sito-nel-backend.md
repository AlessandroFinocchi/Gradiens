# L'aiuto dell'LLM al profilo di un sito passa da un modulo del backend

**Stato**: accettato, implementato il 17 novembre 2026 (decisioni dell'utente del 13 e 14 novembre 2026, n. 19 e
33 di [decisioni.md](../miglioramenti/decisioni.md), e n. 58 per i dettagli). Doveva venire dopo le correzioni
deterministiche della ricerca sui siti; l'utente ha scelto di farlo prima (decisione 58).

`WEB-04` permette all'LLM di intervenire alla creazione del profilo di un sito, ma oggi nessuna chiamata LLM
esiste fuori dall'esecuzione. L'utente ha deciso che l'LLM potrà aiutare, su richiesta (un bottone alla
creazione o rigenerazione del profilo), a scegliere le sezioni utili e a proporre esclusioni quando le regole
automatiche falliscono, con un tetto di 10.000 token per sito. Restava da decidere dove vive quel codice,
perché tocca due confini di [struttura.md](../architettura/struttura.md): la dashboard non chiama i provider
LLM, e il codice di scraping non contiene prompt né gestione della quota. L'analisi è in
[03-revisione-architetturale.md](../miglioramenti/03-revisione-architetturale.md), scheda A-07 e proposta P-1.

Le chiamate LLM fuori dall'esecuzione stanno in un modulo di `esecuzione/`, che usa la fabbrica dei provider
con il ruolo di elaborazione. `fonti/siti` fornisce solo funzioni senza LLM: ridurre la pagina a un albero di
link e convalidare la risposta. La dashboard chiama il modulo, mai il provider. Il tetto di token si applica
prima della chiamata, accorciando l'ingresso, e si controlla dopo con i token restituiti dal provider.

## Opzioni considerate

- **Chiamata dalla rotta della dashboard**: scartata. Rompe il confine "la dashboard non chiama i provider".
- **Funzione `chiedi` passata al codice dei siti**: scartata. Porterebbe prompt, quota e tetto nel codice di
  scraping.
- **Parametro di limite nell'interfaccia dei provider**: scartata. Darebbe un tetto rigido, ma allargherebbe
  l'interfaccia di ogni provider presente e futuro per un solo chiamante
  ([ADR 0006](0006-claude-code-come-provider-predefinito.md)).

## Conseguenze

- Il tetto di 10.000 token è una stima, non un limite rigido: l'ingresso si accorcia contando i caratteri, e
  il consumo vero si conosce solo dopo la chiamata.
- L'interfaccia dei provider non cambia: l'aiuto funziona con qualunque provider configurato per
  l'elaborazione.
- Lo scraping resta fatto solo dal codice dell'applicazione e l'LLM non interviene mai durante le esecuzioni
  (`WEB-04`, `WEB-05`).
- Nessuna differenza tra Windows e Linux.

## Come è stato implementato

- `fonti/siti/aiuto.py`: `leggi_albero` rilegge la pagina iniziale (una pagina, con i suoi redirect e robots.txt) e la riduce ai
  link interni raggruppati per forma dell'indirizzo; `convalida` tiene solo indirizzi dell'albero e del perimetro
  e restituisce le differenze rispetto al profilo (sezioni da aggiungere e da togliere, esclusioni nuove).
- `esecuzione/aiuto_profilo.py`: `aiuta` accorcia l'albero togliendo gli ultimi gruppi finché la stima (caratteri
  divisi per 2,35, più 1.300 token di carico fisso e 2.700 di uscita; l'uscita viene dalla
  [prova vera](../miglioramenti/dati/prova-aiuto-profilo-2026-11-17.md), la 6a-12 ne stimava 700) sta nei 10.000 token, chiama il provider e il
  modello dell'elaborazione, scrive nel log i token veri e dice se hanno superato il tetto. Prompt e schema in
  `esecuzione/prompt.py`.
- Dashboard: bottone "Chiedi aiuto all'LLM" per ogni sito; le proposte si mostrano con una casella ciascuna e si
  applicano solo con "Applica", come modifiche manuali (restano dopo una rigenerazione, `WEB-25`). Il profilo
  mostra anche le sezioni.
- Togliere una sezione si propone solo per quelle che l'LLM ha visto tra i link della pagina iniziale, e la casella
  parte senza spunta: una sezione tolta si riaggiunge solo con un'altra richiesta. Corretto nella rilettura del 17
  novembre 2026: prima si proponeva, già spuntata, di togliere anche le sezioni che l'LLM non poteva vedere.
- Il tetto vale per ogni richiesta; l'LLM propone solo sezioni ed esclusioni, non la forma degli indirizzi degli
  articoli della scheda 6a-12, che il profilo non sa salvare (decisione 58).
