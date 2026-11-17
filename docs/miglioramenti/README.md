# Miglioramenti di Gradiens: stato

Dal 12 al 15 novembre 2026 un'analisi in sei fasi ha prodotto solo documenti (proposte, piani, ADR); dal 15 al 17
novembre le parti decise sono state implementate, un pezzo per conversazione. Le scelte dell'utente sono in
[decisioni.md](decisioni.md) (1-62). Nel codice "decisione N" rimanda a quel registro; quelle dell'intervista sui
requisiti si scrivono "decisione N dei requisiti".

Questa pagina dice cosa è fatto, cosa resta aperto e dove trovare i dettagli. Aggiornata il 17 novembre 2026.

## I documenti dell'analisi

| Fase | Documento | Contiene |
|---|---|---|
| 1 | [mappa-moduli.md](../architettura/mappa-moduli.md) | moduli, flussi, dove si usa l'LLM: fotografia del codice al 12-15 nov |
| 2 | [02-test-e-copertura.md](02-test-e-copertura.md) | copertura ([dati](dati/copertura-2026-11-13.md)), 50 test di caratterizzazione T-nn, sospetti bug S-01…S-39 |
| 3 | [03-revisione-architetturale.md](03-revisione-architetturale.md) | problemi A-01…A-15, passi di refactoring R-nn, proposte P-1…P-3 |
| 4 | [04-debugging.md](04-debugging.md) | 15 schede di debugging, prove che deve raccogliere l'utente |
| 5 | [05-dipendenze-e-stile.md](05-dipendenze-e-stile.md) | dipendenze, Claude Code, linter e formatter |
| 6a | [06a-ricerca-sui-siti.md](06a-ricerca-sui-siti.md) | proposte 6a-1…6a-13 sulla ricerca delle notizie nei siti |
| 6b | [06b-consumo-di-token.md](06b-consumo-di-token.md) | misure e proposte 6b-1…6b-16 sulla quota LLM |
| 6c | [06c-dashboard-da-internet.md](06c-dashboard-da-internet.md) | accesso da fuori casa |

Questi documenti non sono stati riscritti dopo le decisioni: la nota "Decisioni dell'utente" o la sezione "Esito
della rilettura" in testa vale sul testo sotto. Codice e test citano le loro sigle (S-nn, T-nn, "scheda N"), quindi
non vanno spostati né rinominati. I dati delle prove vere stanno in [dati/](dati/).

## Fatto

| Cosa | Decisioni e ADR | Commit |
|---|---|---|
| I video YouTube segnalati come sponsorizzati si valutano comunque (S-01, `WEB-23`) | 36 | `97e5d38` |
| Test T-01…T-10 (T-09 coperto dal test dei video); `pytest-cov` anche in CI | 23-26 | `6e0d507` |
| Refactoring R-02a: `FONTE_DI_TIPO` e `SPENTO` una volta sola in `dati/` | 28 | `09735ad` |
| Pre-filtro arXiv fino al tetto, tetto a 30 (`ARX-02`, `ESE-04`) | [ADR 0010](../adr/0010-prefiltro-arxiv-fino-al-tetto.md), 8-9 | `4fdbf25` |
| Profilo tenuto se la rigenerazione non trova niente (S-34); voci di altri domini fuori dai feed; traduzioni escluse; bottone "Togli" per gli esclusi | 18, 21, 22 | `210bb5a` |
| Raccolta incrementale dei siti: "coperto fino a", stato "copertura parziale" (`WEB-26`) | [ADR 0011](../adr/0011-raccolta-incrementale-dei-siti.md), 17, 34, 37, 59, 60 | `9e275e3` |
| Schede 3 e 4: database bloccato (S-06, S-08); risposte dell'LLM di forma inattesa (S-02, S-04, S-05, S-07) | — | `173435c` |
| Schede 7 e 11: due avvii del bot (S-12); `/pausa` e `/riprendi` spiegati (`TG-10`) | 41 | `1085a0f` |
| Schede 8 e 14: redirect di robots.txt verso la rete di casa (S-32); un 5xx di robots.txt vieta il sito per 5 minuti | 39 | `d348741` |
| Schede 9 e 13: una sola esecuzione al ritorno all'ora solare (S-09); attesa della rete a 15 minuti (`ESE-01`) | 40 | `7ceebcf` |
| Scheda 12: `gradiens aggiorna` resta spento e lo dice; ruff come linter, anche in CI | 43, 47 | `231497a` |
| Versione di Claude Code a ogni esecuzione, errore di login che ferma l'esecuzione, prova di funzionamento quando la versione cambia | 45, 61 | `77a7363` |
| Dashboard da fuori casa con Tailscale Serve (`AMB-02`, `TG-03`) | [ADR 0013](../adr/0013-dashboard-da-fuori-casa-con-tailscale-serve.md), 50-57, 62 | `de20ea5` |
| Aiuto dell'LLM al profilo di un sito, su richiesta (`WEB-04`) | [ADR 0012](../adr/0012-llm-del-profilo-del-sito-nel-backend.md), 19, 33, 58 | da committare |

Prove vere fatte, con il permesso dell'utente: la prova di funzionamento di Claude Code 2.1.316 (1.764 token, 17
nov) e l'aiuto al profilo di redhotcyber (6.983 token, con un'uscita di 2.658 token contro i 700 stimati:
[dati](dati/prova-aiuto-profilo-2026-11-17.md)).

## Ancora aperto

- **Refactoring R-01, R-03, R-04, R-02b: non fatti** (decisione 28). Dovevano preparare l'esecutore prima di ADR 0010
  e 0011, che sono già nel codice; nel frattempo `esecuzione/esecutore.py` è passato da 466 a 604 righe. Da decidere
  di nuovo. Proposta: fare ogni passo solo subito prima della prossima modifica che tocca quel codice. Il formatter
  aspetta il refactoring (decisione 47), quindi dipende da questa scelta.
- **Decise, senza codice**: avvisi come errori nei test, dopo la pulizia delle connessioni non chiuse (decisione 48);
  il punto 4 della sezione 4.5 del documento 05 (campi documentati di `claude auth status`).
- **Senza una soluzione sicura** (schede 5 e 6 del documento 04): la migrazione del database in transazione (la
  variante provata fa perdere dati), insieme al cambio annunciato di `sqlite3` in Python 3.16, e la protezione dal
  secondo processo del servizio. Finché non c'è un test adatto, `dati/database.py` non va toccato.
- **Proposte in bozza, da discutere prima del codice**: 6a-2 (solo il rifiuto delle date future, decisione 16), 6a-3,
  6a-4, 6a-5, 6a-7, 6a-8, 6a-9, 6a-10; 6b-3, 6b-8, 6b-10; 6b-4, 6b-5, 6b-6 e 6b-12 dopo le misure; P-3 (le metriche
  salvate cambiano solo per aggiunta). La 6b-1 è rimandata (decisione 29).
- **Misure e prove autorizzate e non fatte**: M1-M6 sui token, a tempi separati (decisione 10, script in
  `scripts/misura/` per la decisione 14); la prova vera di yt-dlp (decisione 46). Dopo una settimana di metriche
  vere col tetto arXiv a 30 si valuta se salire a 50 (decisione 9).
- **Da fare a mano dall'utente**: i passi di Tailscale e la verifica dal telefono (pagina Aiuto, "Dashboard da fuori
  casa"); le prove elencate in [04-debugging.md](04-debugging.md), sezione "Che cosa deve raccogliere l'utente".
- **Non verificato dal vero**: tutto il ramo Windows del lavoro di novembre; Tailscale Serve; il testo di un errore
  di login di Claude Code (le parole riconosciute sono un'ipotesi); un vero ritorno all'ora solare.
- **Domande minori mai fatte**: tre della fase 2, elencate in [decisioni.md](decisioni.md) dopo la decisione 27.

## Stato delle proposte

Stati: bozza, accettata, fatta, scartata, non pianificata. Sforzi stimati (g = giorni, h = ore; S, M, L = piccolo,
medio, grande).

### 6b — Consumo di token

| Codice | Problema in breve | Raccomandazione | Sforzo | Stato |
|---|---|---|---|---|
| 6b-1 | Le metriche non separano cache, ragionamento, fase e tipo di fonte | Solo aggiunte | 0,5 g | rimandata (decisione 29) |
| 6b-2 | Il 43% dei token (es. 10) va al pre-filtro di paper poi scartati dal tetto | Pre-filtro dei paper fino a riempire il tetto | 1-1,5 g | **fatta** (ADR 0010) |
| 6b-3 | L'ingresso è scritto in cache a 1 ora e, tranne il prefisso, non riletto | Cache a 5 minuti (valore in quota: ipotesi) | 1-2 h | bozza |
| 6b-4 | Una chiamata per paper, quasi tutta carico fisso | Valutazione a lotti di 5 paper | 1-1,5 g | bozza, dopo la misura M3 |
| 6b-5 | Ragionamento sempre attivo su Haiku 5.5 | Effort basso e istruzione nel prompt | 0,5 g | bozza, dopo la misura M4 |
| 6b-6 | Circa 825 token aggiunti da Claude Code a ogni chiamata | Diagnosi, poi variabili d'ambiente | 0,5 g | bozza, dopo M1-M2 |
| 6b-7 | Il tetto sceglie per data, non per pertinenza | Misurare e decidere | 1-1,5 g | bozza, rimandata |
| 6b-8 | Sommario fino a 1.500 caratteri nel pre-filtro | Solo se `ARX-02` non cambiava | 1-2 h | bozza |
| 6b-10 | Taglio a 60.000 caratteri, trascrizioni lunghe | Misurare prima | 2-3 h | bozza |
| 6b-12 | Rivalutazioni, nuovi tentativi, `pronto` due volte | Solo `pronto` una volta, il resto dopo la misura | 2-3 h | bozza |
| 6b-9, 11, 13, 14, 15 | Blocchi, deduplicazione, modello, schema, argomenti | Lasciare così | — | bozza |
| 6b-16 | Modello locale, embedding, API a pagamento | Solo descritti (decisione 6) | — | non pianificata |

### 6a — Ricerca sui siti

| Codice | Problema in breve | Raccomandazione | Sforzo | Stato |
|---|---|---|---|---|
| 6a-1 | Nessun modo di misurare una modifica senza nuove richieste | Banco di misura | M | non pianificata (decisione 15) |
| 6a-11 | Profilo che diventa vuoto; niente anteprima, differenze | Protezione del profilo, poi il resto | S + M | protezione **fatta** (decisione 21); il resto bozza |
| 6a-4 | Feed di una sezione scartato (ACN: da 17 a 38 articoli in 7 giorni) | Accettare il feed linkato dalla sezione | S | bozza |
| 6a-5 | Un feed in ritardo ferma la cascata (redhotcyber) | Leggere sempre news sitemap o API | S-M | bozza; traduzioni escluse **fatto** (decisione 22) |
| 6a-2 | `lastmod` come data certa; date future accettate | Rifiutare le date future | S + M | `lastmod` scartata (decisione 16); date future bozza |
| 6a-7 | Sitemap lette alla cieca | Figlie giuste, news sitemap prima | S-M | bozza |
| 6a-3 | La fonte non conosce il registro delle viste | Parametro `viste` | M | bozza |
| 6a-9 | HTML: non articoli, pagine per la data spese male | `non_articolo` più severo | M | bozza |
| 6a-6 | Ogni esecuzione rifà tutta la finestra | Raccolta incrementale | L | **fatta** (ADR 0011) |
| 6a-13 | Candidate inutili al pre-filtro | Voci di altri domini fuori | S-M | **fatta** (decisione 18); regola sui titoli scartata (decisione 20) |
| 6a-8 | Piattaforme riconosciute male | Più segnali, API paginata | S + M | bozza |
| 6a-10 | Cache solo in memoria | Cache su disco con richieste condizionali | S-M | bozza |
| 6a-12 | Euristiche che falliscono senza aiuto | LLM alla creazione del profilo, su richiesta | M | **fatta** (ADR 0012, decisioni 19 e 58) |

Le proposte 6a che trovano più articoli consumano parte della quota che la 6b-2 ha liberato (stima: 60-110 mila
token per esecuzione su circa 226 mila; decisione 12).

## Regole nate da questo lavoro

- I dati di una misura che non si può ripetere si copiano subito in `docs/miglioramenti/dati/`: la cartella
  temporanea della sessione si svuota a ogni riavvio del PC (è successo il 13 novembre).
- I sottoagenti a effort xhigh consumano molta quota (una bozza di proposta circa 500.000 token, una rilettura
  250-300.000): meglio pochi alla volta, o nessuno.
- Una proposta contiene: problema con `file:riga`, opzioni con compromessi, raccomandazione, effetto su Windows e
  Linux, passi piccoli e verificabili, test, rischi, stima dello sforzo. Solo fatti verificati; ipotesi e stime
  dichiarate.
- Prima di consumare quota LLM, installare pacchetti o fare molte richieste ai siti si chiede all'utente. I commit
  li fa l'utente.
