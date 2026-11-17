# 6b — Consumo di token per alzare il tetto delle notizie

**Data**: 12-13 novembre 2026. **Stato**: chiusa, decisioni 8-14; cosa è fatto e cosa resta in [README.md](README.md). **Fase**: 6b di [README.md](README.md).

> **Decisioni dell'utente (13 novembre 2026)**, numeri 8-14 di [decisioni.md](decisioni.md): `ARX-02` cambia e la 6b-2 è accettata ([ADR 0010](../adr/0010-prefiltro-arxiv-fino-al-tetto.md)); tetto arXiv a 30, poi si valuta 50; misure M1-M6 autorizzate a tempi separati, M7 no; perdita accettabile 2% nel pre-filtro e 5% nella valutazione; la quota liberata va ai siti senza tetto per sito; i video YouTube esclusi come sponsorizzati erano voluti (difetto da analizzare nella fase 4: corretto quello, i video costeranno quota); script di misura in `scripts/misura/`. Il testo sotto è la bozza su cui sono state prese le decisioni e non è stato riscritto.

**Base del lavoro**
- [mappa-moduli.md](../architettura/mappa-moduli.md), sezioni A2, A6 e C3 (verificata contro il codice): qui non si ripete, si rimanda.
- Codice di `src/gradiens` al commit `3868260`; i percorsi `file:riga` sono relativi a `src/gradiens/`.
- Database `.gradiens/gradiens.db` letto in sola lettura (esecuzioni 9 e 10 del 10 e 11 novembre).
- La misura con 8 chiamate vere a Claude Code del 12 novembre 2026 (decisione 5 di [decisioni.md](decisioni.md)).
- Documentazione ufficiale di Anthropic letta il 12 novembre 2026 e in parte riverificata il 12-13 novembre dal coordinatore (sezione 7).
- Vincoli: decisione 6 (si pianificano solo le leve dentro l'abbonamento Claude Code e quelle senza LLM; modelli locali, embedding e API a pagamento sono solo descritti), ADR 0006, Windows e Linux insieme, dati solo in `.gradiens/` e `.env` (PER-02, PER-03).

**Questo documento è l'unica traccia dei calcoli.** I file temporanei della prima stesura (script, JSON grezzi della misura, risposta dell'API di arXiv) sono andati persi con il riavvio del PC del 13 novembre 2026. I conti sono stati rifatti il 13 novembre con script nuovi nella cartella temporanea della sessione (anch'essi non conservati). La sezione 2.3 dà parametri, formule ed esempio svolto a mano: bastano per rifare ogni cifra.

**Come leggere le cifre**: ogni numero porta l'origine tra parentesi: *(misura)* = le 8 chiamate vere; *(DB)* = database; *(metriche)* = `esecuzioni.metriche`; *(codice)*; *(fonte)* = documentazione ufficiale; *(modello)* = ricavato dal modello della sezione 2; *(stima)* e *(ipotesi)* = non verificato. Le cifre sono in token grezzi (come li salva l'app) e, dove serve, in "unità pesate" (sezione 2.1).

---

## Riepilogo

### Che cosa si è scoperto

1. **Tra il 41% e il 52% del consumo è pre-filtro, e la parte più grossa è sprecata.** Esecuzione 10: 268.402 token su 516.750 al pre-filtro (51,9%); esecuzione 9: 451.965 su 1.112.754 (40,6%) *(metriche)*. Il pre-filtro dei paper arXiv poi scartati dal tetto vale 43,1% (es. 10) e 33,5% (es. 9) di **tutti** i token *(modello, sezione 2.4)*.
2. **Per arXiv il pre-filtro non filtra.** Promuove il 94-95% dei paper (es. 10: 386 su 412; es. 9: 643 su 677) e la valutazione ne approva il 95% (19 su 20 sopra la soglia 60; pertinenza massima mediana 79-85) *(metriche, DB)*. Il tetto fissa il numero di valutazioni (`paper[:tetto]`, `esecutore.py:279-280`): il pre-filtro di arXiv non ne riduce mai nessuna. Serve solo a tenere fuori dal tetto il 5-6% di paper non pertinenti, e per questo oggi si pre-filtra ogni paper. In pratica il tetto, per data, sceglie i paper. Senza tetto il pre-filtro non si ripagherebbe comunque: costa più di quanto fa risparmiare se scarta meno del 13% *(calcolo, scheda 6b-2)*.
3. **Il resto del consumo** (percentuali del totale, es. 10): testo delle notizie in ingresso 57% e carico fisso per chiamata 23% *(modello)*; ragionamento (thinking) 14% e risposta utile 6% *(stima: ricavati per differenza, con 633-580 token di risposta a valutazione e 70 token per notizia negli argomenti assunti per analogia)*. In unità pesate il ragionamento sale a circa 29% *(stima)*.
4. **La cache riusa solo il prefisso** (strumento dello schema e prompt di sistema, 1,1-1,3 mila token a chiamata). Tutto il resto, messaggio compreso, è scritto nella cache a 1 ora e non viene riletto *(misura)*. Con i prezzi dell'API le scritture sarebbero il 56% delle unità pesate *(modello)*.
5. **Nessuno sa come la quota dell'abbonamento pesa i token**: le pagine ufficiali non danno pesi (sezione 2.2). Per questo ogni stima è data in due unità. La proposta con l'effetto maggiore (6b-2) vale in entrambe.
6. **Campi della risposta di `claude -p`.** `usage.cache_creation.ephemeral_1h_input_tokens` e `ephemeral_5m_input_tokens` sono documentati (code.claude.com/docs/en/prompt-caching). `usage.output_tokens_details.thinking_tokens`, `modelUsage.<modello>.thinkingTokens`, `costBasis` e l'evento `rate_limit_event` di `stream-json` li ho osservati il 12 novembre nei JSON grezzi poi persi: **non sono descritti nelle pagine ufficiali lette** e vanno riconfermati con la prima chiamata di misura. Su questi poggiano la scomposizione del ragionamento e la percentuale d'uso delle finestre di 5 ore e 7 giorni.
7. **Non serve**: deduplicazione (0 coppie di titoli originali quasi uguali tra le notizie di siti mostrate), blocchi più grandi (−2,8%), processo `claude` sempre aperto (a prezzi dell'API conviene solo per le prime 6-8 notizie, in token grezzi mai), cambio di modello (Haiku 4.5 costa 10 volte a listino).
8. **Rischio da seguire (non è una proposta 6b).** La pagina headless (letta il 13 novembre) dice che `--bare` "è la modalità consigliata per le chiamate da script e SDK e diventerà il predefinito per `-p` in una versione futura"; in modalità bare Claude Code non legge le credenziali OAuth dell'abbonamento (serve `ANTHROPIC_API_KEY`). Se diventa il predefinito, le chiamate `claude -p` di Gradiens con l'abbonamento (ADR 0006) potrebbero smettere di funzionare finché non si passa un'opzione esplicita. Da verificare a ogni aggiornamento di Claude Code.

### Combinazione raccomandata (dentro la decisione 6)

6b-1 (metriche) → 6b-2 (pre-filtro arXiv "fino a riempire il tetto") → 6b-3 (cache a 5 minuti) → dopo le misure M3 e M4: 6b-4 (valutazione dei paper a lotti) e 6b-5 (ragionamento ridotto); in parallelo la diagnosi 6b-6 del contesto che Claude Code aggiunge a ogni chiamata.

### Di quanto si può alzare il tetto arXiv (a parità del consumo dell'esecuzione 10, tetto oggi 10)

| Scenario | Leve e ipotesi | Tetto sostenibile (token grezzi / unità pesate) |
|---|---|---|
| Prudente | 6b-2 e 6b-3; valutazione singola; ragionamento invariato | 56 / 48-62 (circa 50) |
| Intermedio | + lotti da 5 paper (ragionamento per paper invariato) e effort basso (ragionamento −27%, una sola prova) | 80-87 / 68-84 |
| Ottimistico | nessun pre-filtro arXiv (ARX-02 tolto per arXiv), lotti da 10, ragionamento per paper 700 o 350 (**ipotesi senza misura**), con o senza effort basso | 119-151 / 92-139 |

Con il consumo della esecuzione 9 (più articoli di siti) i tetti sono 75-248 (sezione 4.2). Valutare **tutti** i 412 paper della finestra costerebbe 2,0-4,0 volte il budget in token grezzi: il tetto resta. La sola 6b-2 libera circa 226.000 token (−43,8%): bastano per portare il tetto da 10 a 56 (46 paper in più) oppure per circa 85 notizie nuove di siti in più (sezione 4.3).

### Tabella delle proposte

| Codice | Problema in breve | Raccomandazione | Risparmio stimato (grezzi / pesate) | Effetto sulla qualità | Sforzo | Rischio |
|---|---|---|---|---|---|---|
| 6b-1 | Le metriche non separano cache, ragionamento, fase e tipo | Fare subito, solo aggiunte | 0 (serve a misurare) | nessuno | 0,5 g | basso |
| 6b-2 | 43% dei token (es. 10) va al pre-filtro di paper poi scartati dal tetto | Fare: pre-filtro dei paper per data fino a riempire il tetto; cambia ARX-02 | −43,8% / −39,7% (es. 10); −34,2% / −31,6% (es. 9) | stessi paper di oggi, se il pre-filtro è deterministico e non dipende dagli altri paper del blocco | 1-1,5 g | basso |
| 6b-3 | Tutto l'ingresso è scritto in cache a 1 ora (2 volte il prezzo base) e, tranne il prefisso, non riletto | Fare dopo 6b-1: cache a 5 minuti nel provider Claude Code | 0 / −21% se la quota segue i prezzi (ipotesi) | nessuno | 1-2 h | basso |
| 6b-4 | Una chiamata per paper: 1,9 mila token fissi su 2,4 mila di ingresso | Dopo M3: valutazione a lotti di 5 paper | −38% per paper / −12%; fino a −59% / −44% se cala il ragionamento (ipotesi) | da misurare (M3) | 1-1,5 g | medio |
| 6b-5 | Ragionamento: 14% dei token, 29% delle pesate (stima) | Dopo M4: effort basso e istruzione "senza spiegare" | −3,7% / −7,8% (ragionamento −27%, una prova) | da misurare (M4) | 0,5 g + misura | medio |
| 6b-6 | Circa 825 token aggiunti da Claude Code a ogni chiamata, 605 riscritti ogni volta | Diagnosi (M1, M2), poi variabili d'ambiente | fino a −7,5% / −6,3% (ipotesi) | nessuno | 0,5 g | basso |
| 6b-7 | Il tetto sceglie per data, non per pertinenza | Non ora: misurare (M5) e decidere | costa circa 104.000 grezzi (circa 20 paper di tetto in meno) | migliora (da misurare) | 1-1,5 g | medio |
| 6b-8 | Sommario fino a 1.500 caratteri nel pre-filtro | Solo se ARX-02 non cambia: 500 caratteri | −21,8% con 500, −34,9% solo titolo (es. 10); 1,6% dopo 6b-2 | possibili perdite (M6) | 1-2 h | medio |
| 6b-9 | Blocchi di 30 (pre-filtro) e 40 (argomenti) | Lasciare così | −2,8% / −1,3% con blocchi da 60 | — | — | — |
| 6b-10 | Taglio a 60.000 caratteri; trascrizioni YouTube lunghe | Misurare prima (6b-1) | non misurabile oggi | copertura dei riassunti | 2-3 h | basso |
| 6b-11 | Deduplicazione prima dell'LLM | Non fare | 0 | violerebbe DUP-03 | — | — |
| 6b-12 | Rivalutazioni, nuovi tentativi, "rate limit", `pronto` due volte | Solo `pronto` una volta; il resto dopo la misura | 0 osservato (nessuna rivalutazione nel DB) | nessuno | 2-3 h | basso |
| 6b-13 | Modello per fase | Lasciare l'alias `haiku` (Haiku 5.5) | Haiku 4.5: 10 volte a listino (peso nella quota ignoto) | — | — | — |
| 6b-14 | Carico fisso: schema, processo aperto, più notizie per chiamata | Non fare ora; lotti anche per i siti dopo 6b-4 | senza schema −8,0% / −2,6%; siti a lotti di 3: −8,7% | parse del testo | — | — |
| 6b-15 | Argomenti e proposte | Lasciare così | blocchi da 80: −0,3% | — | — | — |
| 6b-16 | Modello locale, embedding, API a pagamento | Solo descritti (decisione 6) | pre-filtro locale: al massimo 14,5% dopo 6b-2 | — | — | — |

**Che cosa serve dall'utente**: le decisioni D1-D7 della sezione 6 (la prima: cambiare ARX-02) e il permesso per le misure M1-M7 della sezione 4.5 (M1-M6: circa 0,6-0,8 di un'esecuzione tipo; M7: 0,6-1,2).

---

## 1. Inventario delle chiamate LLM

### 1.1 Come sono state ricavate le dimensioni

- **Caratteri per token**: 2,35 per testo italiano in JSON con Haiku 5.5 *(misura: messaggio da 12.121 caratteri più sistema da 758 caratteri = circa 5.470 token)*. Per gli abstract in inglese la taratura sulle esecuzioni dà **3,05** *(modello: 3,07 sulla 10; 3,04 sulla 9)*. La pagina dei prezzi dice che i modelli dalla serie 4.7 in poi producono circa il 30% di token in più per lo stesso testo. Nella misura il totale in ingresso di Haiku 5.5 è il 33% più alto di quello di Haiku 4.5 (6.785 contro 5.113), ma i totali comprendono contesto e prompt degli strumenti diversi per modello: non è un rapporto puro tra tokenizzatori.
- **Lunghezze dei testi di arXiv**: 1 richiesta all'API pubblica di arXiv il 12 novembre 2026 (200 paper più recenti di una categoria generica, non quelle seguite dall'utente). La risposta non è conservata (persa il 13 novembre): restano queste statistiche. Titolo: media 83 caratteri, mediana 83, p90 113. Abstract: media 1.442, mediana 1.430, p10 1.011, p90 1.867, massimo 1.920; il 44% supera i 1.500 caratteri del pre-filtro (`esecuzione/prompt.py:12`). Media di `min(abstract, N)` per N = 0, 150, 300, 500, 800, 1.000, 1.500: 0, 150, 300, 499, 794, 984, 1.334. Nel database i 19 paper mostrati hanno abstract medio 1.365 (es. 9) e 1.551 (es. 10).
- **Riassunti salvati** *(DB, 135 notizie mostrate dalle es. 9 e 10)*: media pesata 1.283 caratteri; 19 paper 1.178; 116 notizie di siti 1.300. Per esecuzione: es. 9, paper 1.107 (9) e siti 1.289 (82); es. 10, paper 1.241 (10) e siti 1.328 (34). `titolo_it` presente nei 19 paper (88-95 caratteri) e in 38 notizie di siti su 116.
- **Articoli di siti e video**: il contenuto non è salvato; le lunghezze si ricavano dall'ingresso dell'elaborazione (sezione 2.3).

### 1.2 Che cosa contiene ogni chiamata

Tutte passano da `Provider.chiedi(sistema, messaggio, schema, modello)` (`llm/base.py:29`) e da `ClaudeCode._una_chiamata` (`llm/claude_code.py:85-111`); parallelismo, tentativi, timeout ed errori sono in [mappa A2](../architettura/mappa-moduli.md#a2-flusso-di-unesecuzione-completa), qui non si ripetono. Quattro soli punti chiamano `chiedi` (verificato con `grep`): `esecutore.py:299`, `:334`, `:370`, `:389`.

| # | Fase | Chiamata | Ruolo e modello | Prompt di sistema | Messaggio | Schema |
|---|---|---|---|---|---|---|
| 1 | Pre-filtro | `esecuzione/esecutore.py:389-390` (`_prefiltra`, `:381-416`) | prefiltro, `haiku` (`dati/modelli.py:31-34`) | `prompt.py:24-34`: ruolo, interessi con id (`[id] nome: descrizione` più raffinamento), "Nel dubbio includi la notizia", istruzione sugli sponsorizzati | `prompt.py:47-49`: lista JSON `{id, titolo, sommario[:1500]}` per al massimo 30 notizie | `prompt.py:37-44` (191 caratteri): `pertinenti`, `sponsorizzate` |
| 2 | Valutazione e riassunto | `esecutore.py:299-301` (`elabora`, `:291-319`) | elaborazione, `haiku` | `prompt.py:52-64`: interessi, fasce di pertinenza, riassunto di 3-6 frasi, `titolo_it` | `prompt.py:88-89`: `{tipo, fonte, titolo, testo}` per **una** notizia; `testo` = contenuto, il sommario non si manda | `prompt.py:67-85` (368 caratteri): `punteggi[]`, `riassunto`, `titolo_it` |
| 3 | Argomenti | `esecutore.py:334-336` (`_argomenti`, `:325-354`) | elaborazione | `prompt.py:92-106`: definizione di argomento più elenco `[id] nome` degli argomenti recenti (al massimo 100, ricalcolato a ogni blocco, `esecutore.py:332`) | `prompt.py:120-122`: `{id, titolo_it o titolo, riassunto[:600]}` per 40 notizie | `prompt.py:109-117` (264 caratteri) |
| 4 | Proposta di raffinamento | `esecutore.py:370` (`_proposte`, `:356-379`) | elaborazione | `prompt.py:130-141`: nome, descrizione, raffinamento attuale | `prompt.py:125-127`, `:169-170`: al massimo 10 notizie con il Cuore, `riassunto[:600]` | `prompt.py:144` (100 caratteri) |
| 5 | Proposta di interesse nuovo | `esecutore.py:370` (compito aggiunto a `:362-366`) | elaborazione | `prompt.py:147-159`: elenco degli interessi | `prompt.py:173-176`: al massimo 10 notizie con il Cuore e le loro pertinenze | `prompt.py:162-166` (134 caratteri) |

### 1.3 Quanto pesa ogni chiamata

Dimensioni con gli interessi veri (3 interessi con descrizioni brevi: 181 caratteri in tutto, nessun raffinamento) *(codice, DB)*. I token del sistema sono a 2,35 caratteri per token.

| # | Sistema (caratteri, token) | Messaggio tipico | Chiamate in funzione delle notizie | Ingresso per chiamata (token) | Uscita per chiamata (token) |
|---|---|---|---|---|---|
| 1 Pre-filtro | 758, circa 323 | voce arXiv 1.462 caratteri (circa 479 token); voce di sito 393 caratteri (circa 167); blocco da 30: 12-14 mila token | ⌈(arXiv + siti + video) / 30⌉; es. 10: 17, es. 9: 29 | 14.064 (es. 10), 13.995 (es. 9) *(metriche)* | 1.724 (es. 10), 1.590 (es. 9) *(metriche)* |
| 2 Valutazione | 1.028, circa 437 | paper: 1.585 caratteri (circa 520 token); articolo di sito: 1.750 (es. 10) e 2.920 (es. 9) token *(modello)*; massimo 60.000 caratteri | una per notizia che supera pre-filtro e tetto: 45 (es. 10), 100 (es. 9) | paper circa 2.380; sito 3.600-4.800 | paper circa 1.640, sito circa 1.700: 53 di struttura, circa 580 (paper) o 630 (siti) di risposta e circa 1.000 di ragionamento *(stima)* |
| 3 Argomenti | 756 più 46 per ogni argomento (53 argomenti: circa 3.200, 1.360 token) | 40 notizie da 720 caratteri (circa 12.300 token) | ⌈mostrate / 40⌉: 2 (es. 10), 3 (es. 9) | circa 15.000 il primo blocco | circa 2.900 (stima: 137 più 40 × 70) |
| 4 Raffinamento | 678, circa 289 | fino a 10 × 685 caratteri (circa 2.900 token) | una per interesse con 3 Cuori nuovi (`dati/proposte.py:15`): 0 nelle es. 9 e 10 | circa 4.500 (stima) | circa 300-1.000 (stima) |
| 5 Interesse nuovo | 943, circa 401 | fino a 10 × 745 caratteri (circa 3.200 token) | 0 o 1 | circa 5.000 (stima) | circa 300-1.000 (stima) |

Le chiamate 4 e 5 non sono mai partite nelle esecuzioni 9 e 10 (nel DB c'è 1 Cuore su 146 notizie): i loro numeri sono stime dal codice, non misure.

**Chiamate dell'esecuzione 10**: 17 + 45 + 2 + 0 = 64; **esecuzione 9**: 29 + 100 + 3 + 0 = 132 *(codice, metriche, log: le metriche non contano le chiamate; si ricavano da ⌈notizie/30⌉, notizie valutate, ⌈mostrate/40⌉ e proposte; nei file di log non c'è nessuna riga "nuovo tentativo" fino al 13 novembre)*. Durata 250,2 e 444,5 secondi *(metriche)*.

### 1.4 Fuori dall'esecuzione

Nessuna chiamata `chiedi`. L'unico altro uso di Claude Code è `claude auth status` (`stato_account`, `llm/claude_code.py:117-129`): due volte per esecuzione, una per ruolo anche se il provider è lo stesso (`esecutore.py:253-254`), e nella configurazione iniziale (`dashboard/rotte_configurazione.py:47`). Non interroga il modello: costo in token nullo *(ipotesi, non misurata: la misura non lo ha chiamato)*; costa un processo in più, 1-2 secondi. Il bot Telegram, l'analisi dei siti e la rigenerazione dei profili non usano LLM ([mappa A2](../architettura/mappa-moduli.md#a2-flusso-di-unesecuzione-completa)).

### 1.5 Il carico fisso per chiamata: la misura del 12 novembre

Metodo: 8 chiamate vere (38.405 token in tutto, ingresso più cache scritta più cache letta più uscita), Claude Code 2.1.316 su Linux, abbonamento dell'utente, alias `haiku` = `claude-haiku-5-5`. Stesse opzioni dell'app (`llm/claude_code.py:18-25`, `:86-92`): `-p --model haiku --system-prompt ... --json-schema ... --output-format json --tools "" --strict-mcp-config --safe-mode --disable-slash-commands --no-session-persistence`, messaggio da stdin, cartella di lavoro = progetto. Per le chiamate 4-8 l'uscita era `stream-json --verbose` (stesse richieste al modello). Blocco A: 8 notizie vere del database (titolo e riassunto usato come sommario, tagliato a 1.500 caratteri): messaggio da 12.121 caratteri, sistema vero del pre-filtro da 758. Le 8 avevano già pertinenza ≥ 85: "8 su 8" è atteso.

I JSON grezzi e lo script di misura sono andati persi il 13 novembre. La tabella è quella consegnata dall'utente (colonne di token, turni, blocchi, costo, tempi). La colonna "di cui ragionamento" l'ho letta il 12 novembre in `usage.output_tokens_details.thinking_tokens` dei JSON poi persi: campo non descritto nelle pagine ufficiali, da riconfermare con la prima chiamata di misura.

| # | Chiamata | Modello | input | cache scritta | cache letta | uscita | di cui ragionamento | turni | blocchi della risposta | costo nozionale USD | secondi (processo) | ms API |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | minima: sistema di 31 caratteri, messaggio "ok", schema `{ok: boolean}` | haiku-5-5 | 2 | 1.318 | 0 | 137 | 84 | 2 | n.d. | 0,0003323 | 3,1 | 1.014 |
| 2 | minima ripetuta subito dopo | haiku-5-5 | 2 | 605 | 717 | 139 | 86 | 2 | n.d. | 0,00019787 | 2,5 | 1.141 |
| 3 | minima senza `--json-schema` (risposta testuale "ok") | haiku-5-5 | 2 | 837 | 0 | 4 | 0 | 1 | n.d. | 0,0001696 | 4,3 | 998 |
| 4 | pre-filtro vero, blocco A, con schema | haiku-5-5 | 2 | 6.785 | 0 | 694 | 587 | 2 | thinking, tool_use | 0,0017042 | 5,5 | 3.688 |
| 5 | come la 4 con `--effort low` | haiku-5-5 | 2 | 605 | 6.181 | 538 | 431 | 2 | thinking, tool_use | 0,00045201 | 4,2 | 2.866 |
| 6 | come la 4 con `MAX_THINKING_TOKENS=0` nell'ambiente | haiku-5-5 | 2 | 606 | 6.181 | 588 | 481 | 2 | thinking, tool_use | 0,00047721 | 4,5 | 2.927 |
| 7 | come la 4 con `--model claude-haiku-4-5` e `MAX_THINKING_TOKENS=0` | haiku-4-5 | 3 | 5.113 | 0 | 524 | 0 | 2 | text, tool_use | 0,012849 | 9,2 | 5.985 |
| 8 | come la 4 senza `--json-schema` (istruzione "rispondi solo con un oggetto JSON" nel sistema) | haiku-5-5 | 2 | 6.301 | 0 | 515 | 470 | 1 | thinking, text | 0,0015179 | 7,9 | 2.922 |

Tutte le chiamate 4-8 hanno restituito gli stessi 8 id pertinenti e nessuna sponsorizzata. Fatti dimostrati *(misura)*:

1. **Carico fisso**: 1.318 token in ingresso con un sistema di 31 caratteri e un messaggio di 2 token (l'ADR 0006 riportava circa 700, misura del 6 novembre). Senza schema sono 837: **lo schema costa circa 480 token in ingresso**. In uscita la chiamata 1 ne produce 137 contro 4 della 3, ma la 3 non aveva ragionamento: i circa 130 token in più non sono tutti dello schema. Ipotesi: i 480 sono il prompt di sistema "per l'uso di strumenti" (406 token con scelta forzata dello strumento su Haiku 5.5, pagina dei prezzi) più la definizione dello strumento (circa 75).
2. **Il contesto aggiunto da Claude Code** vale circa 825 token anche con `--system-prompt`, `--tools ""` e `--safe-mode` (837 meno sistema e messaggio): circa 220 prima del messaggio (717 − 481 − sistema) e circa 605 dopo. Contenuto sconosciuto (6b-6).
3. **Con `--json-schema` la risposta passa da uno strumento** (`tool_use`, 2 turni) ma c'è una sola richiesta al modello (una sola voce in `usage.iterations`, letta nei JSON poi persi).
4. **Tutto l'ingresso è scritto in cache, messaggio compreso, con durata 1 ora** (`usage.cache_creation.ephemeral_1h_input_tokens`, campo documentato): `input_tokens` è sempre 2-3. Il messaggio di un pre-filtro non viene riletto da nessuno.
5. **La cache tra chiamate funziona solo sul prefisso identico**: nella chiamata 2 si rileggono 717 token (strumento più sistema) e se ne riscrivono 605; nelle 5 e 6, identiche alla 4 anche nel messaggio, se ne rileggono 6.181 e se ne riscrivono 605-606. **Circa 605 token si riscrivono a ogni chiamata** anche quando tutto il resto è identico. In produzione si riusa al massimo il prefisso: circa 1.070 token nel pre-filtro e 1.260 nella valutazione *(modello: 717 più la parte del sistema reale)*. Il minimo cacheable di Haiku 5.5 è 512 token, quello di Haiku 4.5 è 4.096 (pagina della cache dei prompt).
6. **Il ragionamento di Haiku 5.5 è adattivo e non si spegne** (model-config). Colonna "ragionamento" *(letta nei JSON persi)*: 431-587 token nel pre-filtro, 84-86 nella chiamata minima con schema, **0** in quella senza schema. Dato verificato: `--effort low` riduce l'uscita del 22% (538 contro 694); `MAX_THINKING_TOKENS=0`, che su Haiku 5.5 non ha effetto documentato, la riduce del 15% (588): una sola prova ciascuna, le due differenze sono dello stesso ordine e potrebbero essere rumore.
7. **Haiku 4.5 senza ragionamento non conviene**: nessun blocco `thinking` ma scrive testo prima dello strumento (524 token), è più lento (6,0 contro 3,7 secondi di API) e costa 7,5 volte a listino (0,0128 contro 0,0017 USD nozionali). Il suo totale in ingresso è più basso (5.113 contro 6.785; vedi 1.1).
8. **Tempi**: 2,5-7,9 secondi a chiamata con Haiku 5.5 (la 8 è la più lenta), di cui 1,0-3,7 di API. La differenza (1,3-3,3 s; 5,0 s nella chiamata 8) è attribuita all'avvio del processo `claude`: è un'inferenza (secondi totali meno millisecondi API), non una misura.
9. **Dai JSON poi persi** *(da riconfermare)*: la risposta con `--output-format json` (quella che usa l'app) conteneva già `usage.output_tokens_details.thinking_tokens`, `modelUsage.<modello>.thinkingTokens` e `costBasis: "list"`. L'app oggi somma tutto in "ingresso" (`llm/claude_code.py:60`) e butta via la divisione tra input, cache scritta e cache letta.
10. **Dai JSON poi persi** *(da riconfermare; non descritto nella pagina headless, che elenca `system/init`, `system/api_retry`, `stream_event`, `result`)*: il flusso `stream-json` conteneva un evento `rate_limit_event` con `unifiedWindows.five_hour.utilization` e `seven_day.utilization` (0,22 = 22%). Nelle 5 chiamate in `stream-json` la finestra di 5 ore andava da 0,22 a 0,26 e quella di 7 giorni restava 0,21. La variazione non si può attribuire alle sole chiamate (la finestra è condivisa con ogni altro uso di Claude) e ha risoluzione di 1 punto percentuale.

**Prezzi nozionali** (`total_cost_usd`): Haiku 5.5 circa 0,10 USD per milione di ingresso, 0,50 di uscita, 0,20 di cache scritta a 1 ora, 0,01 di cache letta; Haiku 4.5 circa 1,00 / 5,00 / 2,00. **Verificati** sulla pagina ufficiale dei prezzi (sezione 2.1): coincidono.

### 1.6 Che cosa finisce nel sommario e nel contenuto, per tipo di fonte

| Tipo | Sommario (pre-filtro, tagliato a 1.500 caratteri) | Contenuto (valutazione, taglio a 60.000) | Lunghezza tipica |
|---|---|---|---|
| arXiv | l'abstract (`fonti/arxiv/__init__.py:42`) | **lo stesso abstract**, senza taglio (`:43`): nessun testo in più viene scaricato | titolo 83, abstract 1.442 caratteri *(campione di 200 paper)* |
| Sito | `summary` del feed (`fonti/siti/strategie/feed.py:40`) o `excerpt` di WordPress (`wordpress.py:64`); **vuoto** per sitemap e HTML (`sitemap.py:116`, `html.py:43`) | testo estratto da trafilatura (`fonti/siti/estrazione.py:58`), scaricato solo dopo il pre-filtro | sommario 251-287 caratteri nelle notizie mostrate *(DB)*; articolo 1.750-2.920 token (circa 4.100-6.900 caratteri) *(modello)* |
| YouTube | descrizione del feed (`fonti/youtube/__init__.py:99`) | trascrizione (`:114-128`, `completa` `:131-139`) | un solo caso nel DB: 224 caratteri di sommario; trascrizioni non salvate e mai valutate nelle es. 9 e 10 |

Note: (a) il sommario nel DB è quello dopo `completa`, che può riempire un sommario vuoto con la meta-descrizione della pagina (`estrazione.py:58`): per i siti trovati dalla sitemap il sommario al pre-filtro può essere più corto di quello salvato. (b) Per arXiv sommario e contenuto coincidono: **il pre-filtro e la valutazione leggono lo stesso testo**, il secondo con più istruzioni e più costoso. (c) Tutte e tre le notizie YouTube di entrambe le esecuzioni sono state escluse dal pre-filtro come "sponsorizzato o offerta" *(metriche)*: oggi YouTube non consuma valutazioni.

### 1.7 Numeri veri delle esecuzioni 9 e 10 *(metriche, DB)*

| | Esecuzione 9 (10 nov) | Esecuzione 10 (11 nov) |
|---|---|---|
| Impostazioni | tetto arXiv 10, finestra 3 giorni, soglia 60, Haiku per entrambi i ruoli | uguali |
| Notizie esaminate | 869: 677 arXiv, 189 siti, 3 YouTube | 499: 412 arXiv, 84 siti, 3 YouTube |
| Pre-filtro: token (ingresso / uscita) | 405.858 / 46.107 | 239.085 / 29.317 |
| Elaborazione: token (ingresso / uscita) | 488.649 / 172.140 | 169.199 / 79.149 |
| Scartate dal pre-filtro (`scartate_prefiltro`) | arXiv 34, siti 75 | arXiv 25, siti 38 |
| Escluse come sponsorizzate dal pre-filtro | siti 20, YouTube 3 | siti 11, YouTube 3, arXiv 1 |
| Pre-filtro: scarto complessivo | arXiv 5,0%, siti 50,3%, in tutto 132 su 869 (15,2%) | arXiv 6,3%, siti 58,3%, in tutto 78 su 499 (15,6%) |
| Oltre il tetto arXiv | 633 | 376 |
| Valutate (chiamate) | 100: 10 arXiv, 90 siti | 45: 10 arXiv, 35 siti |
| Scartate dalla soglia | 9 (1 arXiv, 8 siti) | 1 (sito) |
| Mostrate | 91 (9 arXiv, 82 siti) | 44 (10 arXiv, 34 siti) |
| Escluse a pagamento o senza contenuto | 3 a pagamento, 1 errore di estrazione | nessuna |
| Chiamate in tutto *(codice, metriche, log)* | 132 | 64 |
| Durata | 444,5 s | 250,2 s |

Nessuna notizia è stata riesaminata: le 1.447 righe di `notizie_viste` coincidono con la somma delle notizie esaminate dalle esecuzioni 1, 2, 3, 8, 9 e 10 (65 + 4 + 8 + 2 + 869 + 499); gli errori LLM sono 0 nelle metriche e nel log non compare nessun nuovo tentativo.

---

## 2. Modello del consumo

### 2.1 Le due unità

- **(A) Token grezzi**: come li salva l'app: ingresso (input + cache scritta + cache letta, `llm/claude_code.py:60`) più uscita (ragionamento compreso).
- **(B) Unità pesate (u.p.)**: 1 u.p. = 1 token di ingresso semplice di Haiku 5.5. Pesi dai prezzi dell'API di Haiku 5.5 *(fonte)*:

| Voce | Prezzo USD per milione | Peso (u.p. per token) |
|---|---|---|
| Ingresso semplice | 0,10 | 1 |
| Cache scritta a 5 minuti | 0,125 | 1,25 |
| Cache scritta a 1 ora (quella che usa oggi Claude Code con l'abbonamento) | 0,20 | 2 |
| Cache letta | 0,01 | 0,1 |
| Uscita (ragionamento compreso) | 0,50 | 5 |

Prezzi verificati il 12 novembre 2026 su https://platform.claude.com/docs/en/about-claude/pricing (prompt fino a 100.000 token; oltre, i prezzi di Haiku 5.5 sono 0,50 / 0,625 / 1 / 0,05 / 2,50: nessuna chiamata di Gradiens li raggiunge) e riverificati dal coordinatore. Haiku 4.5: 1,00 / 1,25 / 2,00 / 0,10 / 5,00. Moltiplicatori della cache: scrittura 1,25 (5 minuti) e 2 (1 ora), lettura 0,1 (https://platform.claude.com/docs/en/build-with-claude/prompt-caching). Batch API: −50%. Confronto con i prezzi nozionali ricavati dalla misura: **coincidono** (0,10 / 0,50 / 0,20 / 0,01 per Haiku 5.5; 1,00 / 5,00 / 2,00 per Haiku 4.5): il costo nozionale è calcolato a listino. Ciò **non** prova che la quota dell'abbonamento pesi così: vedi 2.2.

### 2.2 Che cosa dicono le fonti sulla quota dell'abbonamento

*(fonte; URL e date di verifica nella sezione 7; le frasi sono parafrasi)*

- Piani Pro e Max hanno un limite per sessione di 5 ore e un limite settimanale, condivisi tra Claude e Claude Code (Help Center 11145838).
- I fattori elencati: lunghezza del messaggio, dimensione degli allegati, lunghezza della conversazione, strumenti, modello, **livello di effort**, compiti a più passi; il contenuto dei progetti è in cache e conta meno contro i limiti quando è riusato (Help Center 9797557, riferito a claude.ai). Nessuna formula, nessun peso numerico.
- Claude Code (code.claude.com/docs/en/costs): "Claude Code charges by API token consumption"; i token di ragionamento si pagano come uscita; la cronologia si rilegge "at the cached token rate", quindi una domanda di una riga in una sessione aperta da ore consuma comunque quota per tutta la conversazione: **la cache letta pesa meno ma non è gratis**. Nessun peso numerico.
- Il modello conta: Opus "usa molta più quota" (Help Center 14552983). Di quanto Haiku pesi meno di Sonnet o Opus non è scritto.
- Con l'abbonamento, Claude Code chiede la cache a **1 ora** per la conversazione principale, compreso `-p` (code.claude.com/docs/en/prompt-caching); quando si passa ai crediti d'uso torna a 5 minuti, che ha una tariffa di scrittura più bassa. Ipotesi: Anthropic sceglie 1 ora dentro l'abbonamento perché lì la scrittura non è addebitata a prezzo pieno; non è scritto da nessuna parte.
- Percentuale d'uso: nella status line `rate_limits.five_hour.used_percentage` e `seven_day.used_percentage` per abbonati Pro, Max e Ultra, solo in modalità interattiva (code.claude.com/docs/en/statusline). In `-p` non c'è un'interfaccia documentata: l'evento `rate_limit_event` l'ho visto solo nei JSON poi persi (fatto 10 di 1.5).

**Resta ignoto**: i pesi di cache scritta, cache letta, ragionamento e uscita nella quota; se Haiku pesa meno di Sonnet e di quanto; se `-p` ha pesi diversi dall'uso interattivo. Conseguenza: le leve che cambiano solo la cache (6b-3, 6b-6) e il ragionamento (6b-5) hanno valore incerto; 6b-2 vale in entrambe le unità.

### 2.3 Il modello: parametri, formule, taratura

Il modello descrive una esecuzione con poche formule; tutti i numeri delle sezioni 2.4, 2.5, 3 e 4 si ottengono da qui.

**Parametri misurati o letti dal codice** *(misura, codice)*

| Simbolo | Valore | Origine |
|---|---|---|
| c/t italiano | 2,35 caratteri per token | misura (1.1) |
| `F0` ingresso fisso senza sistema né messaggio, schema minimo | 1.303 | chiamata 1: 1.318 − 13 (sistema da 31 caratteri) − 2 (messaggio) |
| lunghezza dello schema minimo | 81 caratteri | schema `{ok: boolean}` della misura |
| lunghezza degli schemi veri | pre-filtro 191, valutazione 368, argomenti 264 | `prompt.py:37-44`, `:67-85`, `:109-117` |
| lunghezza dei prompt di sistema | pre-filtro 758, valutazione 1.028, argomenti 756 più 46 per ogni argomento esistente | `prompt.py` con gli interessi veri (181 caratteri di descrizioni) |
| `F_pf` | 1.672 = F0 + (191 − 81)/2,35 + 758/2,35 | formula |
| `F_val` | 1.863 = F0 + (368 − 81)/2,35 + 1.028/2,35 | formula |
| `F_arg` | 1.381 = F0 + (264 − 81)/2,35, più il sistema (756 + 46 q)/2,35 per q argomenti | formula; con 53 argomenti l'ingresso fisso è 2.740 |
| `G` uscita fissa per chiamata di pre-filtro e di argomenti | 137 | chiamata 1: ragionamento minimo (84, letto nei JSON persi) più 53 di struttura dello strumento |
| `S` struttura dello strumento | 53 | 137 − 84 |
| prefisso riletto dalla cache (dalla 4ª chiamata dello stesso ruolo) | 717 + (schema − 81)/2,35 + (sistema/2,35 − 13): pre-filtro 1.073, valutazione 1.264, argomenti 0 | chiamata 2; il sistema degli argomenti cambia a ogni blocco |
| blocchi | pre-filtro 30 notizie, argomenti 40 | `esecutore.py:32-33` |
| pesi (u.p. per token) | scrittura 2 (1 ora) o 1,25 (5 min), lettura 0,1, uscita 5 | 2.1 |

**Lunghezze degli elementi (caratteri)** *(campione di arXiv, DB, codice)*

| Elemento | Valore |
|---|---|
| voce del pre-filtro, paper | 83 (titolo) + 1.334 (media di `min(abstract, 1.500)`) + 45 (chiavi JSON) = 1.462; token = caratteri / 3,05 = 479 |
| voce del pre-filtro, sito | 78 + 270 + 45 = 393; token = caratteri / 2,35 = 167 |
| voce del pre-filtro, video | 96 + 224 + 45 = 365; 155 token |
| messaggio di valutazione, paper | 1.442 (abstract) + 83 + 60 = 1.585; 520 token |
| risposta utile di una valutazione `J` | riassunto + 185 (titolo tradotto, punteggi, chiavi: stima) caratteri / 2,35: paper (1.178 + 185)/2,35 = 580; siti (1.300 + 185)/2,35 = 632 |
| messaggio degli argomenti | 600 (riassunto) + 85 (titolo) + 35 (chiavi) = 720 caratteri per notizia mostrata = 306 token |

**Formule** (token; `n` = notizie del blocco)

- Pre-filtro: `ingresso = F_pf + Σ voci`; `uscita = G + n × u_pf`.
- Valutazione di una notizia: `ingresso = F_val + m` (m = 520 per un paper, `A` per un sito); `uscita = S + J + T`.
- Valutazione a lotti di k paper: `ingresso = F_val + k × (520 + 15)`; `uscita = S + k × (J + T_b)`.
- Argomenti, blocco di n notizie e q argomenti: `ingresso = F_arg + (756 + 46 q)/2,35 + 306 n`; `uscita = G + n × (18 + 52)` (70 per notizia: **ipotesi**, per analogia con il pre-filtro).
- Chiamate: pre-filtro ⌈(paper + siti + video)/30⌉; una per ogni valutazione; argomenti ⌈mostrate/40⌉.
- Cache e unità pesate: in un ruolo con c chiamate, le chiamate dopo le prime 3 (partono insieme, `llm/claude_code.py:67-69`) rileggono il prefisso. `scritto = ingresso − letto`; `u.p. = scritto × peso_scrittura + letto × 0,1 + uscita × 5`.

**Dati delle esecuzioni usati** *(metriche, DB)*

| | Es. 9 | Es. 10 |
|---|---|---|
| paper, siti, video | 677, 189, 3 | 412, 84, 3 |
| valutazioni (paper + siti) | 10 + 90 | 10 + 35 |
| mostrate (paper + siti) | 9 + 82 | 10 + 34 |
| chiamate di pre-filtro e di argomenti | 29, 3 | 17, 2 |
| argomenti esistenti per blocco di argomenti | 0, 20, 40 (**ipotesi**: se ne sono creati 53 in tutto) | 53, 53 *(DB)* |
| paper promossi dal pre-filtro `p` | 643 su 677 = 0,950 | 386 su 412 = 0,937 |

**Taratura** (4 parametri liberi): c/t dell'inglese (dall'ingresso del pre-filtro), `u_pf` = (uscita del pre-filtro − 137 × chiamate)/notizie (dall'uscita del pre-filtro), `A` (token di un articolo di sito: ingresso dell'elaborazione meno argomenti, paper e parte fissa, diviso le valutazioni di siti), `T` (ragionamento per valutazione: (uscita dell'elaborazione − argomenti)/valutazioni − 53 − J medio, per differenza).

| Parametro | Tarato sulla es. 10 | Tarato sulla es. 9 | Valore usato negli scenari |
|---|---|---|---|
| c/t dell'inglese | 3,07 | 3,04 | 3,05 |
| `u_pf` (uscita per notizia, pre-filtro) | 54,1 | 48,5 | 50,5 (di cui circa 6,75 di id e 43,8 di ragionamento: stima) |
| `A` (token di un articolo di sito) | 1.750 | 2.922 | quello della esecuzione di riferimento |
| `T` (ragionamento per valutazione) | 1.011 | 974 | quello della esecuzione di riferimento (stima) |

**Esempio svolto a mano**, pre-filtro della es. 10 con i parametri medi: ingresso = 17 × 1.672 + 412 × 479 + 84 × 167 + 3 × 155 = 28.424 + 197.348 + 14.028 + 465 = circa 240.300 (reale 239.085, +0,5%); uscita = 17 × 137 + 499 × 50,5 = 2.329 + 25.200 = circa 27.500 (reale 29.317, −6,1%).

**Quanto bene riproduce** (errore percentuale del modello rispetto alle metriche):

| Grandezza | Tarato sulla 10, errore sulla 9 | Tarato sulla 9, errore sulla 10 | Parametri medi, es. 9 / es. 10 |
|---|---|---|---|
| Ingresso del pre-filtro | −0,7% | +0,8% | −0,3% / +0,5% |
| Uscita del pre-filtro | +10,6% | −9,5% | +3,8% / −6,1% |
| Ingresso dell'elaborazione | **−21,6%** | **+24,3%** | −6,0% / **+17,5%** |
| Uscita dell'elaborazione | +1,8% | −1,7% | +0,6% / −1,2% |

Con `A` e `T` della stessa esecuzione e gli altri parametri medi, il totale è riprodotto entro 0,1% (516.346 contro 516.750 per la 10; 1.113.722 contro 1.112.754 per la 9). **Il punto debole è la lunghezza degli articoli dei siti**: 1.750 token nella 10 e 2.922 nella 9 (+67%), non prevedibile e non salvata. Il resto sta entro ±11%. Altre debolezze: due esecuzioni con le stesse impostazioni (4 parametri liberi, 8 osservazioni); `T` è una differenza, non una misura, e poggia sulla colonna del ragionamento non più verificabile; la quota di sommario dei siti trovati dalla sitemap è incerta (nota (a) di 1.6). Rimedio: 6b-1 salva questi numeri per davvero.

**Regole degli scenari** (sezioni 3 e 4): *6b-2* = i paper si pre-filtrano in blocchi da 30, separati da siti e video (che si pre-filtrano da soli, ⌈(siti + video)/30⌉ blocchi), per ⌈T/(30 p)⌉ blocchi (T = tetto: con T = 10, un blocco di 30 paper); *lotti di k* = ⌈T/k⌉ chiamate con le formule sopra; *effort basso* = ragionamento × 0,73 in tutte le chiamate (84 per chiamata e 43,8 per notizia nel pre-filtro, 52 per notizia negli argomenti, `T` per valutazione); paper mostrati = 0,95 T (quelli veri per T = 10); articoli di siti e mostrate di siti come nella esecuzione di riferimento.

### 2.4 Dove va oggi il consumo

Token grezzi del modello, ripartiti per fase e tipo (parametri della esecuzione stessa; la quota fissa di ogni chiamata è divisa in proporzione al numero di notizie):

| Voce | Es. 10 | % | Es. 9 | % |
|---|---|---|---|---|
| Pre-filtro arXiv: paper **oltre il tetto** (376 e 633) | 222.399 | **43,1%** | 373.613 | **33,5%** |
| Pre-filtro arXiv: gli altri (36 e 44) | 21.293 | 4,1% | 25.970 | 2,3% |
| Pre-filtro siti e YouTube (87 e 192) | 24.270 | 4,7% | 53.362 | 4,8% |
| Valutazione arXiv (10 e 10) | 40.262 | 7,8% | 39.891 | 3,6% |
| Valutazione siti poi mostrati (34 e 82) | 180.498 | 35,0% | 528.391 | 47,4% |
| Valutazione siti poi **scartati dalla soglia** (1 e 8) | 5.309 | 1,0% | 51.550 | 4,6% |
| Argomenti | 22.315 | 4,3% | 40.944 | 3,7% |
| Totale ricostruito | 516.346 | | 1.113.722 | |

Nella es. 9 la riga "Valutazione arXiv" comprende un paper poi scartato dalla soglia (circa 4.000 token, 0,4%).

Per natura del consumo (percentuali del totale):

| Natura | Es. 10: token | Es. 10: u.p. | Es. 9: token | Es. 9: u.p. |
|---|---|---|---|---|
| Ingresso: carico fisso per chiamata (strumento, contesto, prompt di sistema) | 22,8% | 9,2% | 21,6% | 7,8% |
| Ingresso: testo delle notizie | 56,5% | 47,4% | 58,6% | 50,0% |
| Uscita: ragionamento *(stima)* | 13,8% | 28,9% | 12,8% | 27,4% |
| Uscita: struttura dello strumento | 0,7% | 1,4% | 0,6% | 1,3% |
| Uscita: risposta utile (riassunti, id, assegnazioni) *(stima)* | 6,2% | 13,0% | 6,3% | 13,5% |

Le prime due righe e la struttura sono ricavabili dal modello; ragionamento e risposta utile sono ricavati per differenza e da stime (risposta di 580-632 token per valutazione, 70 token per notizia negli argomenti, `G` che poggia sulla colonna del ragionamento non più verificabile). Ragionamento: circa 66% dell'uscita (es. 10: circa 71.000 token su 106.700 dell'uscita del modello; le metriche danno 108.466; es. 9: 65%). Con riassunti a 3,0 caratteri per token invece di 2,35 la stima salirebbe di circa 1 punto.

Totale in u.p. del modello: circa 1,23 milioni (es. 10) e 2,61 milioni (es. 9). Ripartizione per tipo di token (es. 10): scritture di cache 56%, letture 0,5%, uscita 43%. A prezzi di listino l'esecuzione 10 costa 0,12 USD e la 9 0,26 USD (solo per capirsi: la quota non è in dollari).

### 2.5 Quante notizie si possono esplorare con un budget dato

**Formula** (token grezzi; `Na'` = paper pre-filtrati, `Ns` = notizie di siti, `Nv` = video, `b` = blocco; `Va`, `Vs` = valutazioni di paper e di siti; `M` = notizie mostrate):

```
C = ⌈(Na' + Ns + Nv)/b⌉ × (F_pf + 137)                              parte fissa del pre-filtro
  + Na' × (479 + 50,5) + Ns × (167 + 50,5) + Nv × (155 + 50,5)      parte variabile del pre-filtro
  + Va × (F_val + 520 + 53 + 580 + Ta) + Vs × (F_val + A + 53 + 632 + Ts)    valutazioni
  + ⌈M/40⌉ × F_arg + M × (306 + 70) + (sistema degli argomenti)     argomenti
```

(per gli argomenti, con 53 nomi, circa 448 token per notizia mostrata includendo la quota fissa del blocco.) Oggi `Na' = Na` (tutti i paper nuovi) e `Va = tetto`. `Ta` e `Ts` sono i token di ragionamento di una valutazione (circa 1.000 nella taratura). Le leve cambiano `Na'`, `Va`, `b`, i pesi e i termini fissi.

**Costi marginali per notizia** *(modello, blocchi da 30, cache a 1 ora)*:

| Voce | Token grezzi | u.p. |
|---|---|---|
| Pre-filtro di un paper (parte variabile) | 530 (590 con la quota fissa del blocco) | 1.211 (1.278) |
| Pre-filtro di una notizia di sito | 218 | 587 |
| Valutazione di un paper, una per chiamata | 4.026 | 10.583 |
| Valutazione di un paper, lotti di 5 / 10 (ragionamento invariato) | 2.509 / 2.317 | 9.342 / 9.183 |
| Valutazione di un paper, lotti di 10 con ragionamento 700 / 350 (**ipotesi**) | 2.006 / 1.656 | 7.628 / 5.878 |
| Valutazione di un articolo di sito (es. 10: 1.750 token) | 5.309 | 13.304 |
| Valutazione di un articolo di sito (es. 9: 2.922 token) | 6.444 | 15.463 |
| Argomenti, per notizia mostrata | 448 | 1.117 |
| Un paper di tetto con 6b-2 (pre-filtro 590/0,937 + valutazione + argomenti) | circa 5.100 | circa 13.060 |
| Un video con trascrizione da 9.000 / 30.000 / 60.000 caratteri *(stima: circa 900 caratteri al minuto di parlato)* | 7.414 / 16.350 / 29.116 | 17.514 / 35.387 / 60.919 |

**Con il budget della esecuzione 10** (516.346 token del modello, 516.750 reali; circa 1,23 milioni di u.p.), oggi: tetto 10, 412 paper pre-filtrati, 35 valutazioni di siti. Un paper in più oltre il tetto costa circa 4.500 token (valutazione più argomenti) e circa 11.700 u.p.: senza altre leve il tetto a quota costante è **10**, per definizione. I tetti sostenibili con le leve sono nella sezione 4.2.

---

## 3. Le leve

Le schede delle proposte **raccomandate o da fare dopo le misure** (6b-1 … 6b-8, 6b-10, 6b-12) hanno tutte le voci: problema (con `file:riga`), opzioni, risparmio, qualità, provider, Windows e Linux, raccomandazione, passi, test, rischi, sforzo. Quelle la cui raccomandazione è "non fare" o "lasciare così" (6b-9, 6b-11, 6b-13, 6b-14, 6b-15, 6b-16) hanno una scheda breve: problema con `file:riga`, opzioni considerate, perché no, che cosa farebbe cambiare idea. Gli sforzi sono **stime** in giorni (g) o ore (h) di lavoro del backend, test compresi. Dove serve cambiare un requisito del PRD è scritto con il suo codice.

### 6b-1 — Metriche di token dettagliate (prerequisito)

**Problema.** `Metriche.conta_token` somma solo `ingresso` e `uscita` per ruolo (`esecuzione/esecutore.py:87-89`); `interpreta` somma input, cache scritta e cache letta (`llm/claude_code.py:60`) e butta via la divisione; il ragionamento non si legge; non si registrano token per fase o per tipo, numero di chiamate, tentativi, lunghezza dei contenuti, contenuti troncati (`esecutore.py:422-423`) né i paper pre-filtrati e promossi. Questo documento poggia su ipotesi proprio per questo (lunghezza degli articoli dei siti, ragionamento).

**Vincolo sui lettori delle metriche** *(verificato)*: `dashboard/templates/resoconto.html:60-61` itera `r.token.items()` e per ogni voce legge `modello`, `provider`, `ingresso`, `uscita`; `dati/esecuzioni.py:59` somma `ingresso + uscita` su **ogni** chiave di `token`. Quindi sotto `token` possono stare solo chiavi di ruolo, e `ingresso` e `uscita` devono mantenere il significato di oggi (ingresso comprende cache scritta e letta). I campi nuovi vanno **fuori** da `token`:

- `metriche.dettaglio_token.<ruolo>` = `{chiamate, ingresso_semplice, cache_scritta_1h, cache_scritta_5m, cache_letta, ragionamento, secondi}`;
- `metriche.chiamate` = lista di `{fase, tipo, notizie, ingresso_semplice, cache_scritta, cache_letta, uscita, ragionamento, secondi, tentativi}`;
- `metriche.fonti.<tipo>.contenuto` = `{n, caratteri_p50, caratteri_p90, caratteri_max, troncati}`;
- `metriche.fonti.arxiv.prefiltrate` e `promosse`.

`dati/esecuzioni.py:46` elenca i contatori sommati per `totali` (`CONTATORI`): le chiavi nuove non ne fanno parte e non si sommano.

**Opzioni.** A. Lasciare così. B. Solo gli aggregati per ruolo. C. B più una riga per chiamata: circa 64 righe, circa 6 KB per l'esecuzione 10 (132 righe per la 9). D. C più contenuti e paper pre-filtrati.

**Risparmio.** 0: serve a misurare. **Qualità.** Nessun effetto.

**Provider (ADR 0006).** `Risposta` (`llm/base.py:8-12`) riceve campi **facoltativi** con valore 0 (`token_cache_scritta_1h`, `token_cache_scritta_5m`, `token_cache_letta`, `token_ragionamento`): chi non li conosce li lascia a 0. Per Claude Code `usage.cache_creation.ephemeral_1h_input_tokens` e `ephemeral_5m_input_tokens` sono documentati; `usage.output_tokens_details.thinking_tokens` è da riconfermare (1.5). Per l'API di Claude `usage.cache_creation_input_tokens` e `cache_read_input_tokens`; per i provider compatibili OpenAI `prompt_tokens_details.cached_tokens`, che il livello di compatibilità di Anthropic lascia vuoto (pagina openai-sdk). `Finto` (`llm/finto.py`) e i test continuano a funzionare. Il contratto cambia solo con aggiunte: avvisare l'architetto e il frontend (il resoconto legge `token` come sopra).

**Windows e Linux.** Nessuna differenza.

**Raccomandazione.** Opzione D, subito, senza decisioni: la prima esecuzione programmata dopo la modifica è la misura di base senza costi di quota.

**Passi** (ognuno committabile con i test verdi):
1. `interpreta` legge cache e ragionamento (campi mancanti = 0); `Risposta` con campi facoltativi.
2. `Metriche.conta_token(ruolo, risposta, fase, tipo, notizie)` aggiorna `token.<ruolo>` come oggi e, in più, `dettaglio_token` e `chiamate`.
3. Lunghezza dei contenuti e troncamenti in `_completa` (`esecutore.py:418-424`).
4. `prefiltrate` e `promosse` per arXiv in `_prefiltra` (nel passo 3 di 6b-2 se si fa insieme).
5. (Frontend, facoltativo) il resoconto mostra le nuove voci.

**Test.** `tests/llm/test_claude_code.py`: `test_interpreta_legge_cache_e_ragionamento` con una risposta **scritta a mano** coi soli campi documentati (la fixture registrata il 12 novembre è andata persa; un'alternativa è una chiamata minima vera con il permesso dell'utente, circa 1.500 token); `test_provider_senza_cache_lascia_zero`. `tests/esecuzione/test_esecutore.py`: `test_le_metriche_dividono_i_token_per_fase_e_tipo`, `test_ingresso_e_uscita_di_token_mantengono_il_significato`, `test_contenuto_troncato_si_conta`. `tests/dati/`: `test_riepilogo_ignora_le_chiavi_nuove`.

**Rischi.** Dimensione del JSON (trascurabile); chiavi nuove in `esecuzioni.metriche`: lettori con `.get`; un campo non documentato (`thinking_tokens`) potrebbe sparire: va letto con `.get`.

**Sforzo.** 0,5 g *(stima)*.

### 6b-2 — Pre-filtro arXiv "fino a riempire il tetto" (cambia ARX-02)

**Problema.** `esecutore.py:274-283`: tutti i paper nuovi passano dal pre-filtro (`ARX-02`) e solo dopo si applica il tetto (`ARX-03`); i paper oltre il tetto sono scartati senza valutazione. Es. 10: 376 paper su 412; 43,1% di tutti i token. Es. 9: 633 su 677; 33,5% (sezione 2.4). Per arXiv il pre-filtro promuove il 94-95% e legge lo stesso abstract della valutazione.

**Il pre-filtro di arXiv non riduce le valutazioni.** Il tetto fissa il numero di paper valutati: il pre-filtro non ne toglie mai nessuna. La sua sola utilità è tenere fuori dal tetto il 5-6% di paper non pertinenti, a un costo di 226.000 token nella es. 10. Senza tetto non si ripagherebbe nemmeno: costa 590 token grezzi e circa 1.280 u.p. per paper, una valutazione singola più argomenti 4.474 token e 11.700 u.p., quindi risparmia solo se scarta almeno 590/4.474 = 13,2% dei paper (10,9% in u.p.); con le valutazioni a lotti da 10 (2.765 token) il pareggio sale al 21%. Osservato: 6,3% e 5,0%.

**Opzioni** (con blocchi da 30; paper separati da siti e video):

| Opzione | Che cosa cambia | Token grezzi (es. 10 / es. 9) | u.p. (es. 10 / es. 9) | Compromessi |
|---|---|---|---|---|
| A. Lasciare così | niente | 0 | 0 | tetto fermo a 10 |
| B. **Fino a riempire il tetto** | i paper, in ordine di data, passano dal pre-filtro a blocchi; ci si ferma quando i promossi raggiungono il tetto; gli altri sono "visti" come oggi | **−43,8% / −34,2%** | −39,7% / −31,6% | Con tetto 10 si pre-filtra 1 blocco da 30 paper (non 11): chiamate 64 → 51 (es. 10), 132 → 111 (es. 9). Stessi paper di oggi **se** il pre-filtro è deterministico e non dipende dagli altri paper del blocco (i primi blocchi sono identici: `nuove` conserva l'ordine dell'API, data decrescente: `fonti/arxiv/__init__.py:44`, `:59`). ARX-02 va riscritto. Pre-filtro residuo: 14,5% (es. 10), 9,8% (es. 9) del consumo |
| C. Nessun pre-filtro arXiv, valutazione diretta | solo il tetto per data | −47,2% / −35,8% | −42,8% / −33,1% | guadagna 3,4 punti in più di B (es. 10; 1,6 es. 9); perde lo scarto del 6% e la bandiera "sponsorizzato" (1 paper nella es. 10); ARX-02 va tolto per arXiv |
| D. Tetto prima del pre-filtro | si tagliano i T paper più recenti e poi si pre-filtrano | come B | come B | il tetto conta paper non filtrati: ne restano circa 6% in meno; cambia ARX-03 |
| E. Tetto per pertinenza | vedi 6b-7 | negativo | negativo | scheda a parte |

**Effetti da dichiarare**
- **Più lento**: con pochi promossi i giri da 1 blocco vanno in fila (fino a 14 chiamate in sequenza per 412 paper, contro 3 in parallelo oggi: il semaforo di `ClaudeCode`, `llm/claude_code.py:67-69`); a ogni giro qualche secondo di attesa.
- **Esecuzioni piccole**: separare i paper da siti e video può aggiungere un blocco (es. 9: 29 → 30 chiamate se si pre-filtrassero tutti).
- **Avanzamento**: il totale del pre-filtro (`_fase("pre-filtro", len(blocchi))`, `esecutore.py:385`) non è più noto all'inizio: si parte dai blocchi del primo giro e lo si aggiorna.
- **Metriche e resoconto**: `oltre_tetto` deve contare i paper **non pre-filtrati più i promossi in eccesso**; altrimenti il riquadro "arXiv: tetto raggiunto" (`dashboard/templates/resoconto.html:44-49`), la riga della CLI (`app/cli.py:110-111`) e l'identità dei contatori di ESE-11 (esaminate = scartate dal pre-filtro + oltre il tetto + escluse + senza contenuto + scartate dalla valutazione + mostrate: es. 10 oggi 412 = 25 + 376 + 1 + 0 + 0 + 10) non tornano. `scartate_prefiltro` per arXiv conterà solo i paper pre-filtrati e scartati; si aggiungono `prefiltrate` e `promosse`.
- **Testi**: `ESE-04` (il pre-filtro legge "le notizie nuove") e l'aiuto (`dashboard/templates/aiuto.html:28`, proprietà del frontend) vanno precisati per arXiv.

**Qualità.** Per costruzione B sceglie "i T paper più recenti tra quelli che passano il pre-filtro", come oggi. Con un LLM vero il verdetto su un paper può dipendere dalla composizione del blocco: differenze possibili, non misurate. L'ultimo blocco di oggi può mescolare paper con siti e YouTube: B lo evita.

**Provider.** Tutto nell'esecutore: `Provider.chiedi` non cambia. Vale per ogni provider.

**Windows e Linux.** Nessuna differenza.

**Requisiti da cambiare.** `ARX-02` ("tutti i paper nuovi delle categorie scelte passano dal pre-filtro") → "i paper nuovi passano dal pre-filtro dal più recente, a blocchi, finché i promossi raggiungono il tetto (ARX-03); gli altri entrano nel registro delle notizie già viste". Ritocchi di `ESE-04` e dell'aiuto. `ARX-03` e `ESE-11` restano. **Decisione dell'utente (D1).**

**Raccomandazione.** Opzione B.

**Passi** (ognuno committabile con i test verdi; i test esistenti sostituiscono `BLOCCO_PREFILTRO` con 1 e restano validi, quindi nel codice non si fissano 30 né 0,94):
1. Refactoring senza cambiare comportamento: `_prefiltra` si divide in una funzione per blocco e in una che prende una lista ordinata e la elabora **in giri**; per ora un solo giro con tutti i blocchi. Test esistenti verdi.
2. Separare i paper da siti e video nei blocchi. Test `test_il_prefiltro_separa_i_paper_da_siti_e_video`. Test esistenti verdi (con attenzione al conteggio delle chiamate).
3. Giri con arresto: un giro lancia il minimo di blocchi che potrebbe riempire il tetto, cioè ⌈mancanti / blocco⌉, al massimo `GIRO_PREFILTRO = 3` insieme (costante dell'esecutore, indipendente dal semaforo del provider); si ripete finché i promossi ≥ tetto o i paper finiscono. Test sotto.
4. Se un blocco fallisce (`ErroreLLM`) **non si lanciano giri nuovi**; i blocchi dello stesso giro non si fermano, come oggi (`test_un_blocco_del_prefiltro_fallito_non_ferma_l_esecuzione`, `tests/esecuzione/test_esecutore.py:156`, che resta verde); i paper non filtrati restano non visti. Conseguenza da documentare: un blocco fallito lascia posto a paper più vecchi nel tetto, come oggi.
5. Metriche: `oltre_tetto`, `scartate_prefiltro`, `prefiltrate`, `promosse` con il significato sopra (dopo 6b-1 per i nomi dei campi nuovi).
6. Documentazione: PRD (ARX-02, ESE-04), mappa, `aiuto.html` e testi del resoconto (frontend).

**Test.** `test_prefiltro_arxiv_si_ferma_quando_i_promossi_riempiono_il_tetto` (100 paper, tetto 5, pre-filtro finto che promuove tutto: 1 sola chiamata, non 4); `test_i_paper_non_prefiltrati_sono_visti_e_contano_come_oltre_il_tetto`; `test_con_pochi_promossi_i_giri_continuano_fino_all_ultimo_paper`; `test_siti_e_youtube_si_prefiltrano_tutti`; `test_i_contatori_di_arxiv_tornano` (identità di ESE-11); `test_dopo_un_blocco_fallito_non_partono_giri_nuovi`; `test_i_paper_valutati_sono_i_piu_recenti_tra_i_promossi` con un **elenco atteso scritto a mano** (il confronto con il vecchio codice non è realizzabile dopo la modifica). Restano `test_tetto_arxiv_elabora_solo_i_piu_recenti` (`tests/esecuzione/test_esecutore.py:101`) e `test_esecuzione_completa`.

**Rischi.** Basso. Tempo di esecuzione maggiore nei giorni con pochi promossi; lettori delle metriche (resoconto, CLI, Telegram) da allineare al nuovo significato di `oltre_tetto`.

**Sforzo.** 1-1,5 g *(stima)*.

### 6b-3 — Cache dei prompt: scrittura a 5 minuti

**Problema.** `llm/claude_code.py:40-42` (`_ambiente`) non tocca la cache: tutto l'ingresso, messaggio compreso, è scritto a 1 ora (peso 2 a listino) e, tranne il prefisso, non viene riletto (fatti 4 e 5 della misura). La cache fa risparmiare solo sul prefisso: 1.073 token nel pre-filtro (7,6% dell'ingresso di una chiamata da 14.064), 1.264 nella valutazione di un paper (circa 53% di 2.380). Ordinare diversamente sistema e messaggio non serve: l'ordine è già statico, poi variabile (strumento, sistema, messaggio); il messaggio è per definizione diverso tra chiamate. L'unico modo di leggere di più dalla cache sarebbe allungare il prefisso comune, cioè pagare di più per scriverlo.

**Che cosa dice la documentazione** *(fonte)*: la cache a 1 ora è il valore predefinito con l'abbonamento; `FORCE_PROMPT_CACHING_5M=1` la porta a 5 minuti e vince su ogni altra impostazione (ordine: `FORCE_PROMPT_CACHING_5M`, poi `CLAUDE_CODE_PROMPT_CACHE_TTL` dalla v2.1.242, poi l'impostazione `promptCacheTtl`, poi `ENABLE_PROMPT_CACHING_1H`, poi il predefinito); `DISABLE_PROMPT_CACHING=1` e `DISABLE_PROMPT_CACHING_HAIKU=1` la spengono; `claude -p "hello" --output-format json` e `usage.cache_creation` dicono la durata usata.

**Opzioni.**

| Opzione | Token grezzi | u.p. (es. 10 / es. 9) | Se la quota non distingue le scritture |
|---|---|---|---|
| A. Lasciare (1 ora) | 0 | 0 | 0 |
| B. `FORCE_PROMPT_CACHING_5M=1` | 0 | **−21,0% / −21,5%** | 0 |
| C. `DISABLE_PROMPT_CACHING=1` | 0 | −23,4% / −23,6% | **peggio**: si perdono le letture a 0,1 (circa +6,5% se le scritture pesano come l'ingresso semplice) |
| D. Riordinare sistema e messaggio | 0 | 0 | 0 |

Non si conosce uno scenario in cui B peggiora: la scrittura a 5 minuti non costa mai più di quella a 1 ora in nessun listino letto, e le chiamate di un'esecuzione sono a pochi secondi l'una dall'altra; fra due esecuzioni (24 ore) la cache non sopravvive comunque. Ma che la quota segua i prezzi è **ipotesi**, e Anthropic usa proprio 1 ora con l'abbonamento (2.2): l'effetto va verificato, non presunto.

**Qualità.** Nessun effetto.

**Provider (ADR 0006).** Specifica di Claude Code, **confinata** in `ClaudeCode` (`_ambiente`: `env.setdefault("FORCE_PROMPT_CACHING_5M", "1")`, così non si sovrascrive una scelta dell'utente). Per l'API di Claude: nessun `cache_control` sul messaggio, solo sul blocco di sistema, con scadenza di 5 minuti (scrittura 1,25, lettura 0,1); Haiku 5.5 ha un minimo di 512 token (il sistema più lo strumento di Gradiens, circa 1.070, lo supera), Haiku 4.5 di 4.096 (non lo supera). Per i provider compatibili OpenAI: il livello di compatibilità di Anthropic **non** supporta la cache; OpenAI la fa in automatico da 1.024 token con sconto fino al 95% (https://developers.openai.com/api/docs/guides/prompt-caching); per Ollama e LM Studio non verificato.

**Windows e Linux.** Una variabile d'ambiente passata a `create_subprocess_exec`: identica. Versione minima di Claude Code per `FORCE_PROMPT_CACHING_5M` non indicata nelle pagine lette; la 2.1.316 su Linux la accetta (documentata). Su una versione che non la conosce è ignorata.

**Raccomandazione.** Fare B dopo 6b-1, senza decisioni dell'utente e senza quota extra: l'effetto si verifica nelle metriche di 6b-1 (`cache_scritta_5m` contro `cache_scritta_1h`, campi documentati). Una prova a parte (una delle chiamate di M2) è facoltativa.

**Passi.**
1. Estendere il finto `claude` dei test: oggi salva solo `ANTHROPIC_API_KEY` (`tests/llm/test_claude_code.py:18`); deve salvare anche `FORCE_PROMPT_CACHING_5M`.
2. Test rosso: la variabile arriva al processo e `ANTHROPIC_API_KEY` no.
3. Modifica di `_ambiente`.
4. Dopo una settimana di metriche: confronto della quota di `cache_scritta_5m` e delle u.p. per chiamata.

**Test.** `test_la_cache_dei_prompt_e_a_5_minuti`; `test_non_si_sovrascrive_la_scelta_dell_utente`.

**Rischi.** Basso. Se Anthropic cambia i nomi delle variabili l'effetto sparisce senza errori (lo dicono le metriche); effetto reale sulla quota ignoto.

**Sforzo.** 1-2 h *(stima)*.

### 6b-4 — Valutazione dei paper a lotti

**Problema.** `elabora` (`esecutore.py:291-319`) fa una chiamata per notizia. Per un paper il contenuto è solo l'abstract (circa 520 token): su un ingresso di 2.380 token, 1.863 (78%) sono carico fisso (1.303 di strumento e contesto, 122 di schema, 437 di sistema) e 53 di uscita sono la struttura dello strumento.

**Opzioni.**

| Opzione | Token per paper (grezzi / u.p.) | Rispetto alla valutazione singola |
|---|---|---|
| A. Singola (oggi) | 4.026 / 10.583 | — |
| B. Lotti di 5, ragionamento per paper invariato (circa 1.000) | 2.509 / 9.342 | −38% / −12% |
| B'. Lotti di 10, ragionamento invariato | 2.317 / 9.183 | −42% / −13% |
| B''a. Lotti di 10, ragionamento per paper 700 (**ipotesi**, mai misurata) | 2.006 / 7.628 | −50% / −28% |
| B''b. Lotti di 10, ragionamento per paper 350 (**ipotesi**, mai misurata) | 1.656 / 5.878 | −59% / −44% |
| C. Lotti per lunghezza (anche articoli di siti brevi, fino a circa 6.000 token) | vedi 6b-14 | |

L'effetto in u.p. è piccolo perché l'uscita (ragionamento e riassunto) pesa 5 per token e non cambia; il guadagno vero in u.p. verrebbe solo da un calo del ragionamento per paper, che nessuno ha misurato. Con la 6b-2, a tetto 50 la valutazione a lotti da 5 vale −15,6% dei token e −5,0% delle u.p. (es. 10).

**Qualità.** Rischi: riassunti meno completi o confusi tra paper (ESE-05: "corretto e completo"); ragionamento condiviso tra paper; un id mancante o duplicato. Come misurarlo (M3): rivalutare in lotti i 19 paper già valutati (abstract, punteggi e riassunti sono nel DB) e confrontare. Soglie proposte (da concordare, D4): per ogni interesse la differenza di pertinenza ≤ 10 punti nell'80% dei casi; stesso lato della soglia 60 nel 95% dei casi; nessun errore fattuale in 5 riassunti letti dall'utente; nessun id mancante.

**Provider.** Provider-agnostico: cambiano prompt, schema (un array di risultati con `id`) ed esecutore; `chiedi` no. Con l'API di Claude e con i provider compatibili OpenAI lo schema dei lotti è un `json_schema` con array (il livello di compatibilità accetta solo `json_schema` con `strict: true`). Il messaggio passa da stdin: nessun limite della riga di comando; sul sistema e sullo schema, che passano come argomenti, si aggiungono circa 100 caratteri (limite di 32.767 su Windows, [mappa A6](../architettura/mappa-moduli.md#a6-osservazioni-per-le-fasi-successive)).

**Windows e Linux.** Nessuna differenza. Tempo di un lotto da 10: uscita di circa 16.000 token con ragionamento invariato (circa 12.900 se fosse 700), a 200-300 token al secondo *(stima dalla es. 10)* = 53-80 secondi (43-64), sempre entro il timeout di 300 secondi (`llm/claude_code.py:67`).

**Raccomandazione.** Fare dopo M3 con lotti di 5; lotti di 10 solo se M3 va bene.

**Passi.**
1. Test rosso: 7 paper con lotto 5 → 2 chiamate; ogni paper valutato si salva appena arriva il suo lotto.
2. `prompt.sistema_valutazione_lotto`, `SCHEMA_VALUTAZIONE_LOTTO`, `messaggio_valutazione_lotto`.
3. Esecutore: i paper promossi si raggruppano per `BLOCCO_VALUTAZIONE_ARXIV = 5`; la risposta si legge per `id`; i paper senza risposta valida si rifanno **singolarmente**.
4. Metriche per paper (token del lotto divisi per i paper).
5. Siti e YouTube restano come oggi.

**Test.** `test_valutazione_a_lotti_salva_ogni_paper`; `test_id_mancante_si_rifa_in_singola`; `test_lotto_fallito_conta_gli_errori_per_ogni_paper`; `tests/esecuzione/test_prompt.py` (nuovo): schema e messaggio del lotto.

**Rischi.** Medio. Un lotto fallito (timeout, errore) con il nuovo tentativo raddoppia il costo di 5 paper; la quota esaurita a metà lotto perde fino a 5 valutazioni; la granularità del salvataggio ("ogni notizia si salva appena valutata", intestazione di `esecutore.py`) scende da 1 a 5 paper.

**Sforzo.** 1-1,5 g *(stima)*.

### 6b-5 — Ragionamento: effort basso e istruzioni nel prompt

**Problema.** Il ragionamento è circa 14% dei token e 29% delle u.p. *(stima, 2.4)*; sull'**uscita** circa il 66% (es. 10: circa 71.000 token su 106.700 dell'uscita del modello, 108.466 nelle metriche), calcolato come uscita totale meno la risposta utile (circa 580-630 token per valutazione dalle lunghezze salvate nel DB, 6,75 per notizia nel pre-filtro, 18 per notizia negli argomenti) meno la struttura (53 per chiamata). Haiku 5.5 non lo spegne (documentazione) ma lo regola. Misura: `--effort low` ha ridotto l'uscita del 22% (538 contro 694; −27% del solo ragionamento secondo i JSON persi); `MAX_THINKING_TOKENS=0`, senza effetto documentato, l'ha ridotta del 15% (588): una prova ciascuna, i due effetti sono dello stesso ordine e il secondo suggerisce rumore. La valutazione ragiona circa 1.000 token per notizia, più del riassunto che scrive *(stima)*. La documentazione dice che si può chiedere al modello di pensare di più o di meno "direttamente nel prompt" (model-config); l'effetto di un'istruzione non è stato misurato.

**Opzioni.**
- A. Lasciare (livello `medium`, predefinito di Haiku 5.5, *fonte*).
- B. Effort basso: **il meccanismo proposto è la variabile `CLAUDE_CODE_EFFORT_LEVEL` impostata in `_ambiente()`, mai provata**; la misura ha usato il flag `--effort low`. La variabile prevale sul flag (model-config), quindi un'eventuale variabile dell'utente annullerebbe il flag: l'app deve imporre la sua. M4 deve usare lo stesso meccanismo della produzione. Effetto: −3,7% token e −7,8% u.p. se il ragionamento scende del 27%; −6,9% e −14,5% se scende del 50% *(modello)*.
- C. Istruzione nel prompt di sistema ("decidi senza spiegare; ragiona il minimo necessario"): provider-agnostica, effetto da misurare.
- D. Uscita più corta: il pre-filtro risponde già solo con id; il riassunto è fissato da ESE-05 (3-6 frasi, "corretto e completo"): non si tocca.
- E. Effort diverso per ruolo (basso al pre-filtro, medio alla valutazione): la fabbrica dei provider (`esecutore.py:109`, `Callable[[str], Provider]`) non conosce il ruolo: servirebbe `crea_provider(nome, ruolo)`, un cambio di contratto da concordare con l'architetto.

**Qualità.** Un ragionamento più corto può peggiorare il giudizio di pertinenza (soprattutto sui casi dubbi) e la completezza dei riassunti. Misura M4: su 8 paper noti, 3 varianti (predefinita, effort basso con la variabile, istruzione) ≈ 100 mila token; punteggi e riassunti confrontati con quelli salvati. Per il pre-filtro: M6 (rieseguire il pre-filtro sulle 135 notizie già mostrate: devono passare quasi tutte).

**Provider.** Specifica di Claude Code, confinata in `ClaudeCode` (`_ambiente`). Per l'API di Claude esiste un parametro di ragionamento; il livello di compatibilità OpenAI **ignora** `reasoning_effort` e non restituisce il ragionamento *(fonte)*; l'istruzione del punto C vale per tutti.

**Windows e Linux.** Nessuna differenza.

**Raccomandazione.** Dopo M4. Se la qualità regge, B per entrambi i ruoli (un solo valore, nessun cambio di contratto).

**Passi.** 1) M4 con la variabile. 2) Costante `EFFORT` in `claude_code.py`, passata in `_ambiente()` **sovrascrivendo** eventuali valori dell'utente. 3) Estendere il finto `claude` per salvare l'ambiente (oggi solo `ANTHROPIC_API_KEY`, `tests/llm/test_claude_code.py:18`). 4) Una settimana di metriche (`ragionamento` per fase, 6b-1).

**Test.** `test_l_effort_e_impostato_nell_ambiente_di_claude`; `test_la_variabile_dell_utente_viene_sostituita`.

**Rischi.** Medio (qualità); la variabile potrebbe non avere l'effetto del flag (mai provata).

**Sforzo.** 0,5 g più misure *(stima)*.

### 6b-6 — Il contesto che Claude Code aggiunge a ogni chiamata

**Problema.** Il carico fisso è 1.318 token con un prompt minimo (fatto 1 della misura): 481 sono lo strumento dello schema e circa **825** sono contesto aggiunto da Claude Code anche con `--system-prompt`, `--tools ""` e `--safe-mode`; circa 605 vengono **riscritti a ogni chiamata** (fatto 5). Non si sa che cosa contengano. La documentazione dice che Claude Code aggiunge promemoria nella conversazione (elenco dei subagenti e delle skill, CLAUDE.md, note sui file cambiati, dati d'ambiente: cartella, sistema, shell) e che con un prompt di sistema sostitutivo manca l'istantanea di git (headless). Variabili che esistono *(fonte; che riducano i 605 o gli 825 token è un'**ipotesi**)*: `CLAUDE_CODE_DISABLE_ATTACHMENTS=1` (secondo env-vars spegne l'espansione dei file citati con @; secondo la pagina agent-sdk anche le note sui file cambiati e l'elenco delle skill, mentre l'elenco dei subagenti arriva lo stesso: le due descrizioni non coincidono del tutto), `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` (non carica i CLAUDE.md), `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1` (toglie le istruzioni git e l'istantanea di `git status`). Con `OTEL_LOG_RAW_API_BODIES=file:<cartella>` (o `1`; ignorata nelle impostazioni di progetto e locali) Claude Code scrive il corpo esatto delle richieste. Il servizio parte con la cartella di lavoro del progetto: `WorkingDirectory` per systemd (`app/avvio_sistema.py:133`) e `-WorkingDirectory` per l'attività di Windows (`:207`); `claude` la eredita. Il progetto contiene `.claude/agents` e `.claude/settings.json`: una cartella diversa potrebbe cambiare il contesto.

**Risparmio.** Se si eliminassero 600 degli 825 token: −38.720 token (−7,5%) e −77.440 u.p. (−6,3%) sulla es. 10 (605 × 64 chiamate; in u.p. a peso 2) *(stima, ipotesi sul contenuto)*.

**Opzioni.** A. Lasciare. B. Diagnosi con 2-3 chiamate minime e il log dei corpi (M1). C. Poi, in ordine: le tre variabili sopra; una cartella di lavoro dedicata **dentro `.gradiens/`** (per esempio `.gradiens/claude/`, creata al primo uso, PER-02) passata come `cwd` a `create_subprocess_exec` (`llm/claude_code.py:94`); nient'altro che non sia nella documentazione. Attenzione: una cartella sotto `.gradiens/` resta sotto il progetto, quindi Claude Code potrebbe comunque trovare `.claude/` risalendo (non verificato): lo dirà M2.

**Qualità.** Nessun effetto: il modello riceve lo stesso messaggio e lo stesso sistema.

**Provider.** Specifica di Claude Code, **confinata** in `_ambiente()` e in `cwd`. Il corpo delle richieste (che contiene la conversazione) va scritto in una cartella dentro `.gradiens/` e cancellato subito.

**Windows e Linux.** Il formato `file:<cartella>` della variabile OTEL su Windows (percorsi con `\` e unità) **non è verificato**: chiedere la prova all'utente. La cartella di lavoro si costruisce con `pathlib`; per il servizio Windows la cartella di partenza è quella di `-WorkingDirectory` (`:207`).

**Raccomandazione.** M1 e M2 (circa 15 mila token); poi, se uno dei flag riduce i 605, applicarlo.

**Passi.** 1) M1. 2) M2 con una variabile alla volta. 3) Estendere il finto `claude` per salvare ambiente e cartella di lavoro (oggi solo `ANTHROPIC_API_KEY`, `tests/llm/test_claude_code.py:18`). 4) Modifica di `_ambiente()` o del `cwd`. 5) Verifica in produzione: `cache_scritta` per chiamata (6b-1) scende.

**Test.** `test_le_variabili_che_riducono_il_contesto_arrivano_a_claude`; `test_claude_parte_nella_cartella_dei_dati`.

**Rischi.** Basso: se una variabile cambia il comportamento del modello (non c'è motivo documentato) lo si vede in M2; dipendenza dalla versione di Claude Code. **Sforzo.** 0,5 g, soprattutto misura *(stima)*.

### 6b-7 — Il tetto per pertinenza invece che per data

**Problema.** Con tetto 10 l'utente vede i 10 paper più **recenti** tra i promossi, non i 10 più pertinenti (`esecutore.py:278-280`). Dati: dei paper valutati il 95% (19 su 20) supera la soglia 60; la pertinenza massima ha mediana 85 (es. 9: 9 paper, minimo 72, uno ≥ 90) e 79 (es. 10: 10 paper, minimo 62, nessuno ≥ 90), contro 91 per i siti *(DB)*. Né il pre-filtro (94-95% di promossi) né la soglia selezionano i paper: seleziona il tetto, per data.

**Opzioni.**

| Opzione | Costo | Note |
|---|---|---|
| A. Per data (oggi, o 6b-2) | — | quello che si vede dipende da quando è uscito il paper |
| B. Pre-filtro "a punteggio": ogni paper riceve un voto 0-10 su titolo e primi 300 caratteri; il tetto prende i migliori | circa 104.000 token (es. 10) per i 412 paper; con solo il titolo circa 63.400; in u.p. circa 247.500 e 166.500 | equivale a **circa 20 paper di tetto in meno** (circa 12 con il solo titolo), contando 5.100 token per paper di tetto; cambia ARX-02 e ARX-03 ("i più recenti" → "i più pertinenti secondo il pre-filtro") |
| C. Pre-filtro più severo ("includi solo se chiaramente pertinente") | cresce con la severità: se promuove il 50% invece del 94%, circa +11% di token per paper tenuto (1.180 invece di 630 di pre-filtro su 5.100 totali) | serve a far entrare nel tetto paper più pertinenti; senza misura è a occhio |
| D. Embedding (similarità con gli interessi) | 0 token LLM | solo descritto (6b-16) |

**Qualità.** B potrebbe migliorare molto il contenuto di una lista da 50 paper; ma il vantaggio non è misurato e il voto sul solo titolo e 300 caratteri potrebbe essere rumoroso. Misura M5: 30 paper oltre il tetto (1 richiesta all'API di arXiv più valutazioni) per vedere se la loro pertinenza è simile a quella dei 10 già valutati.

**Provider.** Esecutore, prompt e schema: provider-agnostico. **Windows e Linux.** Nessuna differenza.

**Raccomandazione.** Non ora. Prima 6b-2 e M5; si decide con la distribuzione delle pertinenze (decisione rimandata, sezione 6).

**Passi** (se approvata): 1) schema `SCHEMA_PREFILTRO_PUNTEGGIO` con `voti` e test con il finto; 2) sistema del pre-filtro con la scala dei voti; 3) ordinamento nell'esecutore e tetto per voto (parità decise per data), con test; 4) aggiornare PRD (ARX-02, ARX-03), metriche e resoconto ("si sono tenuti i più recenti" → "i più pertinenti").

**Test.** `test_il_tetto_prende_i_voti_piu_alti`; `test_a_parita_di_voto_vince_il_piu_recente`; `test_voto_mancante_conta_zero`.

**Rischi.** Medio: voto rumoroso su pochi caratteri; 14 chiamate di pre-filtro su tutti i paper (in parallelo, ma più quota); cambia il significato del tetto per l'utente. **Sforzo** 1-1,5 g *(stima)*.

### 6b-8 — Pre-filtro più corto: sommario ridotto, solo titolo, euristiche

**Problema.** Il pre-filtro manda fino a 1.500 caratteri di sommario (`prompt.py:12`, `:48`), 479 token a paper.

**Opzioni** *(modello; es. 10, se il pre-filtro dei 412 paper resta)*:

| Caratteri di sommario | Token per paper | Risparmio sul totale della es. 10 |
|---|---|---|
| 1.500 (oggi) | 479 | — |
| 1.000 | 365 | −9,2% |
| 800 | 302 | −14,1% |
| 500 | 206 | **−21,8%** |
| 300 | 140 | −27,1% |
| solo titolo | 42 | −34,9% |

Per i siti il sommario è già breve (251-287 caratteri): il solo titolo risparmia circa l'1,9% del totale. **Dopo 6b-2** si pre-filtrano 30 paper e 500 caratteri risparmiano circa 8.200 token: 1,6% del consumo di oggi (2,8% di quello nuovo).

Euristiche senza LLM (parole chiave, elenchi di termini): **non** si fanno. Il filtro deve funzionare a prescindere dalla lingua degli articoli e degli interessi, che sono testo libero: un elenco di parole andrebbe tradotto e mantenuto per ogni interesse.

**Qualità.** Un abstract dice l'argomento nelle prime frasi, ma il collegamento con un interesse può stare in fondo (il 44% degli abstract supera già i 1.500 caratteri e viene tagliato oggi). Rischio di scarti sbagliati: definitivi (la notizia diventa "vista"). Misura M6: rieseguire il pre-filtro con sommario completo, 300 caratteri e solo titolo sulle 135 notizie già mostrate; devono passarne quasi tutte (soglia proposta: almeno 98%, D4). Limite: sono notizie note come pertinenti; mancano i falsi positivi, e dei paper noti sono solo 19.

**Provider.** Provider-agnostico (`MAX_SOMMARIO` in `prompt.py:12`, per tipo di fonte). **Windows e Linux.** Nessuna differenza.

**Raccomandazione.** Solo se D1 è "no" (ARX-02 resta): 500 caratteri per arXiv. Altrimenti niente.

**Passi.** 1) Test di `messaggio_prefiltro` con tipi diversi. 2) `MAX_SOMMARIO` per tipo di fonte. 3) M6 prima di attivare.

**Test.** `test_il_sommario_dei_paper_si_taglia_a_500_caratteri`; `test_il_sommario_dei_siti_resta_a_1500`.

**Rischi.** Medio (scarti definitivi). **Sforzo** 1-2 h *(stima)*.

### 6b-9 — Blocchi più grandi (scheda breve)

**Problema.** Pre-filtro 30 (`esecutore.py:32`), argomenti 40 (`:33`). Quota fissa per paper nel pre-filtro (ingresso 1.672 e uscita 137 per blocco): 60 token per paper a blocchi da 30 (10,2% del costo di un paper), 36 a 50 (6,4%), 30 a 60 (5,4%), 23 a 80 (4,1%). Negli argomenti la parte fissa di una chiamata (strumento, contesto e sistema con 53 nomi: circa 2.900 token) è il 16% per notizia a blocchi da 40 e l'8,7% a 80.

**Opzioni considerate.** Pre-filtro 60: −2,8% token e −1,3% u.p. (es. 10); argomenti a 80: circa −0,3%. Dopo 6b-2 ancora meno.

**Perché no.** Guadagno sotto il rumore del modello; più notizie in una risposta (il ragionamento per notizia potrebbe calare); un blocco fallito costa il doppio (nuovo tentativo) e blocca più notizie; uscita di 60 notizie circa 3.200 token (circa 12 s), entro il timeout di 300 s; nessun limite di riga di comando (messaggio da stdin, tetto di 10 MB in `claude -p`, headless).

**Che cosa farebbe cambiare idea.** Un'esecuzione con migliaia di notizie nuove (prima esecuzione con finestra di 7 giorni e categorie molto attive, [piano-fase-4.md](../architettura/piano-fase-4.md)). **Windows e Linux**: nessuna differenza.

### 6b-10 — Contenuto ridotto prima della valutazione

**Problema.** `MAX_CONTENUTO = 60_000` caratteri (`esecutore.py:34`, taglio a `:422-423` con stato "contenuto parziale"). Il commento del codice dice "~15.000 token": a 2,35 caratteri per token sono circa **25.500** *(misura)*. Un articolo medio di sito vale 1.750-2.922 token *(modello)*: il taglio tocca solo la coda lunga. Un articolo al massimo costa 29.116 token grezzi e 60.919 u.p., 5,5 volte un articolo medio. Per YouTube la trascrizione è tutto il contenuto: video di 10 minuti circa 9.000 caratteri, di un'ora circa 54.000 *(stima, circa 900 caratteri al minuto di parlato)*: 7.414 token grezzi per un video da 9.000 caratteri e fino a 29.116 per uno da 60.000. Oggi nessun video è stato valutato (3 su 3 esclusi come sponsorizzati nelle es. 9 e 10).

**Opzioni.** A. Lasciare. B. Tetto più basso, per esempio 30.000 caratteri per tutti o 20.000 per i video, con "contenuto parziale" già previsto da ESE-05 ("Se il contenuto è parziale, il riassunto lo dice"): −44% su un video da 60.000 caratteri. C. Testa e coda. D. Campionamento di parti salienti senza LLM. E. Riassunto in due passi (più chiamate).

**Risparmio.** Non misurabile oggi (contenuti non salvati); −44% per un video da 60.000 caratteri con l'opzione B *(modello)*.

**Qualità.** ESE-05 chiede un riassunto che "copre tutti i punti principali, non solo l'inizio": ogni taglio lo mette a rischio su video lunghi.

**Provider.** Provider-agnostico. **Windows e Linux.** Nessuna differenza.

**Raccomandazione.** Non cambiare ora: prima la misura con 6b-1 (`contenuto.caratteri_p50/p90/max` e `troncati`, una settimana). Verificare i 6 video esclusi come "sponsorizzati" (D6): se erano falsi positivi YouTube diventa la voce più costosa per notizia.

**Passi.** 1) 6b-1. 2) Dopo una settimana, se la coda lunga esiste: costante `MAX_CONTENUTO_VIDEO` (oggi `MAX_CONTENUTO` vale per tutti i tipi, `_completa`, `esecutore.py:418-424`). 3) Aggiornare il commento sui token.

**Test.** `test_la_trascrizione_oltre_il_massimo_e_contenuto_parziale`; `test_i_siti_mantengono_il_massimo_di_prima`.

**Rischi.** Basso; copertura dei riassunti dei video lunghi. **Sforzo** 2-3 h *(stima)*.

### 6b-11 — Deduplicazione prima dell'LLM (scheda breve)

**Problema.** Lo stesso evento da più fonti costerebbe più valutazioni: `esecutore.py:263-266` toglie solo gli indirizzi già visti.

**Dato.** Tra le 82 (es. 9) e le 34 (es. 10) notizie di siti mostrate non c'è **nessuna** coppia di titoli originali con somiglianza di Jaccard ≥ 0,6 sulle parole di almeno 3 lettere; sui titoli tradotti (`titolo_it` o `titolo`) c'è 1 coppia (0,62, es. 9) *(DB; si conservano solo le notizie mostrate, quindi è un limite inferiore)*.

**Opzioni considerate.** Raggruppare i quasi-doppioni e valutare un solo rappresentante.

**Perché no.** DUP-01 e DUP-03: indirizzi diversi coesistono; notizie diverse sullo stesso evento restano separate e vanno nello stesso Argomento: togliere un quasi-doppione prima dell'LLM violerebbe DUP-03. Risparmio osservato: 0-1 notizie per esecuzione.

**Che cosa farebbe cambiare idea.** Le metriche di 6b-1 con molti doppioni (es. dopo la fase 6a, con più siti). **Windows e Linux**: nessuna differenza.

### 6b-12 — Niente rivalutazioni e igiene dei tentativi

**Problema** ([mappa A6](../architettura/mappa-moduli.md#a6-osservazioni-per-le-fasi-successive)): blocchi falliti, valutazioni fallite, dirette, resti di un'interruzione ripassano a ogni esecuzione; il nuovo tentativo scatta anche dopo un timeout (`llm/claude_code.py:76-83`: fino a 600 secondi e quota doppia per una notizia); "rate limit" è trattato come quota esaurita (`:26`, `:53`) e interrompe l'esecuzione; `pronto()` due volte (`esecutore.py:253-254`).

**Costo osservato: 0.** Nessuna notizia riesaminata (1.447 righe in `notizie_viste` = somma delle esaminate), errori LLM 0 nelle es. 9 e 10 e nessun "nuovo tentativo" nel log (sezione 1.7).

**Opzioni.** A. Lasciare. B. `pronto` una volta per provider diverso (un processo e circa 1-2 s in meno; token nulli per ipotesi). C. Niente nuovo tentativo dopo un timeout (risparmia fino al 100% di una notizia lenta). D. Distinguere un limite passeggero da quota esaurita. E. Contare nei token anche i tentativi falliti (metrica `tentativi` di 6b-1; il JSON di un tentativo fallito per timeout non esiste).

**Risparmio.** 0 osservato; protezione. **Qualità.** Nessun effetto.

**Provider.** `pronto`/`chiedi` nel provider; B è nell'esecutore. **Windows e Linux.** Nessuna differenza.

**Raccomandazione.** B subito; C e D dopo aver visto un caso vero nelle metriche: toccano la robustezza e vanno decise con le fasi di debugging.

**Passi.** 1) B: nel ciclo di `esecutore.py:253-254` si chiama `pronto()` una sola volta per istanza di provider distinta (stesso oggetto o stesso `nome`). 2) Metrica `tentativi` (6b-1). 3) Se un caso vero lo giustifica: nel `chiedi` di `claude_code.py` il timeout non si riprova (`test_timeout`, `tests/llm/test_claude_code.py:77`, da aggiornare). 4) Se serve, distinguere "rate limit" passeggero da quota (testo e `api_error_status`).

**Test.** `test_pronto_una_volta_per_provider_uguale`; poi `test_timeout_non_si_riprova`.

**Rischi.** Basso (B); medio per C e D (robustezza). **Sforzo** 2-3 h per B *(stima)*.

### 6b-13 — Modello per fase (scheda breve)

**Problema.** `impostazioni.provider_*` e `modello_*` hanno default `claude-code` e `haiku` (`dati/modelli.py:31-34`) e non si cambiano dalla dashboard (7a rimandata, [piano-fase-4.md](../architettura/piano-fase-4.md)). L'alias `haiku` è Haiku 5.5 sull'API di Anthropic e Haiku 4.5 su Bedrock, Google Cloud e Foundry (model-config).

**Opzioni considerate.** A. Alias `haiku` (oggi). B. ID esplicito `claude-haiku-5-5`: insensibile a un cambio dell'alias, ma **non segue gli aggiornamenti** dell'alias (resterebbe su una versione vecchia). C. Haiku 4.5: 1,00 / 5,00 USD per milione contro 0,10 / 0,50 (10 volte a listino; nella misura 7,5 volte, stessi 8 id, più lento, minimo di cache 4.096 token: il prefisso di Gradiens, circa 1.070, non verrebbe messo in cache); come la quota pesi i modelli non è scritto (2.2: Opus "usa molta più quota"). D. Sonnet per la valutazione: qualità maggiore e più quota, contro l'obiettivo.

**Perché no.** Haiku 5.5 è già il modello più economico; le alternative costano più quota o non seguono l'alias.

**Che cosa farebbe cambiare idea.** Un cambio dell'alias che peggiora qualità o consumo (lo mostrerebbero le metriche, campo `modello`). **Windows e Linux**: nessuna differenza. **Rischi / sforzo**: nessuna modifica (B: 1 riga nel database, 15 minuti).

### 6b-14 — Carico fisso: schema, processo aperto, più notizie per chiamata (scheda breve)

**Problema.** Ogni chiamata paga lo schema (circa 480 token in ingresso) e il contesto (`llm/claude_code.py:85-92`, opzioni `:18-25`).

**Opzioni considerate.**
- **Senza `--json-schema`** (risposta testuale validata dall'app). Misura (chiamata 8 contro 4): −484 token in ingresso, −179 in uscita (di cui −117 di ragionamento secondo i JSON persi, forse non dovuti allo schema), −11% di costo nozionale, 7,9 s contro 5,5 s (una prova). Su una esecuzione come la 10: −41.200 token (−8,0%) con −62 token d'uscita per chiamata (senza i −117 di ragionamento) e −48.700 (−9,4%) con −179; in u.p. circa −2,6%. Reintroduce errori di lettura (l'ADR 0006 sceglie lo schema proprio per questo); con lo schema Claude Code ritenta da solo fino a 5 volte (`MAX_STRUCTURED_OUTPUT_RETRIES`, predefinito 5) se la risposta non è valida; senza, i tentativi sono dell'app. È specifica di Claude Code: l'API di Claude ha uscite strutturate native.
- **Processo `claude` sempre aperto** (`--input-format stream-json`, scartato dall'ADR 0006): si risparmia il carico fisso (a prezzi dell'API circa 1,3 mila u.p. a chiamata: i 605 riscritti a peso 2 più il prefisso letto a 0,1), ma ogni notizia rilegge a 0,1 tutta la cronologia delle precedenti: alla k-esima 0,1 × (k − 1) × 4.026 (paper) o 5.309 (siti) = 403 o 531 × (k − 1) u.p. Pareggio marginale: k ≈ 4,3 (paper) o 3,5 (siti); cumulativo: conviene solo fino a 6-8 notizie. Vale solo con i pesi dell'API: **nei token grezzi non conviene mai**, perché la cronologia riletta conta per intero (con 45 notizie la somma supera 4 milioni di token). In più, rischio di contaminazione tra notizie e di compattazione automatica. L'ADR 0006 è **confermato con i numeri di oggi**.
- **Più notizie per chiamata**: 6b-4 per i paper. Per i siti, lotti di 2-3 articoli per lunghezza: −18% / −24% di token per articolo (circa −6,5% / −8,7% del totale della es. 10) e circa −6% / −8% di u.p. per articolo *(modello)*; rischio: articoli lunghi (fino a 60.000 caratteri), riassunti più confusi, salvataggio a gruppi.

**Perché no (ora).** Schema: guadagno modesto in u.p. e rischio di parsing; processo aperto: costa di più oltre poche notizie; lotti per i siti: da rivalutare dopo 6b-4.

**Che cosa farebbe cambiare idea.** M3 positiva sui lotti dei paper (allora i lotti per i siti); una pagina ufficiale che dica che il ragionamento adattivo costa meno in conversazioni lunghe.

**Rischio da seguire (ADR 0006).** La pagina headless (letta il 13 novembre) dice che `--bare` diventerà il predefinito per `-p` in una versione futura e che in bare Claude Code non legge le credenziali OAuth dell'abbonamento: le chiamate di Gradiens (`--safe-mode`, `llm/claude_code.py:18-25`) potrebbero smettere di funzionare con l'abbonamento finché non si passa un'opzione esplicita. Non è una proposta 6b: basta ricontrollare a ogni aggiornamento di Claude Code. **Windows e Linux**: nessuna differenza.

### 6b-15 — Argomenti e proposte (scheda breve)

**Problema.** `_argomenti` (`esecutore.py:325-354`) e `_proposte` (`:356-379`): argomenti 22.315 token (4,3%, es. 10) e 40.944 (3,7%, es. 9). Per chiamata: sistema 756 caratteri più 46 per ogni argomento esistente (53 all'inizio della es. 10 *(DB)*, ricalcolati a ogni blocco perché l'elenco cambia, ADR 0008) più 40 notizie da 720 caratteri; uscita circa 2.900 (stima). Costo per notizia mostrata: circa 448 token e 1.117 u.p.: con tetto 50 (circa 85 mostrate) sono 38.000 token. Proposte: 0 chiamate nelle es. 9 e 10; al massimo 1 per interesse con 3 Cuori nuovi più 1: circa 4-5 mila token in ingresso e meno di 1.000 in uscita ciascuna (stima), circa 20-25 mila token nel caso peggiore (4 chiamate).

**Opzioni considerate.** Blocchi da 80 (−0,3%); salto dell'elenco quando nessun argomento è cambiato (non applicabile: cambia a ogni blocco); escludere i paper dagli argomenti (il prompt già dice "nessuno" per i paper: `prompt.py:106`): risparmierebbe una quota crescente con il tetto (con tetto 50 circa 6 notizie mostrate su 10 sarebbero paper).

**Perché no.** Peso piccolo; ADR 0008 e ESE-08 non escludono i paper: **non cambiare senza decisione dell'utente**.

**Che cosa farebbe cambiare idea.** Un tetto alto che porti gli argomenti sopra il 10% del consumo. **Windows e Linux**: nessuna differenza.

### 6b-16 — Leve descritte e non pianificate (decisione 6; scheda breve)

**Modello locale per il pre-filtro (LLM-03).** Toglierebbe tutto il pre-filtro dalla quota: 51,9% dei token oggi (es. 10), ma circa **14,5%** dopo 6b-2 (9,8% nella es. 9). Sul portatile di riferimento (i7, 16 GB, nessuna GPU) un modello da 7-9 miliardi di parametri elabora il prompt a decine di token al secondo *(ipotesi, mai misurata: Ollama e LM Studio non sono installati)*: i 239.085 token di ingresso del pre-filtro della es. 10 richiederebbero da 40 minuti a oltre 2 ore (ipotesi: 30-100 token al secondo), prima della generazione. Il PRD (`LLM-03`) lo prevede e il piano ([piano-fase-4.md](../architettura/piano-fase-4.md), 7a) lo rimanda proprio perché non si può provare qui.

**Embedding.** Una similarità tra abstract e interessi sostituirebbe il pre-filtro dei paper con 0 token LLM e darebbe anche un ordine per pertinenza (6b-7). Costo in CPU *(stima)*: circa 206 mila token di abstract in 1-3 minuti con un modello piccolo multilingue. Costi: una dipendenza grossa (da cento a poche centinaia di MB, da decidere con un ADR), la qualità sui testi liberi e sulle lingue diverse non misurata (il filtro deve funzionare in ogni lingua). Vale come 6b-2 sui paper (circa 47% della es. 10) con in più l'ordine per pertinenza.

**API di Claude a pagamento.** Con prezzi di listino Haiku 5.5 e cache a 1 ora, l'esecuzione 10 costerebbe circa 0,12 USD e la 9 circa 0,26 USD: 3,7 e 7,8 USD al mese a 30 esecuzioni; con la cache spenta 2,8 e 6,0; con la Batch API (−50%, non adatta a chi vuole il risultato al mattino) 1,4 e 3,0. Con 6b-2 la es. 10 scenderebbe a circa 2,2 USD al mese a 1 ora. Per Haiku 4.5 circa dieci volte. **Fuori dalla decisione 6**: è solo un ordine di grandezza per decidere in futuro; `LLM-02` la prevede come alternativa e il PRD dice "nessun tetto di spesa" (ESE-11).

**Windows e Linux.** Un modello locale e gli embedding girano su entrambi (dipendenze con ruote per Windows e Linux da verificare); l'API non dipende dal sistema. Nessun passo, test o sforzo: non si pianificano.

---

## 4. Di quanto si possono alzare i tetti a quota costante

### 4.1 La combinazione raccomandata

6b-1 → 6b-2 → 6b-3 senza altre ipotesi sul modello della quota; poi 6b-4 e 6b-5 dopo le misure. Il modello usa il budget dell'esecuzione 10 (516.346 token del modello, 516.750 reali; circa 1,23 milioni di u.p.) e dell'esecuzione 9 (1.113.722; 1.112.754 reali; circa 2,61 milioni).

### 4.2 Tetto arXiv sostenibile

**Ipotesi comuni**: promossi dal pre-filtro 93,7% (es. 10) e 95,0% (es. 9); 95% dei valutati sopra soglia; abstract da 1.442 caratteri; articoli di siti come nella esecuzione di riferimento (1.750 token nella 10, 2.922 nella 9); 35 e 90 valutazioni di siti; blocchi da 30 e 40; regole degli scenari di 2.3.

**Esecuzione 10** (budget 516.346 token; 1,23 milioni di u.p.): tetto 10 oggi.

| Scenario | Leve e ipotesi | Consumo a tetto 10 (token / u.p.) | Tetto sostenibile (token / u.p.) |
|---|---|---|---|
| P1 prudente | 6b-2 | 56,2% / 60,3% | 56 / 48 |
| P2 prudente con cache | 6b-2 e 6b-3 | 56,2% / 50,9% | 56 / 62 |
| P3 intermedio | + lotti di 5, ragionamento per paper invariato | 53,3% / 50,0% | 80 / 68 |
| P4 intermedio | + effort basso (ragionamento −27%, una sola prova) | 50,5% / 44,2% | 87 / 84 |
| P5 | nessun pre-filtro arXiv (ARX-02 tolto per arXiv), lotti di 10, ragionamento per paper invariato, effort basso, cache a 5 minuti | 46,8% / 41,9% | 122 / 97 |
| O1' ottimistico | come P5 ma ragionamento per paper 700 (**ipotesi**) e senza effort basso | 48,9% / 46,4% | 119 / 92 |
| O2' ottimistico | come O1' con ragionamento per paper 350 (**ipotesi**) | 48,2% / 44,9% | 138 / 118 |
| O1 ottimistico | O1' con effort basso (×0,73 anche sul ragionamento ipotizzato) | 46,3% / 41,0% | 133 / 114 |
| O2 ottimistico | O2' con effort basso | 45,9% / 40,0% | 151 / 139 |

**Esecuzione 9** (budget 1.113.722 token; 2,61 milioni di u.p.): P1 85 / 75; P2 85 / 112; P3 122 / 120; P4 142 / 156; P5 193 / 177; O1' 181 / 160; O2' 212 / 205; O1 210 / 202; O2 239 / 248.

**Lettura.**
- Prudente = P1-P2: **circa 50** (48-62 sulla 10; 75-112 sulla 9). Non dipende da nessuna misura nuova, salvo il peso della quota per P2.
- Intermedio = P3-P4: 68-87 (120-156 sulla 9); dipende da M3 (lotti) e M4 (ragionamento).
- Ottimistico = O1'-O2: 92-151 (160-248 sulla 9); dipende dall'ipotesi che i lotti riducano il ragionamento per paper a 700 o 350 (da circa 1.000), mai misurata, e dall'effort basso.
- **Quanti paper si esaminano e si valutano**: i paper raccolti nella finestra restano tutti "esaminati" (412 e 677: la raccolta è gratuita); con 6b-2 se ne pre-filtrano ⌈T/(30 p)⌉ × 30 (30 con tetto 10, 60 con tetto 56) e se ne valutano T. Valutare **tutti** i 412 paper costerebbe 2,0 (lotti da 10, ragionamento 350, effort basso), 2,6 (lotti da 10, ragionamento invariato) o 4,0 volte (singola) il budget in token grezzi: non è un obiettivo realistico con questa quota.
- **Sensibilità** (a budget fisso, quello della es. 10): la quota di paper promossi conta poco (tetto 55-56 con 85-99%); la lunghezza degli articoli dei siti conta molto (tetto 56 con 1.750 token, 48 con 2.922); il ragionamento nei lotti è l'ipotesi più importante.

### 4.3 Più articoli di siti

Una notizia nuova di sito in più costa (pre-filtro, 42% di promossi, valutazione, argomenti) circa 2.600 token e 6.500 u.p. *(modello)*. Il risparmio di 6b-2 (circa 226.000 token) si può spendere per paper e per siti: tutto sui siti darebbe circa **85 notizie nuove di siti in più** (da 84 a 169, token; da 84 a 157, u.p.), ma il limite dei siti non sono i token: è la scoperta delle notizie (fase 6a). Riparto a titolo di esempio *(modello, 6b-2 senza lotti)*:

| Tetto arXiv | Notizie nuove di siti sostenibili (token / u.p.) | Rispetto a 84 |
|---|---|---|
| 10 | 169 / 157 | +101% / +87% |
| 20 | 152 / 140 | +81% / +67% |
| 30 | 128 / 117 | +52% / +39% |
| 40 | 112 / 100 | +33% / +19% |
| 50 | 95 / 84 | +13% / 0% |

### 4.4 Piano di verifica su un'esecuzione reale

**Principio.** Una leva alla volta, una esecuzione (anche quella programmata, 07:00 per impostazione predefinita, `ESE-01`) per leva; confronto con le metriche di 6b-1. La prima esecuzione dopo 6b-1 è la **misura di base** senza costi extra.

**Che cosa misurare prima e dopo** (metriche di 6b-1, tutte aggiunte, nessuna modifica di schema; chiavi di `esecuzioni.metriche`, fuori da `token`):

| Metrica | Dove | A che cosa serve |
|---|---|---|
| `dettaglio_token.<ruolo>.{chiamate, ingresso_semplice, cache_scritta_1h, cache_scritta_5m, cache_letta, ragionamento, secondi}` | per ruolo | pesi in u.p. veri, effetto di 6b-3, 6b-5 |
| `chiamate[]` con `{fase, tipo, notizie, ingresso_semplice, cache_scritta, cache_letta, uscita, ragionamento, secondi, tentativi}` | una riga per chiamata | sostituisce il modello con dati; costo fisso per fase |
| `fonti.<tipo>.contenuto.{n, caratteri_p50, caratteri_p90, caratteri_max, troncati}` | per tipo | lunghezza degli articoli e dei video, taglio a 60.000 (6b-10) |
| `fonti.arxiv.{prefiltrate, promosse}` | arXiv | verifica del 93,7% di promossi; equivalenza di 6b-2 |
| Per leva: token per paper valutato, per notizia mostrata, per notizia di sito; quota di ogni fase; numero di chiamate; paper mostrati | derivate | confronto prima e dopo |

**Come confrontare la qualità del filtro** (proposte; soglie da concordare, D4):
1. **6b-2**: nessun confronto in produzione se il pre-filtro è deterministico; test automatico con un elenco atteso. In produzione: la quota di paper valutati sopra soglia resta intorno al 95%.
2. **6b-4 e 6b-5**: rivalutare i **19 paper noti** (abstract e punteggi nel DB) con la variante e confrontare punteggio, lato della soglia 60 e riassunto (M3, M4).
3. **Pre-filtro più corto o severo** (6b-7, 6b-8): rieseguire sulle **135 notizie già mostrate** (19 paper e 116 di siti) e contare quante ne perde (M6). Limite: sono tutte pertinenti: mancano i falsi positivi.
4. **Campione etichettato a mano**: l'utente segna con il Cuore una trentina di notizie in una settimana (oggi il DB ha 1 Cuore su 146): serve anche a `INT-04`. Con 50 notizie etichettate si può stimare richiamo e precisione dei pre-filtri nuovi.

**Quanta quota consuma la verifica stessa.** Strumentazione e confronto di metriche: **zero** (i numeri sono già nelle risposte). Le misure M1-M7 della sezione 4.5 sì: in tutto, M1-M6 circa 0,6-0,8 di una esecuzione tipo (es. 10 = 516.750 token); M7 da 0,6 a 1,2 esecuzioni.

**Dove tenere gli script di misura** *(decisione dell'utente, D7)*. In questa analisi gli script stavano fuori dal progetto e si sono persi. CLAUDE.md dice "Lavora SOLO dentro questa cartella": all'implementazione serve un posto dentro la repository (per esempio `scripts/misura/`, versionato, senza dati) e i risultati stanno in `.gradiens/misure/` (PER-02, esclusi da git).

**Passi su Windows e Linux** (CLAUDE.md: istruzioni accanto):

| Passo | Linux | Windows (PowerShell) |
|---|---|---|
| Test del codice | `uv run pytest` | `uv run pytest` |
| Eseguire uno script di misura (come `misura.py` del 12 nov, da riscrivere) | `uv run python scripts/misura/misura.py <nome>` | `uv run python scripts\misura\misura.py <nome>` |
| Una variabile d'ambiente per la sola prova | `FORCE_PROMPT_CACHING_5M=1 uv run python scripts/misura/misura.py ...` (vale solo per quel comando) | `$env:FORCE_PROMPT_CACHING_5M = "1"; uv run python scripts\misura\misura.py ...; Remove-Item Env:FORCE_PROMPT_CACHING_5M` (la variabile resta nella sessione finché non la si toglie) |
| Lanciare un'esecuzione | `uv run gradiens esegui` | `uv run gradiens esegui` |
| Leggere le metriche | Resoconto della dashboard; oppure uno script che apre `.gradiens/gradiens.db` con `sqlite3.connect("file:...?mode=ro", uri=True)` | stesso script |
| Tenere i corpi delle richieste di M1 | variabile `OTEL_LOG_RAW_API_BODIES=file:<progetto>/.gradiens/otel` e cancellare la cartella a fine prova | formato `file:` con percorsi Windows **non verificato**: chiedere la prova |

Il ramo Windows non è stato provato da questa analisi (solo letto). Le leve che toccano il provider passano variabili d'ambiente al processo `claude`, senza comandi di shell (CLAUDE.md: liste di argomenti, mai `shell=True`). La prova su Windows va chiesta all'utente per 6b-3 e 6b-6 (variabili d'ambiente e, per M1, il formato `file:` della variabile OTEL).

### 4.5 Misure che richiedono altra quota (da chiedere all'utente)

Costi in token grezzi, **stime** dal modello; in due tempi: prima M1 e M2. Dopo ogni misura va riconfermato il campo `thinking_tokens` (1.5).

| Misura | Che cosa risponde | Come | Costo (stima) |
|---|---|---|---|
| M1 Contesto di Claude Code | che cosa sono gli 825 token fissi (6b-6) | 2 chiamate minime (con e senza schema) con `OTEL_LOG_RAW_API_BODIES`; riconferma dei campi `thinking_tokens` | circa 3.000 |
| M2 Varianti del carico fisso | cache a 5 minuti (`usage.cache_creation.ephemeral_5m_input_tokens`), cache spenta, `CLAUDE_CODE_DISABLE_ATTACHMENTS`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS`, cartella dedicata: quante scritture restano | 8 chiamate minime, una variabile alla volta | circa 12.000 |
| M3 Lotti contro singola | qualità e ragionamento di 6b-4 | i 19 paper noti: 2 lotti da 10 (circa 44.000) e 4 da 5 (circa 48.000); 38.000 e 42.000 se il ragionamento fosse 700 | circa 82.000-92.000 |
| M4 Ragionamento | effetto dell'effort basso (con la **variabile** d'ambiente, come in produzione) e di "decidi senza spiegare" (6b-5) | 8 paper noti × 3 varianti (24 chiamate; 16 se si riusano i punteggi salvati come variante base) | circa 64.000-97.000 |
| M5 Campione oltre il tetto | la pertinenza dei paper che oggi si scartano (6b-7) | 1 richiesta all'API di arXiv (200 paper, categoria generica) e 30 paper valutati a lotti di 10 (circa 70.000 con ragionamento invariato, 60.000 se fosse 700) o singoli (circa 121.000) | 60.000-121.000 |
| M6 Pre-filtro con e senza sommario | perdita del pre-filtro con sommario completo, 300 caratteri e solo titolo (6b-8); blocchi da 30 | le 135 notizie già mostrate, 3 varianti × 5 blocchi (44.000 + 38.000 + 23.000) | circa 105.000 |
| M7 Peso della quota | quanto pesano cache scritta, letta, uscita nella quota (6b-3, 6b-5) | due bracci da almeno 10 chiamate di pre-filtro (cache 1 ora contro 5 minuti), leggendo la percentuale d'uso con `stream-json` (`rate_limit_event`, da riconfermare) prima e dopo; **nessun altro uso di Claude** nella finestra; si ripete se la variazione è sotto 3 punti | 320.000-640.000 |

---

## 5. Ordine consigliato e dipendenze

In ordine di rapporto beneficio / sforzo:

| # | Proposta | Beneficio | Sforzo | Dipende da | Decisione |
|---|---|---|---|---|---|
| 1 | 6b-1 Metriche | abilita tutto; zero quota | 0,5 g | nessuna | **nessuna: subito** |
| 2 | 6b-2 Pre-filtro fino al tetto | −44% / −34% token | 1-1,5 g | 6b-1 (per i campi nuovi) | **D1 (ARX-02)** |
| 3 | 6b-3 Cache a 5 minuti | fino a −21% u.p. (ipotesi) | 1-2 h | 6b-1 (per verificare) | nessuna |
| 4 | 6b-12 `pronto` una volta | 1-2 s e un processo | 2 h | nessuna | nessuna |
| 5 | M1, M2 → 6b-6 Contesto | fino a −7,5% | 0,5 g | M1, M2 | D3 (quota per misurare) |
| 6 | M3 → 6b-4 Lotti | −38% per paper | 1-1,5 g | 6b-2, M3 | decisione rimandata (dopo M3) |
| 7 | M4 → 6b-5 Ragionamento | −3,7% / −7,8% (o più) | 0,5 g | M4 | D4 |
| 8 | M5 → 6b-7 Per pertinenza | qualità | 1-1,5 g | 6b-2, M5 | decisione rimandata (dopo M5) |
| 9 | 6b-10 Contenuto, 6b-14 lotti per i siti | da misurare | 2-3 h | 6b-1, 6b-4 | D6 |
| — | 6b-9, 6b-11, 6b-13, 6b-15 | — | — | — | **lasciare così** |

**Subito, senza decisioni**: 6b-1, 6b-12 (solo `pronto`), 6b-3 dopo 6b-1. **Dipende da una decisione**: 6b-2 (D1), 6b-5 (D4), 6b-6 e M1-M7 (D3), 6b-10 (D6).

**Rischio da seguire (non è una proposta 6b)**: `--bare` come predefinito di `claude -p` (riepilogo, punto 8; 6b-14). Da ricontrollare a ogni aggiornamento di Claude Code, anche prima di ogni misura.

---

## 6. Domande per l'utente

Una alla volta; ognuna con la mia risposta consigliata. Sono solo le scelte che dipendono dall'utente oggi.

**D1. Può cambiare `ARX-02` ("tutti i paper nuovi passano dal pre-filtro") in "passano dal più recente, a blocchi, finché i promossi riempiono il tetto"?**
Consigliata: sì. Valutano gli stessi paper di oggi (se il pre-filtro è deterministico), con il 44% di token in meno nella es. 10; oggi il pre-filtro di arXiv serve solo a tenere fuori dal tetto il 5-6% dei paper e costa circa 226.000 token.

**D2. Che tetto arXiv vorrebbe leggere ogni giorno (oggi 10)?**
Consigliata: 30 al primo passo, 50 dopo le misure. Il solo 6b-2 sostiene circa 50, ma con soglia 60 il 95% dei paper valutati la supera: una lista da 50 è lunga (la dashboard ordina per pertinenza, Telegram mostra le prime 3).

**D3. Autorizza le misure che consumano quota, in due tempi?** Prima M1 e M2 (circa 15 mila token), poi M3-M6 (circa 310-415 mila, 0,6-0,8 di una esecuzione) e, solo se vuole sapere come la quota pesa cache e ragionamento, M7 (0,6-1,2 esecuzioni, senza usare Claude per qualche ora).
Consigliata: sì ai primi due tempi; M7 dopo 6b-1 e 6b-2. M1-M2 decidono se vale la pena di toccare contesto e cache; M3-M6 rendono sicure 6b-4, 6b-5, 6b-8; M7 decide se 6b-3, 6b-4 e 6b-5 valgono in quota o solo in token.

**D4. Quanta perdita di notizie pertinenti accetta quando cambia il filtro o la valutazione?**
Consigliata: per la valutazione (lotti, ragionamento ridotto) al massimo il 5% di notizie che cambiano lato rispetto alla soglia 60 e nessun errore fattuale in 5 riassunti letti; per il pre-filtro al massimo il 2% (richiamo ≥ 98% sulle 135 note), perché uno scarto sbagliato è definitivo (la notizia diventa "vista").

**D5. Dove spendere la quota liberata: più paper, più articoli di siti (fase 6a) o margine?**
Consigliata: metà e metà: tetto 30-50 e il resto come margine per i siti, il cui vero limite è la scoperta.

**D6. Guarda nel resoconto delle esecuzioni 9 e 10 i 6 video YouTube esclusi come "sponsorizzati" (titoli e indirizzi sono in `metriche.fonti.youtube.notizie_escluse`) e dice se erano davvero sponsorizzati?**
Consigliata: sì, prima di toccare il taglio dei contenuti: se erano falsi positivi YouTube diventa la voce più costosa per notizia (7-29 mila token per video).

**D7. Dove tenere gli script di misura dentro la repository?**
Consigliata: `scripts/misura/`, con i risultati in `.gradiens/misure/` (esclusi da git); CLAUDE.md non ammette lavoro fuori dalla cartella.

**Decisioni rimandate a dopo le misure** (si chiedono con i dati):
- *Tetto per data o per pertinenza* (6b-7): dopo M5. Consigliata: per data ora; per pertinenza costerebbe circa 104.000 token a esecuzione (circa 20 paper di tetto) e il vantaggio non è misurato.
- *Valutazione dei paper a lotti di 5* (6b-4): dopo M3, con i criteri di D4 e con la valutazione singola come ripiego per gli id mancanti. Il risparmio è del 38% dei token per paper; il rischio è nella qualità dei riassunti (ESE-05).

---

## 7. Fonti esterne

Verifica **12 novembre 2026** = fatta da me (analista); **12-13 novembre** = riverificata dal coordinatore (tutte confermate); **13 novembre** = letta dal coordinatore. Le frasi tra virgolette sono traduzioni o parafrasi dell'inglese originale, salvo dove è citato l'originale.

| URL | Verifica | Che cosa se n'è preso | Che cosa non dice |
|---|---|---|---|
| https://platform.claude.com/docs/en/about-claude/pricing | 12; 12-13 | Prezzi per milione di Haiku 5.5 (ingresso 0,10; cache 5 min 0,125; cache 1 h 0,20; lettura 0,01; uscita 0,50; oltre 100.000 token 0,50 / 0,625 / 1 / 0,05 / 2,50) e Haiku 4.5 (1 / 1,25 / 2 / 0,10 / 5); Batch API −50%; token del prompt di sistema "per l'uso di strumenti" (Haiku 5.5: 286 con scelta automatica, 406 con scelta forzata; Haiku 4.5: 496 / 588); nuovo tokenizzatore con circa +30% di token | non dice come la quota dell'abbonamento pesa i token |
| https://platform.claude.com/docs/en/build-with-claude/prompt-caching | 12 | Minimo di 512 token per Haiku 5.5 e 4.096 per Haiku 4.5; scadenza di 5 minuti o 1 ora; moltiplicatori 1,25 / 2 / 0,1; prefisso strumenti, sistema, messaggi; corrispondenza esatta | letta solo la prima parte (0-100.000 di 167.602 caratteri); non parla di ITPM nel dettaglio né dei provider compatibili OpenAI |
| https://code.claude.com/docs/en/prompt-caching | 12; 12-13 | TTL di 1 ora con abbonamento per la conversazione principale (compreso `-p`); ordine `FORCE_PROMPT_CACHING_5M`, `CLAUDE_CODE_PROMPT_CACHE_TTL` (da v2.1.242), impostazione, `ENABLE_PROMPT_CACHING_1H`, predefinito; `DISABLE_PROMPT_CACHING` e `DISABLE_PROMPT_CACHING_HAIKU`; ambito della cache (macchina e cartella); controllo con `claude -p "hello" --output-format json` e `usage.cache_creation` (`ephemeral_1h_input_tokens`, `ephemeral_5m_input_tokens`) | non dice come cache scritta e letta pesano sulla quota |
| https://code.claude.com/docs/en/env-vars (seconda metà, offset 100000) | 12; 12-13 | `MAX_STRUCTURED_OUTPUT_RETRIES` (predefinito 5), `MAX_THINKING_TOKENS` (nessun effetto su Haiku 5.5), `OTEL_LOG_RAW_API_BODIES` (`1` o `file:<dir>`, ignorata nelle impostazioni di progetto e locali), `CLAUDE_CODE_SAFE_MODE`, `DISABLE_PROMPT_CACHING*`, `FORCE_PROMPT_CACHING_5M`, `ENABLE_PROMPT_CACHING_1H`; esistenza di `CLAUDE_CODE_DISABLE_ATTACHMENTS`, `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS` | la prima metà della pagina l'ha letta l'utente nella misura del 12 novembre; non dice se le tre variabili riducano i token fissi |
| https://code.claude.com/docs/en/costs | 12; 12-13 | "Claude Code charges by API token consumption"; il ragionamento si paga come uscita; la cronologia si rilegge "at the cached token rate" e consuma quota per tutta la conversazione; `/usage` | nessun peso numerico dell'abbonamento |
| https://support.claude.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan | 12 | Limite di sessione di 5 ore e settimanale condivisi con Claude | non descrive come si misura l'uso; non cita la cache né `-p` |
| https://support.claude.com/en/articles/9797557-usage-limit-best-practices | 12 | Fattori: lunghezza di messaggio e conversazione, modello, effort, strumenti; il contenuto in cache conta meno quando riusato (progetti) | nessuna formula; parla di claude.ai |
| https://support.claude.com/en/articles/11647753-how-do-usage-and-length-limits-work | 12 | Conferma dei fattori; l'effort alto usa più token | non definisce il calcolo; non tratta la cache |
| https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code | 12 | Opus "usa molta più quota" | non descrive Pro e Max, né la cache, né `-p`, né la lettura dei limiti |
| https://support.claude.com/en/articles/8324991-about-claude-s-pro-plan-usage | 12 | — | pagina non trovata (errore 404) |
| https://code.claude.com/docs/en/statusline | 12 | `rate_limits.five_hour` e `seven_day` (`used_percentage`, `resets_at`) per abbonati Pro, Max, Ultra | solo modalità interattiva; non cita `rate_limit_event` |
| https://code.claude.com/docs/en/model-config | 12; 12-13 | `haiku` = Haiku 5.5 sull'API di Anthropic e Haiku 4.5 sugli altri; livelli di effort, predefinito `medium`; `CLAUDE_CODE_EFFORT_LEVEL` prevale su `--effort`; ragionamento sempre adattivo su Haiku 5.5 e non spegnibile; si può dire nel prompt di pensare di più o di meno | non dice quanto meno pesa Haiku sulla quota |
| https://code.claude.com/docs/en/headless | 12; 12-13; 13 | `stream-json`; con `--system-prompt` niente istantanea di git; stdin fino a 10 MB; eventi documentati `system/init`, `system/api_retry`, `stream_event`, `result` (**non** `rate_limit_event`); **13 novembre**: `--bare` "is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release"; in bare le credenziali OAuth dell'abbonamento non si leggono (serve `ANTHROPIC_API_KEY`) | non dice quando |
| https://code.claude.com/docs/en/cli-reference | 12 | `--system-prompt`, `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__`, `--exclude-dynamic-system-prompt-sections` (ignorato con `--system-prompt`), `--effort`, `--safe-mode`, `--input-format` | nessun flag per accorciare il contesto aggiunto |
| https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts | 12 | Promemoria aggiunti nella conversazione; variabili per spegnerli; `OTEL_LOG_RAW_API_BODIES=file:` per vedere la richiesta | non elenca il contenuto dei 605 token |
| https://platform.claude.com/docs/en/api/openai-sdk (porta a `.../cli-sdks-libraries/libraries/openai-sdk`) | 12 | Compatibilità OpenAI: **niente cache dei prompt**; `reasoning_effort` ignorato; il ragionamento non è restituito; `response_format` solo `json_schema` con `strict: true`; `usage.prompt_tokens_details` sempre vuoto | — |
| https://developers.openai.com/api/docs/guides/prompt-caching (da platform.openai.com) | 12 | Cache automatica, minimo 1.024 token (GPT-5.6 e successivi), sconto fino al 95%, prefisso identico, contenuto statico per primo | non riguarda Ollama né LM Studio |

---

## Appendice A — Errori e imprecisioni trovati nella mappa e in altri documenti

Nessuna delle cifre di [mappa A2 e C3](../architettura/mappa-moduli.md) è risultata sbagliata: verificati il numero di chiamate (17 + 45 + 2 e 29 + 100 + 3), i token per esecuzione, i tagli (1.500, 600 e 60.000 caratteri), i blocchi (30 e 40), i 633 e 376 paper oltre il tetto, le righe di codice citate per i quattro punti di chiamata. Da correggere o precisare:

1. **A6, riga sulla cache** ("Ipotesi: il riuso della cache potrebbe non avvenire ... probabilmente sotto la lunghezza minima"): **smentita dalla misura**. Il prefisso (strumento più sistema, circa 1.070-1.260 token) si rilegge dalla cache (717 token nella chiamata 2; 6.181 nelle 5 e 6) e il minimo di Haiku 5.5 è 512 token (pagina della cache). Il riuso c'è ma è piccolo e solo sul prefisso.
2. **A6, "Il pre-filtro scarta poco: 63 su 499 e 109 su 869"**: giusto per `scartate_prefiltro`, ma incompleto: il pre-filtro scarta anche le **sponsorizzate** (15 e 23); in tutto 78 su 499 (15,6%) e 132 su 869 (15,2%). Per tipo (es. 10 / es. 9): arXiv 6,3% e 5,0%, siti 58,3% e 50,3%. Il "scarta poco" vale solo per arXiv.
3. **A2/A6, "La quota rimasta non si legge mai"**: vero per l'app e per la documentazione; in `stream-json` ho visto il 12 novembre un `rate_limit_event` con le percentuali delle finestre di 5 ore e 7 giorni, ma nei JSON poi persi e non descritto nelle pagine ufficiali: da riconfermare.
4. **A2, riga 2 della tabella**: il taglio a 60.000 caratteri è in `esecutore.py:34` con il commento "~15.000 token"; con 2,35 caratteri per token sono circa 25.500 (non è un errore della mappa, ma del commento del codice).
5. **ADR 0006** (non è la mappa): riporta "~700 token" di contesto con 2.1.318; la misura del 12 novembre dà 1.318 con lo schema e 837 senza, con Claude Code 2.1.316: o la versione è un refuso o è cambiato il contesto; "qualche centinaio di token di uscita in più" per lo schema: misurati circa 130-180. L'ADR non considera che `--bare` possa diventare il predefinito di `-p` (riepilogo, punto 8).
6. **ADR 0006**, "così le chiamate successive la rileggono dalla cache": vero per il prefisso (7-8% dell'ingresso di un pre-filtro, 53% di una valutazione di paper), non per il messaggio.

## Appendice B — Metodo e limiti

- **Metodo**: lettura del codice e della documentazione; query in sola lettura (`mode=ro`) al database per aggregati (nessun titolo, nessun testo, nessun dato personale); lunghezze dei prompt di sistema con gli interessi veri, senza stampare il testo; 1 richiesta all'API pubblica di arXiv (200 risultati, categoria generica) per le lunghezze di titolo e abstract; modello e tabelle calcolati con script in Python senza chiamate a LLM o a siti. Scritti due volte (12 e 13 novembre); gli script e i file temporanei sono andati persi con il riavvio del 13 novembre e non sono conservati: questo documento è l'unica traccia, e la sezione 2.3 basta per rifare i conti.
- **Che cosa non si è fatto**: nessuna chiamata a `claude` né a `gradiens esegui`; nessuna richiesta a siti web (solo 1 richiesta all'API di arXiv); nessuna installazione; `.env` non letto; nessun file del progetto modificato tranne questo documento.
- **Limiti**: il modello ha 8 osservazioni (2 esecuzioni × 4 grandezze) e 4 parametri liberi; la lunghezza degli articoli dei siti, il ragionamento per valutazione e il ragionamento nei lotti sono ricavati o ipotizzati, non misurati; i campi `thinking_tokens`, `thinkingTokens`, `costBasis` e `rate_limit_event` non sono più verificabili; i contenuti dei siti e i video non sono salvati; YouTube non ha dati (0 video valutati); le chiamate 4 e 5 (proposte) non sono mai partite; tutto il ramo Windows è solo letto; non si sa come la quota pesa i token (2.2); il campione di arXiv viene da una categoria generica e può differire dalle categorie seguite (nel database i 19 paper mostrati hanno abstract medi di 1.365 e 1.551 caratteri contro 1.442); il contesto aggiunto da Claude Code (825 token) è sconosciuto; l'effetto dell'effort basso è una sola prova; nessuna variabilità misurata.
