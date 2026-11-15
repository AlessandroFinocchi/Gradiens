# L'aiuto dell'LLM al profilo di un sito passa da un modulo del backend

**Stato**: accettato, da implementare (decisioni dell'utente del 13 e 14 novembre 2026, n. 19 e 33 di
[decisioni.md](../miglioramenti/decisioni.md)). Si implementa per ultimo, dopo le correzioni deterministiche
della ricerca sui siti.

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
