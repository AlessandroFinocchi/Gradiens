# Il pre-filtro dei paper arXiv si ferma quando i promossi riempiono il tetto

**Stato**: accettato (decisione dell'utente del 13 novembre 2026, n. 8 di
[decisioni.md](../miglioramenti/decisioni.md)); implementato il 15 novembre 2026 in `esecuzione/esecutore.py`
(`_prefiltra`), con il tetto a 30 della decisione 9 (migrazione `0012`). PRD aggiornato (`ARX-02`, `ESE-04`).

Oggi tutti i paper nuovi delle categorie seguite passano dal pre-filtro (`ARX-02`) e solo dopo si applica
il tetto (`ARX-03`): i paper promossi oltre il tetto vengono scartati senza valutazione. Nelle esecuzioni
9 e 10 erano 633 paper su 677 e 376 su 412, e il loro pre-filtro è costato circa il 34% e il 43% di tutti
i token. Per arXiv il pre-filtro promuove il 94-95% dei paper, e il tetto fissa comunque quanti se ne
valutano: il pre-filtro non riduce mai le valutazioni, serve solo a tenere fuori dal tetto il 5-6% di
paper non pertinenti. L'analisi completa è in
[06b-consumo-di-token.md](../miglioramenti/06b-consumo-di-token.md), scheda 6b-2.

Per questo i paper passeranno dal pre-filtro dal più recente, a blocchi, e ci si fermerà quando i promossi
raggiungono il tetto. I paper non pre-filtrati entrano nel registro delle notizie già viste, come oggi
quelli oltre il tetto, e non si riprendono. Siti e video continuano a passare tutti dal pre-filtro.

Nuovo testo di `ARX-02`: "I paper nuovi delle categorie scelte passano dal pre-filtro dal più recente, a
blocchi, finché i promossi raggiungono il tetto (`ARX-03`); gli altri entrano nel registro delle notizie
già viste."

## Opzioni considerate

- **Lasciare così**: scartata. Il tetto resta fermo a 10 perché il pre-filtro consuma la quota che
  servirebbe a valutare più paper.
- **Nessun pre-filtro per arXiv, solo il tetto per data**: scartata per ora. Risparmia 1,6-3,4 punti in
  più, ma i paper non pertinenti (5-6%) e quelli riconosciuti come sponsorizzati entrerebbero nel tetto.
- **Tetto prima del pre-filtro** (si tagliano i paper più recenti e poi si pre-filtrano): scartata. Il
  tetto conterebbe paper non filtrati e se ne valuterebbero circa il 6% in meno; cambierebbe `ARX-03`.
- **Tetto per pertinenza invece che per data**: rimandata. Richiede di pre-filtrare tutti i paper con un
  punteggio, costa circa 104.000 token a esecuzione e il vantaggio non è misurato (scheda 6b-7).

## Conseguenze

- Risparmio stimato dal modello del consumo: circa il 44% dei token dell'esecuzione 10 e il 34% della 9.
  Con quel risparmio il tetto arXiv può salire da 10 a circa 50 a parità di consumo (stima prudente).
- I paper valutati sono gli stessi di oggi se il pre-filtro risponde allo stesso modo: sono "i più recenti
  tra quelli che passano il pre-filtro". Con un LLM vero il verdetto su un paper può dipendere dagli altri
  paper del blocco: differenze possibili, non misurate.
- `oltre_tetto` conterà i paper non pre-filtrati più i promossi in eccesso, così la segnalazione "tetto
  raggiunto" del resoconto e della CLI (`ARX-03`) e la somma dei contatori di `ESE-11` continuano a
  tornare. `scartate_prefiltro` per arXiv conterà solo i paper davvero pre-filtrati.
- Vanno precisati `ESE-04` (il pre-filtro non legge più tutte le notizie nuove) e la pagina Aiuto.
- Nei giorni con pochi paper promossi i giri di pre-filtro vanno in sequenza: l'esecuzione può durare di
  più. Il totale della fase di pre-filtro non è noto all'inizio, quindi l'avanzamento si aggiorna a ogni
  giro.
- Se un blocco fallisce non si lanciano giri nuovi; i paper non filtrati restano non visti e si
  riprendono all'esecuzione successiva, come oggi. Contano come `errori`, così la somma di `ESE-11` torna.
- Un giro lancia i blocchi che potrebbero riempire il tetto (⌈mancanti / 30⌉), al massimo 3 insieme
  (`GIRO_PREFILTRO`). Siti e video si pre-filtrano in blocchi propri, senza paper, in parallelo ai giri.
- Tetto a 30 (decisione 9): la migrazione `0012` porta a 30 il vecchio predefinito (50) e il tetto usato fino
  ad allora (10); un tetto scelto diverso resta com'è.
- La modifica sta tutta nell'esecutore: l'interfaccia dei provider LLM non cambia
  ([ADR 0006](0006-claude-code-come-provider-predefinito.md)) e non c'è differenza tra Windows e Linux.
