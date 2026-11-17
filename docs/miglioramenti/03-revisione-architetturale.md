# Fase 3: revisione architetturale

**Data**: 13 novembre 2026. **Stato**: chiusa, decisioni 28-35; cosa è fatto e cosa resta in [README.md](README.md).

> **Decisioni dell'utente (14 novembre 2026)**, numeri 28-35 di [decisioni.md](decisioni.md): si fanno i cinque passi di refactoring R-02a, R-01, R-03, R-04, R-02b prima delle modifiche già decise; la 6b-1 **non** si fa per ora (R-01 resta come base degli altri passi); i test T-11…T-14 **non** si anticipano (rischio accettato: R-03 e R-04 spostano rami senza test); `fonti/__init__.py` all'architetto e `tests/conftest.py` al tester; le modifiche che attraversano più proprietari si preparano come passi separati, e i commit li fa solo l'utente; P-1 accettata ([ADR 0012](../adr/0012-llm-del-profilo-del-sito-nel-backend.md)); P-2 accettata (aggiunta all'[ADR 0011](../adr/0011-raccolta-incrementale-dei-siti.md)); `avvio_sistema.py`, bot e servizio restano come sono. P-3 non è stata chiesta e resta una proposta. Il testo sotto è la bozza su cui sono state prese le decisioni e non è stato riscritto: gli sforzi dei test vanno letti senza T-11…T-14.

> **Stato dei passi (17 novembre 2026)**: i cinque passi della decisione 28 sono fatti (commit in [README.md](README.md)), dopo ADR 0010 e 0011 invece che prima; i riferimenti di riga sotto valgono per il commit `3868260`. Differenze dal testo: R-01 aggiunge `Avanzamento.inizia_fase` e T-30 in `tests/dati/test_esecuzioni.py` (senza la parte sul resoconto); R-03 sposta anche `chiedi` e il controllo della forma in `esecuzione/chiamata.py` (scelta dell'utente: il pre-filtro lo usa, e importarlo dall'esecutore darebbe un import circolare), `_foglie` con `_tutti` in `esecuzione/parallelo.py` (`in_parallelo`, `foglie`) e `GIRO_PREFILTRO` con `BLOCCO_PREFILTRO`; il tetto diventa `applica_tetto`, chiamata subito dopo `prefiltra`; R-04 legge la fonte dei siti dentro `raccogli_sito`, come prima. Scritti prima dei passi: T-24, T-30, T-51; non scritti, per la decisione 30: T-12, T-13, T-14.

Revisione dell'architettura di `src/gradiens` (commit `3868260`: 5.568 righe Python senza test né migrazioni, 5.944
con le 376 righe di `dati/migrazioni/`; qui si usa sempre il primo numero) in vista delle modifiche **già decise** (ADR
0010; ADR 0011; decisione 21, cioè la protezione del profilo della 6a-11 B; decisione 19, cioè l'LLM nel profilo della
6a-12, per ultima) e di quelle ancora in **bozza** o rimandate (6b-1, 6b-3, 6b-4, 6b-5, 6b-12, 6a-3, 6a-4, 6a-5, 6a-11
C-E, 7a Modelli LLM, 6c). Le bozze servono a capire dove andrà il codice, non bastano da sole a giustificare un passo. Non modifica nessun file del progetto. Riferimenti `pacchetto/file.py:riga` relativi a
`src/gradiens/`, quelli dei test e dei documenti relativi alla radice. Non ripete la
[mappa dei moduli](../architettura/mappa-moduli.md) né il [documento 02](02-test-e-copertura.md): rimanda alle loro
sezioni. Le stime di sforzo sono stime.

## Riepilogo

**Com'è il codice.** Piccolo e in buona parte sano: 5.568 righe senza le migrazioni, mediana di 6 righe per funzione, 4
funzioni sopra le 40 righe, codice morto quasi assente, codice di sistema solo in `app/avvio_sistema.py` (0 occorrenze
fuori), `dati/` e `fonti/` senza dipendenze uscenti, 182 test verdi. Interfaccia dei provider e strategie dei siti fanno
ciò che CLAUDE.md chiede: non vanno toccate. Per un'app personale con un solo utente non serve nessuna riscrittura.

**Modifiche decise** (decisioni.md): ADR 0010 (pre-filtro arXiv fino al tetto), ADR 0011 (raccolta incrementale dei
siti), decisione 21 (6a-11 B: tenere il profilo vecchio se il sito non risponde), decisione 19 (6a-12: LLM nel profilo,
su richiesta e per ultima). 6b-1, 6b-3, 6b-4, 6b-5, 6a-3, 6a-4, 6a-5 sono ancora **bozze**; 7a e 6c sono rimandate.

**I problemi che pesano di più** stanno dove arrivano le modifiche decise:
1. **L'esecutore concentra 13 compiti** in 466 righe (`_pipeline` 80) e riceverà 8 delle modifiche in arrivo, di cui
   tre decise: ADR 0010, ADR 0011 e la decisione 21 (A-01).
2. **La politica dei siti** (stato, guasti, rigenerazione) sta nell'esecutore, la sequenza "rigenera e salva" è scritta
   due volte, e la fonte siti non rispetta il contratto scritto: ADR 0011 e la decisione 21 la cambiano, e la decisione
   21 tocca tre proprietari (A-02).
3. **ADR 0011 non dice come capire se un sito ha finito**: le candidate non portano il sito; una regola troppo larga fa
   perdere articoli in silenzio, una troppo stretta può bloccare un sito senza fine (A-03).
4. **Metriche e liste di valori ripetute**: un formato permanente scritto in un punto e letto in 6 file, con i nomi dei
   contatori in due copie; lo stato "copertura parziale" di ADR 0011 dovrà essere deciso in più posti (la copia di
   `STATI_BUONI` in `siti.html` se sarà "buono", i 7 letterali di "profilo rigenerato" se sarà "visibile ma non rosso")
   (A-04, A-05).
5. **Claude Code presupposto fuori da `llm/claude_code.py`** in 5 punti (configurazione iniziale, avviso del login,
   fabbrica dei provider, etichette, chiavi): pesa solo quando partirà la 7a (A-06).

**Direzione raccomandata.** Refactoring piccolo e mirato, a passi committabili da soli. **Cinque passi prima delle
modifiche decise**, in quest'ordine: R-02a (vocabolario nel backend), R-01 (metriche e avanzamento), R-03 (pre-filtro,
prima di ADR 0010), R-04 (raccolta, prima di ADR 0011 e della decisione 21), R-02b (`STATI_BUONI` nel modello).
Sforzo stimato: circa 1,5 giorni di refactoring e circa 3 giorni di test, in tutto circa **4,5 giorni**, di cui circa
8,5 ore per test che la decisione 26 colloca "insieme alle modifiche" e qui si anticipano (domanda 3); variante minima
senza R-04 circa 3 giorni (domanda 2). Gli altri passi solo quando si tocca quel codice o con la 7a.
`app/avvio_sistema.py`, il bot, lo stato globale della rete e `app.state` restano come sono. Tre ADR proposti (P-1 LLM
nel profilo, P-2 avanzamento di "coperto fino a" in ADR 0011, P-3 metriche solo per aggiunta) e un quarto con la 7a;
otto domande per l'utente (sezione 6).

| Codice | Dove | Perché pesa | Raccomandazione | Sforzo (stima) | Rischio di regressione |
|---|---|---|---|---|---|
| A-01 | `esecuzione/esecutore.py` (466 righe, 13 compiti) | 8 modifiche in arrivo nello stesso file, 3 decise; **alto** | estrarre metriche, pre-filtro, raccolta (R-01, R-03, R-04, dopo R-02a) | circa 1,5 g più i test | medio |
| A-02 | `esecutore.py:179-242`, `fonti/siti/__init__.py:38-43`, `rotte_impostazioni.py:217-224` | ADR 0011 e decisione 21 sulla stessa politica in due posti; **alto** | esito esplicito della rigenerazione in `fonti/siti` (dentro la decisione 21, tre proprietari), politica in `esecuzione/raccolta.py` (R-04) | 4 h (+ parte della decisione 21) | medio |
| A-03 | `fonti/__init__.py:17-29`, `esecutore.py:267-272` | perdita silenziosa o blocco di un sito con ADR 0011; **alto** | avanzare fino alla candidata più vecchia senza esito (P-2) | 3-4 h dentro ADR 0011 | medio |
| A-04 | `esecutore.py:53-89`, `dati/esecuzioni.py:45-46`, 6 lettori | ADR 0010 e ADR 0011 cambiano un dato permanente, la 6b-1 (bozza) lo estenderebbe; **medio** | `esecuzione/metriche.py` e test dei contatori come sottoinsieme (R-01), P-3 | 2 h | basso |
| A-05 | 1.6 (22 letterali di stato, `siti.html:12`) | lo stato nuovo di ADR 0011; **medio** | una copia dei valori che contano (R-02a, R-02b); T-08 per il resto | 1,5 h | basso |
| A-06 | `rotte_configurazione.py:19`, `rotte.py:47`, `bot.py:164`, `llm/__init__.py:9-12`, `resoconto.html:61` | 7a; **medio**, solo con la 7a | lasciare ora (più 6b-12 B, se accettata); R-10 con la 7a | 0 ora; 3-4 h con la 7a | medio |
| A-07 | decisione 19 contro i confini di `struttura.md` | 6a-12 senza un posto; **medio** | modulo del backend più funzioni pure, tetto controllato prima e dopo la chiamata (P-1) | dentro la 6a-12 | basso |
| A-08 | `esecutore.py:146-147` | invariante della sessione non scritta; **medio** | lasciare e documentare, T-24 | 0,5 h + test | nessuno |
| A-09 | 5 `except QuotaEsaurita: raise` | nuovi punti di chiamata LLM; **basso-medio** | lasciare; correzioni nella fase 4 | 0 | — |
| A-10 | 11 `commit()` e 10 accessi diretti ai modelli fuori da `dati/` | ordine; **basso** | funzioni di `dati/` quando si tocca (R-08) | 2-3 h | basso |
| A-11 | `rotte_impostazioni.py` (344 righe) | 7a, 6a-11 C-E; **basso** | dividere con la 7a (R-09) | 3-4 h | basso |
| A-12 | `telegram/messaggi.py:7` | carica FastAPI nel bot; **basso** | lasciare; R-07 se la 6b-1 estende Telegram | 1 h | basso |
| A-13 | globali di `rete.py`, `app.state` | nessuna modifica lo chiede; **basso** | lasciare così | 0 | — |
| A-14 | `app/avvio_sistema.py` | coeso per ADR 0007; **basso** | lasciare così | 0 | — |
| A-15 | `fonti/__init__.py` e `tests/conftest.py` senza proprietario, `struttura.md` | ADR 0011 cambia il contratto, T-14 sposta fixture; **basso**, ma va risolto prima di R-04 | assegnare, aggiornare, R-06 | 0,5 h + documenti | basso |

## 1. Metodo e misure

Le misure sono state fatte il 13 novembre 2026 con due script usa e getta (in sola lettura, nella cartella temporanea
della sessione, che si svuota al riavvio: non sono conservati). Il metodo è descritto qui sotto in modo da poterle
rifare. La suite è stata rilanciata una volta: **182 test verdi** su Linux
(`PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest -q -p no:cacheprovider`), 176 funzioni di test.

### 1.1 Dimensioni

**Metodo**: `ast.parse` di ogni file di `src/gradiens` tranne `dati/migrazioni/`; per ogni `def` la lunghezza è
`end_lineno - lineno + 1` (docstring compresa, funzioni annidate contate a parte); righe con `wc -l`.

- 409 funzioni; **mediana 6 righe**; 25 funzioni con almeno 25 righe; **4 con almeno 40**.
- Moduli più grandi:

| Modulo | Righe | Funzioni (anche annidate) | Classi |
|---|---|---|---|
| `esecuzione/esecutore.py` | 466 | 24 | 5 |
| `app/avvio_sistema.py` | 372 | 36 | 2 |
| `dashboard/rotte_impostazioni.py` | 344 | 35 | 0 |
| `telegram/bot.py` | 274 | 26 | 2 |
| `dashboard/rotte.py` | 213 | 21 | 0 |
| `app/cli.py`, `fonti/siti/rete.py` | 191 | 10, 13 | 0, 2 |

- Funzioni più lunghe (le prime quattordici):

| Posto | Righe | Dove | Funzione |
|---|---|---|---|
| 1 | 80 | `esecuzione/esecutore.py:244-323` | `_pipeline` |
| 2 | 51 | `fonti/siti/__init__.py:80-130` | `raccogli` |
| 3 | 47 | `dashboard/segnali.py:27-73` | `segnali` |
| 4 | 42 | `app/aggiornamento.py:27-68` | `aggiorna` |
| 5 | 39 | `dati/notizie.py:35-73` | `elenca` |
| 6 | 38 | `app/cli.py:154-191` | `main` |
| 7 | 37 | `esecuzione/esecutore.py:179-215` | `_raccogli` |
| 8 | 36 | `esecuzione/esecutore.py:381-416` | `_prefiltra` |
| 9 | 34 | `app/pannello.py:40-73` | `Pannello.__init__` |
| 10 | 33 | `fonti/siti/rete.py:137-169` | `Navigatore._scarica` |
| 11 | 32 | `fonti/siti/strategie/sitemap.py:86-117` | `_leggi` |
| 12 | 30 | `esecuzione/esecutore.py:325-354` | `_argomenti` |
| 13-14 | 29 | `esecuzione/esecutore.py:291-319`; `telegram/bot.py:106-134` | `elabora` (annidata in `_pipeline`); `BotGradiens.avvia` |

Tre delle dieci funzioni più lunghe sono nell'esecutore (cinque delle prime quattordici).

### 1.2 Responsabilità per modulo

**Metodo**: lettura del codice; un "compito" è una cosa che il modulo decide da solo (non una funzione).

- `esecuzione/esecutore.py`: **13 compiti**. Una esecuzione alla volta (`:119-128`), avanzamento (`:45-50`,
  `:426-427`), metriche (`:53-89`), attesa della rete (`:96-102`, `:169-177`), raccolta da tre fonti con gli argomenti
  di ciascuna (`:179-215`), politica dei siti: stato, guasti, rigenerazione (`:217-242`), registro delle viste e
  doppioni (`:263-266`), pre-filtro (`:381-416`), tetto arXiv (`:277-284`), contenuto e taglio (`:418-424`),
  valutazione e salvataggio di notizie e pertinenze (`:291-319`, `:429-455`), argomenti (`:325-354`), proposte
  (`:356-379`).
- `dashboard/rotte_impostazioni.py`: 8 sezioni (`:29-38`), il tutorial di Telegram con 3 scritture dirette sul
  database (`:254-314`) e il ritorno al passo della configurazione iniziale (`:45-48`).
- `app/avvio_sistema.py`: 5 compiti (avvio staccato, eseguibile di Claude Code, avvio all'accensione, icone, `git` e
  `uv`) per 2 sistemi; 11 occorrenze di `os.name`.
- Gli altri moduli letti per intero hanno al massimo tre o quattro compiti strettamente legati (per esempio
  `fonti/siti/__init__.py`: analisi, rigenerazione, cascata, date incerte; `telegram/bot.py`: tutorial e bot in
  funzione).

### 1.3 Dipendenze tra pacchetti

**Metodo**: `ast.walk` di ogni file; per ogni `from gradiens.X import ...` o `import gradiens.X` verso un pacchetto
diverso si conta **un'istruzione** di import (la mappa A1 conta invece i nomi importati, per questo i suoi numeri
sono più alti); "pigro" = dentro una funzione.

| Da → a | Istruzioni | Da → a | Istruzioni |
|---|---|---|---|
| `dashboard → dati` | 17 | `telegram → dati` | 5 |
| `dashboard → app` | 6 | `esecuzione → dati` | 6 |
| `dashboard → llm` | 3 | `esecuzione → fonti` | 2 |
| `dashboard → telegram` | 3 | `esecuzione → llm` | 2 |
| `dashboard → fonti` | 2 | `telegram → app`, `→ dashboard`, `→ esecuzione`, `→ llm` | 1 ciascuno |
| `dashboard → esecuzione` | 1 | `app → dati` | 2 (+1 pigra) |
| `llm → app` | 1 | `app → dashboard`, `→ telegram` | 1 ciascuno; `app → esecuzione` 2 |

Confermato quanto dice la mappa (A1): `dati` e `fonti` non importano nessun altro pacchetto; nessun ciclo con i soli
import in cima ai file; coppie di pacchetti che dipendono l'una dall'altra: `app ↔ dashboard`, `app ↔ telegram`,
`dashboard ↔ telegram`.

### 1.4 Regole di confine di `struttura.md`, misurate

**Metodo**: ricerca testuale per riga sui file `.py` (fuori da `dati/` dove indicato) e sui modelli Jinja.

| Regola | Misura | Esito |
|---|---|---|
| Codice specifico di un sistema solo in `app/avvio_sistema.py` | `os.name`, `sys.platform`, `windll`, `platform.system` fuori da quel file: **0** | rispettata |
| `dati` e `fonti` foglie | nessun import uscente (1.3) | rispettata |
| "La dashboard non scrive SQL" | `select`/`update`/`delete`/`insert`/`execute` in `dashboard/`: 0; **`commit()` fuori da `dati/`: 11** (dashboard 4, esecutore 7); accessi diretti ai modelli fuori da `dati/`: 10 (letture: dashboard 4, telegram 4, esecutore 1 `select`; creazione: esecutore 1 `add`) | alla lettera sì, nello spirito no (mappa B3 (2)) |
| "La dashboard non chiama i provider LLM" | nessun `chiedi` in `dashboard/`; 2 funzioni di `llm/claude_code.py` chiamate direttamente (`stato_account`, `avviso_login`) | `chiedi` sì; il resto lega la dashboard a Claude Code (A-06) |
| "Ogni fonte restituisce candidate in un formato comune" | `arxiv.raccogli` e `youtube.raccogli` → `list[Candidata]`; `siti.raccogli` → `EsitoSito` (`fonti/siti/__init__.py:38-43`) | non vale per i siti (A-02) |
| Ogni cartella ha un proprietario | `fonti/__init__.py` (il contratto delle fonti, `Candidata`) e `tests/conftest.py` non hanno un proprietario in `struttura.md` | lacuna (A-15) |

### 1.5 Stato condiviso

- `app.state`: **39 righe in 5 file** (ricerca di `app\.state\.\w+`, contando le righe). Servizio 20; rotte delle
  Impostazioni 10 (`bot` 6, `conf` 4); `rotte.py` 6 (`esecutore` 5, `programmatore` 1); `comune.py` 2;
  `rotte_configurazione.py` 1. Gli oggetti sono 7: `sessioni`, `esecutore`, `programmatore`, `conf`, `bot`,
  `avviato_alle`, `server`.
- Variabili globali di modulo mutabili: **5** (`fonti/siti/rete.py:31-33` tre dizionari; `app/avvio_sistema.py:66`
  `_cache`; `fonti/youtube/__init__.py:40` `_limiti`), più l'oggetto `Configurazione` unico per processo
  (`app/configurazione.py:58-60`, `lru_cache`) che `salva_segreto` modifica con `setattr` (`:55`).
- Sessione SQLAlchemy unica per tutta l'esecuzione, condivisa dalle coroutine in parallelo
  (`esecuzione/esecutore.py:146-147`; regge per l'invariante descritta in mappa B4 (b)).

### 1.6 Duplicazioni

**Metodo**: ricerca testuale dei letterali e dei costrutti ripetuti; ogni voce è stata riletta nel contesto.

| Che cosa | Dove | Copie |
|---|---|---|
| Mappa tipo di notizia → fonte | `esecuzione/esecutore.py:35` `FONTE_DI_TIPO`, `dati/notizie.py:12` `GRUPPI_EVIDENZA` (identiche) | 2 |
| Nomi e icone delle tre fonti | `dashboard/comune.py:37` `FONTI`, `app/cli.py:107` `nomi`, `telegram/messaggi.py:12` `ICONE`, `dati/notizie.py:81` (dizionario dei gruppi), `dashboard/rotte_impostazioni.py:31-33` (`SEZIONI`) | 5 |
| Tipi di notizia | `dati/modelli.py:12` `TIPI_NOTIZIA`, `dashboard/comune.py:36` `TIPI` | 2 |
| Stati di un sito che non sono problemi | `dati/esecuzioni.py:44` `STATI_BUONI` (importato da 4 moduli e reso globale Jinja in `dashboard/comune.py:105`), copiato a mano in `dashboard/templates/impostazioni/siti.html:12` | 2 |
| Stato "profilo rigenerato" (trattato a parte) | `dati/siti.py:59`, `esecuzione/esecutore.py:240`, `dashboard/segnali.py:61`, `:65`, `templates/impostazioni/siti.html:15`, `:31`, `templates/resoconto.html:78` | 7 letterali |
| Stati di un'esecuzione | 18 letterali in 8 file Python (`dati/modelli.py:13` `STATI_ESECUZIONE` non è usata da nessuno) e 4 modelli Jinja (`home.html:34`, `notizie.html:14`, `resoconto.html:26`, `stato_esecuzione.html:3`) | 22 |
| Motivo "Gradiens è stato spento durante l'esecuzione." | `esecuzione/esecutore.py:38` `SPENTO`, `dati/esecuzioni.py:33` | 2 |
| Ruoli LLM `"prefiltro"`, `"elaborazione"` | 8 letterali su 7 righe di `esecuzione/esecutore.py` (`:76` ne ha due, `:257-258`, `:318`, `:342`, `:378`, `:400`), più `templates/resoconto.html:61` | 9 |
| Lettura del profilo di un sito (`Profilo.da_dict(json.loads(...))`) | `esecuzione/esecutore.py:221`, `dashboard/rotte_impostazioni.py:69`, `:162`, `:223`; `dashboard/segnali.py:66` legge il JSON a mano | 5 |
| Rigenerazione e salvataggio del profilo | `esecuzione/esecutore.py:233-241` (automatica), `dashboard/rotte_impostazioni.py:217-224` (bottone) | 2 |
| "Ultima esecuzione conclusa" | `dashboard/segnali.py:52`, `telegram/bot.py:210` (`storico(s, 2)` e filtro su `in_corso`) | 2 |
| Inversione del cuore (lettura e `imposta_cuore(not ...)`) | `dashboard/rotte.py:182-185`, `telegram/bot.py:252-255` | 2 |
| `except QuotaEsaurita: raise` prima di un `except` più largo | `esecuzione/esecutore.py:302`, `:337`, `:372`, `:391`; `llm/claude_code.py:79` | 5 |
| Lettori delle chiavi di `esecuzioni.metriche` | scrittore unico `esecuzione/esecutore.py:157-161`; lettori: `dati/esecuzioni.py:53-69`, `app/cli.py:100-121`, `telegram/messaggi.py:38-41`, `:63`, `dashboard/segnali.py:52-57`, `templates/resoconto.html` (circa 20 chiavi), `templates/home.html` (circa 10); `app/servizio.py:76` inoltra il JSON alla CLI senza leggerne le chiavi | 1 scrittore, 6 file lettori |

### 1.7 Codice morto

**Metodo**: per ogni nome definito al primo livello o come metodo in `src/gradiens`, conteggio delle occorrenze
come parola intera in `src`, `tests` e nei modelli Jinja; candidato se citato solo nella sua definizione. Le funzioni
delle rotte (registrate da un decoratore) sono state escluse a mano.

- Mai citati: `STATI_ESECUZIONE` (`dati/modelli.py:13`) e `Profilo.aggiungi_sezione` (`fonti/siti/profilo.py:72`),
  che servirà alla 6a-11 E (sezioni modificabili).
- Usati solo dai test: `Esecutore.attendi` (`esecuzione/esecutore.py:130`), `Finto` (`llm/finto.py:8`,
  dichiarato in `struttura.md`).
- Nomi "privati" importati da un altro modulo: `_avvia_staccato` (`app/pannello.py:18`); `cli._attendi` e
  `cli._avvia_staccato` usati da `app/aggiornamento.py:113`, `:126-127`.

Il codice morto è praticamente assente.

### 1.8 Che cosa legano i test

**Metodo**: ricerca di `monkeypatch.setattr` e di attributi con il trattino basso in `tests/`.

- **66 `monkeypatch.setattr`** in 10 file. Bersagli che un refactoring può spostare:
  - `esecuzione.esecutore`: `rete_disponibile` (`tests/conftest.py:24`, autouse per tutti i test, e
    `tests/esecuzione/test_esecutore.py:430`, `:435`), `BLOCCO_PREFILTRO` (`:160`), `PAUSA_RETE`, `ATTESA_RETE`
    (`:431`, `:436`);
  - `dashboard.rotte_configurazione.stato_account` (`tests/conftest.py:38`, nella fixture `client_nuovo`, da cui dipende
    `client` e quindi quasi ogni test della dashboard; `tests/dashboard/test_configurazione.py:35`);
  - `dashboard.rotte.claude_code.avviso_login` (`tests/dashboard/test_rotte.py:378`) e
    `telegram.bot.claude_code.avviso_login` (`tests/telegram/test_bot.py:257`);
  - `app.cli._attendi`, `_avvia_staccato`, `richiedi_spegnimento`, `leggi_stato` (`tests/app/test_aggiornamento.py:32-35`);
  - `app.avvio_sistema`: 15 in `tests/app/test_avvio_sistema.py` (`os` in 6 punti, `shutil.which`, `_cache`,
    `_esegui`), 7 in `tests/dashboard/test_rotte.py` (`_cache`, `attiva_avvio`, `disattiva_avvio`, `crea_icone`,
    `togli_icone`), 3 in `tests/dashboard/test_configurazione.py` (`crea_icone`), 1 in `tests/conftest.py:23` (`_cache`).
- Attributi privati usati dai test: `Esecutore._fonti` (`tests/esecuzione/test_esecutore.py:340`); `BotGradiens._app`,
  `_aggiorna`, `_stato`, `_cuore`, `_ultima`… (`tests/telegram/test_bot.py:71-143`, `:223`, `:243`); `rete._robots`,
  `_prossima`, `_cache` (`tests/fonti/siti/conftest.py:16`).
- Import dall'esecutore: `Avanzamento` (`tests/dashboard/test_rotte.py:11`, `tests/app/test_servizio.py:57`).
- Iniezione delle dipendenze dell'esecutore nei test: `fabbrica_provider=` in 7 punti (sempre `lambda nome: ...`),
  fonti finte costruite con 19 chiamate a `raccolta(...)` in `tests/esecuzione/test_esecutore.py` (definita a `:38`),
  con la firma `raccogli(client, categorie, dal)`.
- Fixture che non si vedono da tutti i test: `sito` e `rete_pulita` stanno in `tests/fonti/siti/conftest.py:13`, `:56`;
  T-14 deve spostarle in `tests/conftest.py` (documento 02, "Esito della rilettura"), file che oggi non ha un
  proprietario (A-15).

### 1.9 Punti caldi: quali file toccano le modifiche in arrivo

**Metodo** (stima, tabella non ricontata nella rilettura): per ogni modifica decisa o proposta ho letto i "Passi" della
sua scheda (6a, 6b, ADR 0010 e 0011, nota 7a di `piano-fase-4.md`) e segnato i file che nomina o che il passo deve per
forza toccare.

In grassetto le modifiche **decise** (ADR 0010, ADR 0011, decisione 21 = 6a-11 B, decisione 19 = 6a-12, decisione
18 = voci di altri domini nei feed, decisione 13 = difetto dei video da correggere nella fase 4); le altre sono bozze o
rimandate.

| File | Modifiche che lo toccano | Decise / tutte |
|---|---|---|
| `esecuzione/esecutore.py` | **ADR 0010** (6b-2 passi 1-5), **ADR 0011** (6a-6 passi 2-3), **decisione 21** (rigenerazione automatica, `:233-241`), 6b-1 (passi 2-4), 6b-4 (passo 3), 6b-12 B, 6a-3 (passo 2), 7a (ruoli e fabbrica dei provider) | 3 / 8 |
| `fonti/siti/__init__.py` | **ADR 0011**, **decisione 21** (protezione), **decisione 19** (albero dei link), 6a-3, 6a-5 (ciclo con `SEMPRE`) | 3 / 5 |
| `dashboard/rotte_impostazioni.py` | **decisione 21** (bottone), **decisione 19** (bottone), 6a-11 C, D, E, 7a | 2 / 4 |
| `esecuzione/prompt.py` | **decisione 19**, **decisione 13** (se la correzione passa dal prompt), 6b-4, 6b-5 C | 2 / 4 |
| `dashboard/templates/resoconto.html` | **ADR 0010** (testo del tetto), **ADR 0011** (stato nuovo), 6b-1 (facoltativo), 7a (etichette) | 2 / 4 |
| `llm/claude_code.py` | 6b-1 (`interpreta`), 6b-3, 6b-5, 6b-6 | 0 / 4 |
| `fonti/siti/strategie/*` | **decisione 18** (`feed`), 6a-4, 6a-5, 6a-7, 6a-8, 6a-9, rifiuto delle date future (resto della 6a-2, non deciso) | 1 / 7, su 5 moduli (`feed`, `sitemap`, `wordpress`, `html` e il nuovo `controllo`) |

Le strategie dei siti assorbono sette modifiche in cinque moduli separati; l'esecutore ne assorbe otto nello stesso file,
di cui tre decise.

## 2. I problemi

Proprietari secondo `struttura.md`: `app/`, `dati/`, `esecuzione/`, `llm/`, `fonti/youtube/`, `fonti/arxiv/`,
`telegram/` → backend-engineer; `fonti/siti/` → scraping-engineer; `dashboard/` (rotte e modelli) →
frontend-engineer; `docs/adr/`, `docs/architettura/` → architetto.

### A-01. L'esecutore concentra tredici compiti e otto delle modifiche in arrivo

- **Dove**: `esecuzione/esecutore.py`, 466 righe, 13 compiti (1.2). `_pipeline` (`:244-323`, 80 righe) è la funzione
  più lunga del progetto; dentro c'è la chiusura `elabora` (`:291-319`) che usa 8 variabili esterne (`s`, `client`,
  `imp`, `sistema`, `ids_validi`, `elaborazione`, `m`, `self.avanzamento`). Il tetto arXiv vive in mezzo a
  `_pipeline` (`:277-284`), non in una funzione.
- **Perché è un problema concreto**: otto modifiche toccano questo file (1.9). Tre sono **decise** e ognuna cambia una
  parte diversa: ADR 0010 il pre-filtro e il tetto (`:274-284`, `:381-416`), ADR 0011 la raccolta dei siti e il
  salvataggio a fine esecuzione (`:217-242`, `:156-167`), la decisione 21 la rigenerazione automatica (`:233-241`). La
  bozza 6b-1, se accettata, cambierebbe anche le metriche (`:53-89` e le quattro chiamate a `conta_token`). Nello stesso
  file, con un solo file di test (`tests/esecuzione/test_esecutore.py`, 441 righe, 18 funzioni di test), ogni modifica
  rischia di toccare le altre: per esempio i giri di ADR 0010 spostano `segna_viste` e i commit del pre-filtro, da cui
  dipende la sessione condivisa (A-08). Le stesse righe sono anche il luogo dei sospetti S-02, S-05, S-06, S-07, S-36.
- **Quanto pesa**: alto. È l'unico punto in cui le modifiche decise si sovrappongono.
- **Opzioni**:
  - **A. Lasciare così.** Costo zero. Ogni modifica si fa nel file com'è; i diff si sovrappongono e la revisione è
    più difficile. Nessun rischio di regressione da refactoring; rischio maggiore dentro ogni modifica funzionale.
  - **B. Estrarre, dentro `esecuzione/`, solo le parti su cui arriva una modifica decisa**: pre-filtro e tetto in
    `esecuzione/prefiltro.py` (prima di ADR 0010: è il passo 1 che la scheda 6b-2 propone già), raccolta delle fonti e
    politica dei siti in `esecuzione/raccolta.py` (prima di ADR 0011 e della decisione 21). Tutti e due usano
    `Metriche` e l'avanzamento: perché i moduli nuovi non importino dall'esecutore (che importa loro: ciclo), metriche e
    avanzamento vanno prima in `esecuzione/metriche.py`. La valutazione (`elabora`, `_completa`, `_salva`) si estrae
    solo prima della 6b-4, se verrà accettata. Argomenti e proposte restano dove sono: nessuna modifica in arrivo
    (6b-15 "lasciare così"). L'`Esecutore` resta l'unico ingresso (`avvia`, `ferma`, `avanzamento`) e il contratto di
    `struttura.md` non cambia. Costo stimato: circa 1,5 giorni per le estrazioni, più i test (sezione 4). Rischio
    medio: si spostano `TaskGroup`, commit e gestione della quota; i test che sostituiscono `BLOCCO_PREFILTRO` vanno
    aggiornati (1.8), mentre `rete_disponibile` e l'attesa della rete restano nell'esecutore (R-04). Windows e Linux:
    solo Python puro, nessuna differenza. Più facile dopo: ADR 0010 e ADR 0011 toccano ciascuno un modulo proprio.
  - **C. Riscrivere l'esecuzione come una catena di "passi" con un'interfaccia comune.** Nessuna modifica in arrivo
    chiede passi intercambiabili: è un'astrazione per un bisogno ipotetico, con il rischio di regressione più alto.
    Scartata.
- **Raccomandazione**: B, a passi (R-01, R-03, R-04 nel piano, dopo R-02a), ciascuno subito prima della modifica che lo
  ripaga.
  Il motivo: le due modifiche decise più grandi diventano diff separati in moduli separati, e il passo 1 di 6b-2
  andrebbe fatto comunque.
- **Proprietario**: backend-engineer (`esecuzione/`, `tests/esecuzione/`). L'import di `Avanzamento` in
  `tests/dashboard/test_rotte.py:11` continua a funzionare (l'esecutore importa il nome); se lo si vuole puntare al
  modulo nuovo lo fa il frontend-engineer, in un commit suo (R-01).

### A-02. Il contratto delle fonti non è comune, e la politica dei siti sta nell'esecutore

- **Dove**:
  - `esecuzione/esecutore.py:179-215`: l'esecutore costruisce a mano la chiamata di ogni fonte, con argomenti
    diversi: `raccogli(client, categorie, dal)` per arXiv (`:183`), `raccogli(client, youtube.Canale(...), dal)` per
    YouTube (`:185-186`, con `youtube.Canale` preso dal modulo vero anche quando le fonti sono iniettate), `_raccogli_sito`
    per i siti (`:188`). Scrive lui gli stati "ok" (`:212`) e "non raggiungibile" (`:206`).
  - `esecuzione/esecutore.py:217-242`: legge il JSON del profilo (`:221`), crea un `EsitoSito` con lo stato "errore di
    lettura" (`:226`), registra guasti (`:227`), decide la rigenerazione dopo 3 guasti (`:233`) e scrive lo stato
    "profilo rigenerato" con il suo testo (`:240-241`).
  - `fonti/siti/__init__.py:38-43` e `:80`: la fonte siti restituisce `EsitoSito`, non `list[Candidata]` come dice il
    contratto (`struttura.md`, "Contratti"; `fonti/__init__.py:3-8`).
  - La stessa sequenza "rigenera e salva" è scritta due volte: `esecuzione/esecutore.py:233-241` e
    `dashboard/rotte_impostazioni.py:217-224`; in tutti e due i casi `dati/siti.salva_rigenerato` (`dati/siti.py:55-60`)
    mette lo stato "profilo rigenerato" e azzera i guasti.
- **Perché è un problema concreto**:
  - ADR 0011 (deciso) cambia proprio questa parte: la raccolta di un sito riceve "coperto fino a" e restituisce fin dove
    ha coperto; nasce lo stato "copertura parziale". Con la politica sparsa tra esecutore e fonte, chi implementa deve
    toccare due proprietari nello stesso momento. La bozza 6a-3 (parametro `viste`) cadrebbe nello stesso punto.
  - La decisione 21 ("si tiene il profilo vecchio e si segnala il problema"; la rigenerazione sostituisce il profilo
    solo se trova almeno una strategia che funziona) vale sia per la rigenerazione automatica sia per il bottone: con la
    sequenza scritta due volte, va scritta due volte. Oggi è il sospetto S-34.
  - Una fonte nuova (non pianificata) richiederebbe di modificare `_raccogli` e almeno 5 liste di nomi (A-05).
- **Quanto pesa**: alto per ADR 0011 e la decisione 21; basso per una fonte nuova, che nessuno ha chiesto.
- **Opzioni**:
  - **A. Lasciare così** e correggere `struttura.md` perché dica che i siti restituiscono `EsitoSito`. Costo minimo;
    ADR 0011 e la decisione 21 si fanno con due modifiche parallele (esecutore e bottone), ciascuna da provare.
  - **B. Un posto per ogni politica.**
    1. La decisione di tenere o sostituire il profilo sta in `fonti/siti` (scraping-engineer), in una funzione che
       restituisce un esito esplicito, per esempio "sostituito" oppure "tenuto il vecchio, perché il sito non risponde".
       Non basta restituire il profilo vecchio: `salva_rigenerato` scriverebbe comunque "profilo rigenerato" e
       azzererebbe i guasti, e l'esecutore scriverebbe "il profilo è stato ricreato" (`:240-241`), cioè il contrario
       della decisione 21. Non basta nemmeno un'eccezione: la rotta del bottone (`dashboard/rotte_impostazioni.py:217-224`)
       non ha un `try` e risponderebbe 500. Quindi cambiano anche i due chiamanti: l'esecutore (o `raccolta.py` dopo
       R-04) salva solo se il profilo è sostituito e altrimenti segnala il problema; la rotta mostra il messaggio nella
       finestra. Sono **tre proprietari** (scraping, backend, frontend). Per tenere verde ogni commit: prima la funzione
       nuova accanto a `rigenera`, poi i due chiamanti, uno per commit, poi si toglie la vecchia.
    2. Raccolta e politica dei siti (stato, guasti, rigenerazione automatica, e domani "coperto fino a") escono da
       `Esecutore` in `esecuzione/raccolta.py` (R-04), con firme esplicite. Costo 4 ore, rischio medio (R-04).
       Testabilità migliore: la raccolta si prova senza pre-filtro né valutazione. Rispetta i confini: `fonti/` resta
       una foglia, il database lo tocca solo `esecuzione/` tramite `dati/`.
  - **C. Contratto uniforme per tutte le fonti** (un oggetto per fonte con `raccogli(client, richiesta) -> Esito`, e
    l'esecutore che le scorre senza conoscerle). Cambia la firma delle tre fonti, i loro test e le 19 fonti finte dei
    test dell'esecutore (1.8). Ripaga solo con una fonte nuova, che non è prevista. Scartata per ora; è la strada se un
    giorno arriva una quarta fonte.
- **Raccomandazione**: B. Il motivo: ADR 0011 e la decisione 21 cambiano tutti e due la politica dei siti; con B ogni
  proprietario la cambia nel suo modulo, senza toccare arXiv e YouTube. In più `struttura.md` va corretto (contratto
  dei siti). B.1 è parte dell'implementazione della decisione 21, non un refactoring: cambia un comportamento (S-34).
- **Proprietario**: B.1 scraping-engineer, backend-engineer e frontend-engineer, in quest'ordine; B.2 backend-engineer.

### A-03. ADR 0011 richiede di sapere, a fine esecuzione, se le candidate di un sito hanno avuto un esito

- **Dove**: la candidata non porta il sito da cui viene (`fonti/__init__.py:17-29`: `fonte` è il dominio, non l'id
  del sito). Lo stato per sito si collega alle notizie nuove dal nome della fonte (`esecuzione/esecutore.py:267-272`,
  con il limite scritto nel commento: due siti dello stesso dominio sommano). Le notizie che "si riprovano la volta
  dopo" (blocco di pre-filtro fallito `:393-397`, valutazione o `completa` falliti con un errore diverso da
  `ContenutoAssente` `:312-315`, dirette `:310-311`, interruzione) non lasciano traccia.
- **Perché è un problema concreto**: la scheda 6a-6 chiede di spostare "coperto fino a" solo se le candidate del sito
  hanno avuto un esito; altrimenti le notizie da riprovare escono dalla finestra effettiva e si perdono "senza segnale"
  (rischio scritto nella scheda). L'ADR 0011 dice solo "si salva a fine esecuzione". Senza un modo esplicito di
  collegare candidate e sito, l'implementazione rischia proprio quella perdita silenziosa.
- **Casi da tenere presenti** (dati delle decisioni e del codice):
  - interruzioni ricorrenti per quota: plausibili, perché l'utente non ha messo tetti di notizie per sito (decisione
    12) e tratta anche il "rate limit" come quota esaurita (decisione 27);
  - candidate che non ottengono mai un esito: errore LLM persistente su una notizia (S-36), eccezione in `completa`;
  - candidate con data incerta della strategia HTML: ricevono come data l'ora della raccolta (`strategie/html.py:43`)
    a ogni esecuzione, quindi restano nella finestra finché la pagina le linka (`:109`).
- **Quanto pesa**: alto (perdita di articoli senza segnale, o al contrario un sito che non avanza più), limitato
  all'implementazione di ADR 0011.
- **Opzioni**:
  - **A. Avanzare sempre a fine esecuzione, salvo esecuzione interrotta o fallita.** La più semplice; perde le notizie
    di un blocco o di una valutazione falliti in un'esecuzione che finisce "completata" (oggi errori LLM 0 nelle
    esecuzioni 9 e 10, documento 06b, 6b-12: raro ma possibile); con interruzioni ricorrenti non avanza nessun sito.
  - **B. Avanzare solo se tutte le candidate nuove del sito hanno un esito** (ricavato dal registro delle viste:
    `dati/notizie.py:130-133`). Nessuna perdita, ma **può bloccare**: una sola candidata senza esito ferma tutto il
    sito finché non esce dalla finestra, e una candidata HTML con data incerta può non uscirne mai.
  - **B'. Avanzare fino alla candidata più vecchia rimasta senza esito.** Durante la raccolta l'esecuzione annota per
    ogni sito gli indirizzi nuovi e la loro data; a fine esecuzione "coperto fino a" avanza al minimo tra l'ora della
    raccolta e la data della più vecchia candidata del sito che non è nel registro delle viste. Una candidata bloccata
    trattiene il sito solo fino alla sua data, e al massimo per la durata della finestra di raccolta (poi esce, come
    oggi); quelle con data incerta hanno come data l'ora della raccolta, quindi non trattengono quasi niente.
    L'interruzione non richiede una regola a parte: le candidate non elaborate trattengono il loro sito. Nessun campo
    nuovo nel contratto, nessuna tabella. Costo stimato 3-4 ore dentro ADR 0011.
  - **C. Elenco di candidate in attesa salvato nel database** (proposto dalla stessa scheda 6a-6): a ogni esecuzione si
    riprendono le candidate rimaste senza esito, con un contatore per abbandonarle dopo N tentativi. Il più preciso;
    serve una tabella o una colonna in più nella migrazione di ADR 0011 e del codice per tenerla pulita.
  - **D. Campo nuovo in `Candidata` (per esempio l'id del sito)**: cambia il contratto delle fonti (proprietario
    incerto, A-15) per un'informazione che serve solo all'esecuzione; non risolve da solo il blocco.
- **Raccomandazione**: B', scritta in un ADR che precisa l'ADR 0011 (P-2). Il motivo: non perde le notizie da
  riprovare, il blocco è limitato per costruzione alla finestra di raccolta, e non aggiunge stato al database; C resta
  la strada se le esecuzioni vere mostrano siti trattenuti a lungo. **Rischio medio**: un errore nel calcolo fa perdere
  articoli o rileggere troppo, in silenzio; servono i test che la scheda 6a-6 elenca, più uno per la candidata con
  data incerta e uno per due siti dello stesso dominio.
- **Proprietario**: backend-engineer (`esecuzione/`, `dati/`). Non attraversa altri proprietari.

### A-04. Le metriche salvate non hanno una definizione condivisa tra chi le scrive e chi le legge

- **Dove**: uno scrittore (`esecuzione/esecutore.py:157-161`, con `Contatori` a `:53-70`) e 6 file lettori (1.6). I nomi
  dei contatori sono scritti due volte: nei campi di `Contatori` e nella tupla `CONTATORI` di `dati/esecuzioni.py:45-46`.
  La CLI legge le chiavi a mano (`app/cli.py:108-120`) e va in errore sulle metriche vecchie (S-28). Il modello Jinja
  traduce i ruoli con un `if` (`templates/resoconto.html:61`).
- **Perché è un problema concreto**: ADR 0010 (deciso) cambia il significato di `oltre_tetto` e `scartate_prefiltro`;
  ADR 0011 (deciso) aggiunge lo stato "copertura parziale" negli `stati`. La bozza 6b-1, se accettata, aggiunge chiavi
  (`dettaglio_token`, `chiamate`, `contenuto`, e i campi `prefiltrate` e `promosse` di arXiv, che **non** vanno nei
  totali) e un vincolo su `token` (solo chiavi di ruolo). Le esecuzioni vecchie restano nel database per sempre
  (nessuna funzione le cancella, mappa B1): ogni lettore deve reggere tutti i formati. Chi aggiunge a `Contatori` un
  contatore da sommare e dimentica `CONTATORI` ha totali sbagliati senza errori.
- **Quanto pesa**: medio. Il formato è piccolo, ma è un dato permanente.
- **Opzioni**:
  - **A. Lasciare così** e affidarsi al test T-30 (chiavi delle metriche e chi le legge). Costo: solo il test.
  - **B. Spostare `Avanzamento`, `Contatori`, `Metriche` in `esecuzione/metriche.py`** e fissare in un test che
    `CONTATORI` è un **sottoinsieme** dei campi interi di `Contatori`, con l'elenco scritto dei campi che non si sommano
    (oggi nessuno; con la 6b-1 `prefiltrate` e `promosse`). Un test di uguaglianza fallirebbe al passo 4 della 6b-1 e
    spingerebbe a sommare campi che non vanno sommati. `dati/` resta una foglia (non importa `esecuzione`). Costo 1-2
    ore, rischio basso. Serve comunque come base di R-03 e R-04 (A-01).
  - **C. Spostare la definizione in `dati/`** (per esempio `Contatori` accanto a `riepilogo`): un solo posto anche per
    il lettore, ma `dati/` acquista una dataclass che è logica dell'esecuzione. Funziona; poco più ordinato di B, poco
    più invasivo.
  - Far leggere alla CLI il `riepilogo` invece del JSON grezzo correggerebbe S-28: è una correzione, non un
    refactoring, e va in un commit a parte.
- **Raccomandazione**: B (R-01), più la regola "le metriche cambiano solo per aggiunta" in un ADR (P-3). Il motivo:
  R-03 e R-04 ne hanno bisogno per non creare un ciclo di import; il beneficio sulla 6b-1 c'è solo se la 6b-1 viene
  accettata (domanda 1).
- **Proprietario**: backend-engineer. Il modello `resoconto.html` (frontend) non cambia in questo passo.

### A-05. Liste di valori ripetute a mano

- **Dove**: tabella 1.6 (mappa tipo → fonte 2 copie identiche; nomi delle fonti 5; tipi 2; `STATI_BUONI` copiato nel
  modello `impostazioni/siti.html:12`; "profilo rigenerato" 7 letterali; stati di esecuzione 22 letterali e una
  costante inutilizzata; motivo dello spegnimento 2; ruoli 8).
- **Perché è un problema concreto**: ADR 0011 aggiunge lo stato "copertura parziale", e come mostrarlo non è ancora
  deciso. Se sarà uno stato "buono", il codice lo saprà in 4 punti perché importano `STATI_BUONI`, ma il modello
  `siti.html:12` ha la sua copia e lo mostrerebbe comunque come problema. Se invece dovrà essere visibile ma non rosso,
  come "profilo rigenerato", andranno toccati i 7 letterali di quel caso (in Python e nei modelli), che R-02a e R-02b non unificano.
  In entrambi i casi la decisione è sparsa in più posti: T-08 serve proprio a fissare dove.
  7a aggiunge provider ed eventuali ruoli: `resoconto.html:61` mostra "Elaborazione" per qualunque ruolo diverso da
  `prefiltro` e il nome grezzo per ogni provider diverso da `claude-code`.
- **Quanto pesa**: medio per `STATI_BUONI` e lo stato nuovo di ADR 0011; basso per il resto (sono etichette di
  presentazione, ognuna con il suo contesto).
- **Opzioni**:
  - **A. Lasciare così**, con T-08 come rete di sicurezza.
  - **B. Minimo indispensabile**: il modello `siti.html` usa il globale `STATI_BUONI` che `comune.py:105` già passa
    a Jinja; la mappa tipo → fonte sta una volta sola in `dati/modelli.py` accanto a `TIPI_NOTIZIA` e la usano
    esecutore e `notizie.in_evidenza`; il motivo dello spegnimento sta una volta sola in `dati/esecuzioni.py`;
    `STATI_ESECUZIONE` si cancella. Le etichette di presentazione (dashboard, Telegram, CLI) restano separate. Costo
    circa 1,5 ore in due commit (backend, frontend). Rischio basso.
  - **C. Enumerazioni (`StrEnum`) per stati, tipi e ruoli in tutto il codice.** I valori nel database restano
    stringhe uguali; tocca circa 15 file e i modelli Jinja per un beneficio soprattutto di tipizzazione. Per un'app
    personale non si ripaga.
- **Raccomandazione**: B (R-02a e R-02b), prima di ADR 0011. Il motivo: toglie la copia che uno stato "buono" romperebbe, senza
  introdurre strutture nuove. Per il caso "visibile ma non rosso" basta T-08, che elenca i 7 punti da toccare.
- **Proprietario**: backend-engineer per `dati/` ed `esecuzione/`; frontend-engineer per `siti.html`. Due commit
  separati, nessun file condiviso.

### A-06. Fuori da `llm/claude_code.py` il codice presuppone che il provider sia Claude Code

- **Dove** (risposta alla domanda "che cosa presuppone Claude Code fuori dal suo modulo"):
  1. configurazione iniziale: il passo "claude" (`dashboard/rotte_configurazione.py:21-26`, `:28-33`) chiama
     `stato_account` di Claude Code (`:19`, `:47`), non il `pronto()` del provider configurato; il modello Jinja dice
     "Gradiens usa Claude Code, con il modello Haiku" (`templates/configurazione_passo.html:15-23`);
  2. avviso di scadenza del login: `claude_code.avviso_login()` chiamato dalla Home (`dashboard/rotte.py:22`, `:47`) e
     dal messaggio Telegram (`telegram/bot.py:24`, `:164`) qualunque sia il provider;
  3. fabbrica dei provider: `crea_provider(nome)` riceve solo il nome (`llm/__init__.py:9-12`) e crea un'istanza
     nuova a ogni chiamata: l'esecutore ne crea una per ruolo (`esecuzione/esecutore.py:251-252`), quindi due semafori
     e due `pronto()` anche con lo stesso provider (`:253-254`, 6b-12);
  4. etichette: `templates/resoconto.html:61` traduce solo `claude-code` e solo i due ruoli di oggi;
  5. la chiave di un'API non ha un percorso: `Configurazione` legge il `.env` ma non lo copia nell'ambiente
     (`app/configurazione.py:19-30`, mappa A5 a), e la fabbrica non riceve la configurazione.

  Non sono presupposti di Claude Code (e vanno bene così): il modello passato a ogni chiamata
  (`chiedi(..., modello=)`), la distinzione `QuotaEsaurita`/`ErroreLLM`, i valori predefiniti `claude-code`/`haiku`
  in `dati/modelli.py:31-34`, la ricerca dell'eseguibile in `app/avvio_sistema.py` (regola di ADR 0007). Le opzioni
  della 6b (6b-3 cache a 5 minuti, 6b-5 effort, 6b-6 cartella di lavoro) restano confinate in `_ambiente()` e nel
  `cwd` di `ClaudeCode`, come propongono le schede: non perdono.
- **Perché è un problema concreto**: la 7a (provider API di Claude e compatibile OpenAI, provider e modello per ruolo)
  deve toccare i punti 1-5. La 6b-5 E (effort diverso per ruolo) richiederebbe il ruolo nella fabbrica. Con un
  provider diverso da Claude Code la configurazione iniziale non si completerebbe senza Claude Code installato
  (punto 1), e la Home mostrerebbe un avviso su un login che non serve (punto 2).
- **Quanto pesa**: medio, e solo quando parte la 7a, che è rimandata. Oggi l'unico provider è Claude Code.
- **Opzioni**:
  - **A. Lasciare così ora**, con questo elenco come lista di lavoro della 7a. Costo zero; il lavoro si fa una volta
    sola, quando si saprà come si configurano davvero i provider locali (serve il PC con la GPU).
  - **B. Preparare adesso**: `crea_provider(nome, conf)`, un'istanza per provider distinto, un metodo facoltativo
    `avviso()` nel protocollo, il passo della procedura che chiama `pronto()` dei provider configurati. Costo 3-4 ore,
    tocca backend e frontend e 4 `monkeypatch` dei test (`tests/conftest.py:38`, `tests/dashboard/test_configurazione.py:35`,
    `tests/dashboard/test_rotte.py:378`, `tests/telegram/test_bot.py:257`). Ripaga solo con la 7a.
  - **C. Una libreria di astrazione dei provider** (`litellm`): già scartata da `stack.md` (sostituirebbe
    l'interfaccia richiesta da CLAUDE.md).
- **Raccomandazione**: A, più la sola 6b-12 B (un `pronto()` per provider distinto) se l'utente accetta quella bozza. Il
  passo R-10 del piano apre la 7a quando partirà. Il motivo: nessuna modifica decisa ha bisogno di B, e il vincolo di
  CLAUDE.md (provider intercambiabili) è rispettato dall'interfaccia: i punti 1-5 stanno attorno, non dentro.
- **Proprietario**: backend-engineer (`llm/`, `telegram/`, `esecuzione/`) e frontend-engineer (`dashboard/`).
  Attraversa due proprietari.

### A-07. La 6a-12 (LLM nel profilo del sito) non ha un posto in cui vivere

- **Dove**: la decisione 19 vuole l'LLM "su richiesta" alla creazione o rigenerazione del profilo, tramite
  l'interfaccia dei provider, con un tetto di 10.000 token per sito, mai durante le esecuzioni. Ma `fonti/` è una
  foglia che non importa `llm/` (1.3), e la dashboard non chiama i provider (`struttura.md`, "Confine dashboard /
  backend"). Oggi l'unico codice che chiama `chiedi` è l'esecutore (mappa A2, "Chiamate fuori dall'esecuzione").
- **Perché è un problema concreto**: senza una scelta, la via più breve è chiamare il provider dalla rotta del
  bottone (`dashboard/rotte_impostazioni.py`), cioè rompere un confine; oppure mettere in `fonti/siti` prompt, schema,
  tetto di token e gestione della quota, che oggi stanno tutti nel backend.
- **Quanto pesa**: medio. La modifica è decisa ma è l'ultima della 6a.
- **Opzioni**:
  - **A. Chiamata dalla rotta della dashboard.** Il più corto; viola la regola di `struttura.md` e mette quota ed
    errori LLM nel codice del frontend. Scartata.
  - **B. `fonti/siti` riceve una funzione `chiedi` come parametro.** `fonti/` resta senza import di `llm/`; ma prompt,
    schema, tetto di token e quota finiscono nel codice di scraping.
  - **C. Un modulo del backend per le chiamate LLM fuori dall'esecuzione** (per esempio `esecuzione/aiuto_profilo.py`):
    riceve da `fonti/siti` l'"albero dei link ridotto" (funzione pura dello scraping-engineer), costruisce prompt e
    schema (in `esecuzione/prompt.py`), chiama il provider del ruolo elaborazione e fa convalidare la risposta da
    un'altra funzione pura di `fonti/siti` (solo indirizzi dell'albero e del perimetro). La rotta chiama questo modulo.
    Rispetta tutti i confini; costo pari a B più un modulo piccolo.
  - **Il tetto di 10.000 token**, con qualunque opzione: `Provider.chiedi` non ha un parametro di limite
    (`llm/base.py:29`). Le strade sono due: (a) allargare l'interfaccia con un limite, contro la sezione 3 e per un solo
    chiamante; (b) **controllare prima della chiamata** la dimensione dell'ingresso (l'albero si accorcia finché la stima,
    caratteri divisi per 2,35 come nella 6a-12, sta sotto il tetto meno l'uscita attesa, 500-700 token) e **registrare
    dopo** i token veri di `Risposta`. Con (b) il tetto è una stima, non un limite rigido: l'uscita non si può fermare.
- **Raccomandazione**: C con il tetto (b), deciso con un ADR prima di implementare la 6a-12 (P-1). Il motivo: ogni
  proprietario fa ciò che sa fare (euristiche, provider, interfaccia), i confini di `struttura.md` restano veri e
  l'interfaccia dei provider non cambia.
- **Proprietario**: scraping-engineer (funzioni pure), backend-engineer (modulo e prompt), frontend-engineer
  (bottone). Tre proprietari: serializzare nell'ordine detto.

### A-08. La sessione unica dell'esecuzione regge su un'invariante non scritta

- **Dove**: `esecuzione/esecutore.py:146-147` apre una sessione per tutta l'esecuzione; la usano in parallelo
  `_raccogli_sito` (`:227`), `filtra` (`:407-408`), `elabora` (`:295-296`, `:305-306`, `:319`). Regge perché tra una
  modifica e il suo `commit()` non c'è mai un `await` (verificato nella mappa, B4 (b)). L'unico accenno è nel
  docstring di `_tutti` (`:459`).
- **Perché è un problema concreto**: ADR 0010 (giri) e ADR 0011 (salvataggio a fine esecuzione), entrambi decisi,
  aggiungono codice proprio lì; lo farebbero anche le bozze 6b-4 (salvataggio per lotto) e 6a-3 (`viste` passato alla
  fonte come funzione legata alla sessione). Un `await` messo tra una modifica e il suo commit mescolerebbe in silenzio
  le transazioni di coroutine diverse. Con la 6a-3 la fonte siti farebbe una `SELECT` sulla sessione condivisa dentro
  la sua coroutine: è sicuro solo finché non ci sono oggetti in sospeso (l'`autoflush` li scriverebbe).
- **Quanto pesa**: medio, perché il danno sarebbe silenzioso; oggi nessun caso noto.
- **Opzioni**:
  - **A. Lasciare la sessione unica e scrivere l'invariante** nel docstring del modulo e in `struttura.md`, con T-24
    (avanzamento con valutazioni intrecciate e latenza finta) come rete. Costo 30 minuti più il test.
  - **B. Una sessione breve per ogni unità di lavoro** (`with self._sessioni() as s` intorno a `registra_esito`, a
    ogni blocco di pre-filtro, a ogni salvataggio). L'invariante sparisce; gli oggetti letti all'inizio (interessi,
    impostazioni) restano usabili perché `expire_on_commit=False`. Costo 2-3 ore, rischio medio (cambia dove si
    aprono le connessioni). Non risolve S-08 (attese sul database nel ciclo di eventi).
  - **C. SQLAlchemy asincrono**: per SQLite non porta vantaggi e cambia tutto `dati/`. Scartata.
- **Raccomandazione**: A ora; B solo se uno dei passi futuri ha davvero bisogno di un `await` tra modifica e commit.
  Il motivo: oggi funziona, ed è più semplice da capire di una sessione per unità.
- **Proprietario**: backend-engineer; `struttura.md` è dell'architetto.

### A-09. Ogni chiamata LLM ripete la gestione della quota, e il motivo di un fallimento è opaco

- **Dove**: 5 copie di `except QuotaEsaurita: raise` (1.6), necessarie perché `QuotaEsaurita` è sottoclasse di
  `ErroreLLM` (`llm/base.py:18`) e gli `except` che seguono sono più larghi. `_tutti` (`esecuzione/esecutore.py:458-466`)
  estrae la quota da un gruppo di eccezioni solo se è sola; altrimenti il motivo salvato è il testo dell'
  `ExceptionGroup` (`:153-155`). È la radice comune di S-02, S-04, S-05 e S-07 (documento 02, "Esito della rilettura").
- **Perché è un problema concreto**: ADR 0010 (nuovo ciclo di giri) e la decisione 19 (6a-12, chiamata fuori
  dall'esecuzione), più la bozza 6b-4 (lotti) se accettata, aggiungono punti di chiamata che devono ricordare lo stesso
  schema.
- **Quanto pesa**: basso-medio.
- **Opzioni**: **A. Lasciare così** nei refactoring e correggere la famiglia S-02/S-04/S-05/S-07 nella fase 4, dove si
  decide il comportamento giusto; **B. una funzione unica** che chiama il provider e traduce gli errori (quota
  rilanciata, altri errori restituiti come esito), usata da tutti i passi: cambia il punto in cui si decide che cosa è
  un errore, quindi tocca il comportamento; **C. `QuotaEsaurita` non più sottoclasse di `ErroreLLM`**: gli
  `except Exception` la prenderebbero comunque, quindi non toglie le copie.
- **Raccomandazione**: A. Il motivo: un refactoring non deve cambiare quale errore fa fallire un'esecuzione, e T-05 e
  T-27 fissano il comportamento di oggi; B si valuta insieme alle correzioni della fase 4.
- **Proprietario**: backend-engineer.

### A-10. Letture e scritture dei modelli fuori da `dati/`

- **Dove**: mappa B3 (2) e misura 1.4: 4 `commit()` nella dashboard (`dashboard/rotte_configurazione.py:92`,
  `dashboard/rotte_impostazioni.py:265`, `:294`, `:313`), 4 letture dirette nella dashboard, 4 nel bot; nell'esecutore
  `select(Notizia)` (`:328`) e la creazione di `Notizia` e `Pertinenza` (`:446-454`). L'inversione del cuore è scritta
  due volte (1.6).
- **Perché è un problema concreto**: la 7a aggiungerà altre impostazioni (provider e modello per ruolo) e verrà
  naturale scriverle come quelle di Telegram, direttamente; la bozza 6b-4 riscriverebbe `_salva` (lotti). Nessun bug attuale ne
  dipende (S-13 riguarda il bot, non dove sta il codice).
- **Quanto pesa**: basso.
- **Opzioni**: **A. Lasciare così**; **B. funzioni di `dati/`** (`impostazioni.salva_telegram`,
  `impostazioni.completa_configurazione`, `notizie.inverti_cuore`, `esecuzioni.leggi`, `siti.leggi`, e
  `notizie.salva_valutata` per `_salva`), introdotte quando si tocca quel codice: 2-3 ore in tutto, rischio basso,
  due proprietari per volta; **C. un test di architettura** che fallisce se compare un `commit()` fuori da `dati/` ed
  `esecuzione/`: costa poco ma blocca anche correzioni legittime.
- **Raccomandazione**: B, ma solo quando si tocca quel codice (R-08; `_salva` insieme a R-05). Il motivo: è ordine,
  non un rischio; farlo tutto subito tocca tre proprietari senza un ritorno immediato.
- **Proprietario**: backend-engineer (funzioni in `dati/`), poi frontend-engineer (rotte) e backend (bot): serializzare.

### A-11. `rotte_impostazioni.py` raccoglie otto sezioni e il tutorial, con un ciclo verso la configurazione iniziale

- **Dove**: `dashboard/rotte_impostazioni.py`, 344 righe, 35 funzioni, 8 sezioni (`:29-38`), il tutorial di Telegram
  (`:254-314`). `finestra` importa `rotte_configurazione` dentro la funzione (`:45`) perché l'altro modulo importa
  questo in cima (`dashboard/rotte_configurazione.py:15`); il passo si sceglie da un'intestazione del browser (`:47-48`,
  sospetto S-15).
- **Perché è un problema concreto**: la 7a aggiunge una sezione intera (provider e modello per ruolo, chiave dell'API
  da salvare nel `.env` come il token di Telegram); 6a-11 C, D, E e 6a-12 aggiungono anteprima, differenze, sezioni e
  il bottone dell'LLM alla sezione Siti. Il file passerebbe le 500 righe. Il ciclo invece non blocca nessuna modifica:
  un passo nuovo della procedura (per esempio "Modelli" con la 7a) si aggiunge a `PASSI` come gli altri.
- **Quanto pesa**: basso oggi, medio con la 7a.
- **Opzioni**: **A. Lasciare così**; **B. un file per gruppo di sezioni** (per esempio `impostazioni_siti.py`,
  `impostazioni_telegram.py`, più tardi `impostazioni_modelli.py`) che riusano `finestra` ed `_esegui`: 3-4 ore,
  rischio basso, i `monkeypatch` dei test puntano a moduli di `fonti/`, `app/` e `telegram/` e non cambiano (1.8);
  **C. rompere il ciclo** spostando `PASSI`, `PASSO_DI`, `dalla_procedura` e `passo` in un terzo modulo: il ciclo
  resterebbe tra `passo` e `dati_sezione`, quindi serve a poco.
- **Raccomandazione**: B quando parte la 7a o la parte di dashboard della 6a-11 (R-09); A per il ciclo, che è
  documentato e funziona. S-15 si corregge nella fase 4.
- **Proprietario**: frontend-engineer. Non attraversa altri proprietari.

### A-12. Il modulo dei messaggi Telegram importa la dashboard per quattro funzioni di formattazione

- **Dove**: `telegram/messaggi.py:7` importa `AVVIATA_DA`, `FONTI`, `durata`, `token_brevi` da `dashboard/comune.py`,
  che all'import crea l'ambiente Jinja (`comune.py:22`, `:103-106`) e importa `segnali` e `avvio_sistema`. È l'arco che
  chiude il ciclo tra i pacchetti `dashboard` e `telegram` (mappa A1).
- **Perché è un problema concreto**: limitato. Se 6b-1 porta le voci nuove anche nel messaggio Telegram, servono altre
  funzioni di formattazione e l'accoppiamento cresce. Nessun bug.
- **Quanto pesa**: basso.
- **Opzioni**: **A. Lasciare così**; **B. `dashboard/formato.py`** con le sole funzioni pure (date, durata, migliaia,
  token, etichette), importato da `comune.py` e da `messaggi.py`: niente FastAPI caricato dal bot; il ciclo tra
  pacchetti resta, quello tra moduli pesanti no. 1 ora, due proprietari; **C. copiare le quattro funzioni** in
  `messaggi.py`: toglie il ciclo, aggiunge una duplicazione.
- **Raccomandazione**: A; B solo se 6b-1 estende il messaggio Telegram (R-07).
- **Proprietario**: frontend-engineer (`comune.py`, `formato.py`), backend-engineer (`messaggi.py`). Serializzare.

### A-13. Stato globale di modulo e `app.state`: lasciare così

- **Dove**: 1.5. `fonti/siti/rete.py:31-33` (robots.txt, pause per host, cache), `app/avvio_sistema.py:66`,
  `fonti/youtube/__init__.py:40`; 39 righe che usano `app.state`.
- **Perché sembrerebbe un problema**: globali e contenitori non tipizzati sono un classico punto fragile.
- **Perché qui non lo è**: le pause per host (`_prossima`) **devono** essere condivise da tutti i siti raccolti in
  parallelo e dall'analisi lanciata dalla dashboard, nello stesso processo: un oggetto passato a mano dovrebbe comunque
  essere unico. I test li ripuliscono in un punto (`tests/fonti/siti/conftest.py:16`). La 6a-10 (cache su disco) è un
  archivio separato, non li sostituisce. `app.state` è il modo documentato di FastAPI; gli oggetti sono 7 e il processo
  uno solo (ADR 0003). Per la 6c il punto di estensione esiste già: l'autenticazione è un middleware accanto ai due di
  `app/servizio.py:110-117`, e "rotte pericolose disattivate da remoto" è una dipendenza FastAPI per rotta o per
  router; i router sono già quattro (`/api`, Impostazioni, configurazione, pagine).
- **Quanto pesa**: basso.
- **Opzioni**: **A. Lasciare così**; **B. un oggetto "stato della rete" passato al `Navigatore`**: stessa semantica,
  più parametri, tutti i test di `fonti/siti` da toccare; **C. funzioni di accesso tipizzate per `app.state`** in
  `comune.py`: solo comodità.
- **Raccomandazione**: A. Il motivo: nessuna modifica in arrivo lo richiede e la struttura attuale è la più semplice
  da capire.
- **Proprietario**: scraping-engineer (`rete.py`), frontend e backend per `app.state`.

### A-14. `app/avvio_sistema.py`: due sistemi in un file; lasciare così

- **Dove**: 372 righe, 36 funzioni, 5 compiti, 11 occorrenze di `os.name` (1.2).
- **Perché sembrerebbe un problema**: è il secondo file per dimensioni e mescola Windows e Linux.
- **Perché qui non lo è**: è coeso per la regola che lo definisce (ADR 0005, ADR 0007: "il codice specifico di un
  sistema sta tutto in un modulo"), e la misura dice che la regola regge (0 occorrenze fuori, 1.4). Nessuna modifica in
  arrivo lo tocca (la cartella di lavoro di Claude Code della 6b-6 va in `llm/claude_code.py`). I test sostituiscono
  l'`os` del modulo in 6 punti e altri suoi nomi in 9 (`tests/app/test_avvio_sistema.py`, 1.8): dividerlo in un
  pacchetto `linux.py`/`windows.py` li romperebbe quasi tutti e cambierebbe il testo di due ADR.
- **Quanto pesa**: basso.
- **Opzioni**: **A. Lasciare così**; **B. pacchetto `app/avvio_sistema/` con un modulo per sistema**: 4-6 ore,
  rischio medio, nessun beneficio per le modifiche in arrivo, rami Windows non provabili su questa macchina.
- **Raccomandazione**: A. Conseguenza sul documento 02: T-37, T-38, T-39 ("prima del refactoring di
  `avvio_sistema`") possono passare dal gruppo B al gruppo C (domanda 8).
- **Proprietario**: backend-engineer.

### A-15. Proprietari mancanti, documenti non allineati e nomi privati usati fuori

- **Dove**:
  - `fonti/__init__.py` (il contratto comune: `Candidata`, `ContenutoAssente`, `USER_AGENT`) non ha un proprietario
    in `struttura.md`, che assegna solo `fonti/youtube/`, `fonti/arxiv/` (backend) e `fonti/siti/` (scraping); lo
    stesso vale per `tests/conftest.py`, condiviso da tutti i test.
  - `struttura.md` cita `llm/compatibile_openai`, che non esiste, e dice che ogni fonte restituisce `list[Candidata]`
    (A-02).
  - `app/cli.py` definisce come privati `_avvia_staccato` e `_attendi`, che però usano anche `app/pannello.py:18` e
    `app/aggiornamento.py:113`, `:126-127`.
- **Perché è un problema concreto**: ADR 0011 cambia il contratto delle fonti (lo dice l'ADR stesso), e T-14 richiede
  di spostare le fixture `sito` e `rete_pulita` in `tests/conftest.py` (1.8); senza un proprietario non è chiaro chi
  modifica questi due file, e CLAUDE.md vieta due membri sullo stesso file.
- **Quanto pesa**: basso, ma va risolto prima di R-04 (T-14) e di ADR 0011.
- **Opzioni**: **A. Lasciare così**; **B. assegnare** `fonti/__init__.py` all'architetto (come tutti i contratti di
  `struttura.md`; le modifiche si concordano con backend e scraping) e `tests/conftest.py` al tester; aggiornare
  `struttura.md`; rendere pubblici i due nomi della CLI (R-06, 30 minuti, due `monkeypatch` di
  `tests/app/test_aggiornamento.py:32`, `:34` da aggiornare); **C. assegnare `fonti/__init__.py` al backend-engineer**,
  che è il lettore principale del contratto.
- **Raccomandazione**: B. Il motivo: il contratto delle fonti serve a due proprietari; chi lo arbitra non deve essere
  uno dei due. È una domanda per l'utente (sezione 6).
- **Proprietario**: architetto (`struttura.md`); backend-engineer (R-06).

## 3. Che cosa va bene e non va toccato

- **Dimensioni**: 5.568 righe senza le migrazioni, mediana 6 righe per funzione, 4 funzioni sopra le 40 (1.1). Per un'app personale con
  un solo utente è codice piccolo e leggibile: la revisione non giustifica riscritture.
- **Interfaccia dei provider** (`llm/base.py`): tre membri (`nome`, `pronto`, `chiedi`), il modello passato a ogni
  chiamata, due eccezioni con un significato chiaro, un provider finto per i test. È della misura giusta per il
  vincolo di CLAUDE.md e per la 7a; le opzioni della 6b restano dentro `ClaudeCode`. Non va allargata prima della 7a
  (A-06).
- **Strategie dei siti come moduli intercambiabili** (`fonti/siti/strategie/__init__.py`): sette modifiche della 6a
  cadono in cinque moduli diversi (1.9); la 6a-5 si aggiunge con un modulo nuovo e un attributo facoltativo. Va preservato
  così com'è.
- **`dati/` e `fonti/` come foglie** (1.3): nessuna dipendenza uscente. Ogni spostamento proposto qui le mantiene.
- **Codice di sistema in un solo modulo** (1.4, A-14): la regola regge alla misura.
- **Un processo, un `Esecutore`, `avvia` senza `await` prima della prenotazione** (mappa A5 (b)): il vincolo
  "un'esecuzione alla volta" si controlla in un punto solo. I refactoring proposti non toccano `avvia`.
- **La CLI e il pannello parlano solo HTTP** (mappa B4 (b)): nessun secondo processo apre il database.
- **Funzioni di `dati/` che fanno commit da sole** (un'azione, una transazione): semplice da capire; le eccezioni
  (`segna_viste`, `argomenti.crea`) sono poche e note.
- **Segnali ricalcolati a ogni richiesta** (`dashboard/segnali.py`): niente cache da invalidare.
- **Codice morto quasi assente** (1.7) e nomi italiani coerenti con `CONTEXT.md`.
- **6c**: i punti in cui aggiungere autenticazione e rotte "solo dal PC" esistono già (A-13); non serve prepararli.

## 4. Piano di refactoring incrementale

Regole valide per ogni passo:
- ogni passo è un commit con i test verdi prima e dopo, e chiude con la definizione di "fatto" di CLAUDE.md (test
  verdi, `/ponytail-review`, commit fatto dall'utente);
- **un refactoring non corregge bug**: se un passo incontra un sospetto S-nn lo preserva, il test che lo fissa resta
  verde con il commento "vedi S-nn" (decisione 24) e il passo lo segnala;
- **dove fermarsi**: se per far tornare verde un test esistente serve cambiare un'asserzione (non solo un import o il
  bersaglio di un `monkeypatch`), il passo ha cambiato un comportamento: si ferma e si torna indietro;
- **Windows e Linux**: tutti i passi sono Python puro o modelli Jinja, senza percorsi, processi o codifiche nuove. Si
  verificano con `uv run pytest` su Linux e con la CI su Ubuntu e Windows (`.github/workflows/test.yml`); nessun passo
  richiede una prova manuale sul PC Windows;
- i test di caratterizzazione T-nn sono quelli della sezione 3 del [documento 02](02-test-e-copertura.md); le stime di
  sforzo sono stime;
- **i moduli nuovi non importano mai dall'esecutore**: l'esecutore importa loro, quindi un import nella direzione
  opposta crea un ciclo (nella rilettura `from gradiens.esecuzione.esecutore import _tutti` dentro un modulo importato
  dall'esecutore ha dato `ImportError: cannot import name '_tutti' from partially initialized module`). Per questo
  l'ordine dei passi parte dalle cose che tutti usano (vocabolario, metriche).

### 4.1 Riepilogo dei passi

Gli identificativi restano quelli della prima stesura; R-02 è diviso in due (backend e frontend). L'ordine giusto è
quello delle righe della tabella.

| Ordine | Passo | Che cosa | Dipende da | Prima di | Test che devono esistere | Sforzo (stima) | Rischio | Proprietario |
|---|---|---|---|---|---|---|---|---|
| 1 | **R-02a** | Vocabolario nel backend: `FONTE_DI_TIPO` una volta sola in `dati/modelli.py`, motivo dello spegnimento una volta sola in `dati/esecuzioni.py`, via `STATI_ESECUZIONE` | — | R-01 | asserzione sul motivo in `tests/dati/test_notizie.py:167-171` | 1 h | basso | backend |
| 2 | **R-01** | `Avanzamento` (con il metodo che oggi è `Esecutore._fase`), `Contatori`, `Metriche` in `esecuzione/metriche.py` | R-02a | R-03, R-04, 6b-1 | T-03, T-30 | 2 h | basso | backend (commit facoltativo del frontend per un import nei suoi test) |
| 3 | **R-03** | Pre-filtro e tetto in `esecuzione/prefiltro.py`; `_tutti` con un nome pubblico in `esecuzione/parallelo.py` | R-01 | ADR 0010 | T-02, T-05, T-11, T-24, T-27, parte di T-28 sul pre-filtro | 4-5 h | medio | backend |
| 4 | **R-04** | Raccolta e politica dei siti in `esecuzione/raccolta.py` | R-01; domanda 4 (fixture in `tests/conftest.py`) | ADR 0011, decisione 21 | T-06, T-07, T-12, T-13, T-14 (parte automatica), T-51 (nuovo) | 4 h | medio | backend |
| 5 | **R-02b** | Il modello `impostazioni/siti.html` usa il globale `STATI_BUONI` | — | ADR 0011 | T-08 | 0,5 h | basso | frontend |
| — | R-05 | Valutazione in `esecuzione/valutazione.py`; `_salva` in `dati/notizie.py` | R-01, R-03 (`parallelo.py`) | 6b-4, se accettata | T-04, T-24, T-26, T-28 | 4 h | medio | backend |
| — | R-06 | Nomi pubblici per `cli._avvia_staccato` e `cli._attendi` | — | quando capita | test esistenti di `tests/app/test_aggiornamento.py` | 0,5 h | basso | backend |
| — | R-07 | `dashboard/formato.py` senza FastAPI per i messaggi Telegram | — | solo se la 6b-1 estende il messaggio | T-35 | 1 h | basso | frontend, poi backend |
| — | R-08 | Funzioni di `dati/` per le scritture e letture dirette | — | quando si tocca quel codice | T-31, T-34 | 2-3 h | basso | backend, poi frontend |
| — | R-09 | `rotte_impostazioni.py` diviso per gruppi di sezioni | — | 7a, 6a-11 C-E | T-31 | 3-4 h | basso | frontend |
| — | R-10 | Fabbrica dei provider con la configurazione, un'istanza per provider, avviso e passo della procedura dal provider configurato | — | 7a | T-29, T-24 | 3-4 h | medio | backend, poi frontend |

**Dipendenze**: R-02a → R-01 (`Metriche.di` usa `FONTE_DI_TIPO`, `esecuzione/esecutore.py:85`: `metriche.py` la deve
trovare in `dati/`, non nell'esecutore) → R-03 e R-04 (usano `Metriche` e l'avanzamento). R-03 → ADR 0010. R-04 → ADR
0011 e la decisione 21 (rigenerazione automatica). R-02b → ADR 0011. R-03 e R-04 non dipendono l'uno dall'altro, ma
toccano lo stesso file: si fanno in fila. R-01 → 6b-1 solo se la 6b-1 viene accettata (domanda 1): R-01 serve comunque
come base di R-03 e R-04.

**Sforzo prima delle modifiche già decise** (stime; S circa 1,5 ore, M circa 4 ore, come nel documento 02):
- refactoring R-02a, R-01, R-03, R-04, R-02b: circa 11,5-12,5 ore, cioè circa **1,5 giorni**;
- test oltre a T-01…T-10, che la decisione 26 chiede già prima del primo commit di ADR 0010 e 0011:
  - del gruppo B: T-24 (M), T-27 (S), T-30 (M) e la parte di T-28 sul pre-filtro (circa 2 ore): circa 11,5 ore;
  - del gruppo A, **anticipati** rispetto alla decisione 26, che li colloca "insieme alle modifiche": T-11, T-12, T-13
    (S) e T-14 (M): circa 8,5 ore (si scriverebbero comunque, solo più tardi: domanda 3);
  - nuovi: T-51 (S) e l'asserzione sul motivo di `segna_interrotte` (15 minuti): circa 1,75 ore;
  - strumenti: il provider finto con latenza ed errori programmabili (strumento 3 del documento 02, serve a T-05 e
    T-24) e lo spostamento delle fixture `sito` e `rete_pulita` in `tests/conftest.py` (serve a T-14): circa 2,5-3 ore;
  - in tutto circa 24-25 ore, cioè circa **3 giorni**, di cui circa 16 ore in più rispetto a quanto la decisione 26
    prevedeva comunque.
- **Totale: circa 4,5 giorni.** Variante minima, se ADR 0011 non parte subito dopo ADR 0010: senza R-04 (e quindi senza
  T-12, T-13, T-14, T-51 e lo spostamento delle fixture) circa 8 ore di refactoring e 15 ore di test, circa 3 giorni;
  R-04 si fa poi subito prima di ADR 0011 (domanda 2).

**Possono aspettare**: R-05 (fino alla 6b-4, che è una bozza e dipende dalla misura M3), R-06, R-07, R-08 (quando si
tocca quel codice), R-09 e R-10 (con la 7a, rimandata).

**Test di caratterizzazione: che cosa cambia rispetto al documento 02.**
- Prima dei passi 1-5 servono, oltre a T-01…T-10: T-11, T-12, T-13, T-14 (gruppo A, anticipati), T-24, T-27, T-30 e la
  parte di T-28 sul pre-filtro (gruppo B), e un test nuovo, **T-51** `test_nessuna_fonte_raggiungibile_e_cancellazione_durante_la_raccolta`:
  con tutte le fonti in errore l'esecuzione fallisce con "Nessuna fonte raggiungibile." (`esecuzione/esecutore.py:213-214`);
  una cancellazione durante la raccolta (un `BaseException` che non è `Exception`) si rilancia (`:207-208`). Oggi
  nessun test fissa questi due rami (documento 02, sezione 2.1), e R-04 li sposta. Sforzo S, file
  `tests/esecuzione/test_esecutore.py`.
- T-26, il resto di T-28 e T-04 servono prima di R-05; T-25 quando si tocca il `finally` di `_esegui`; T-29 prima di
  R-10; T-31 prima di R-08 e R-09; T-34 prima di R-08; T-35 prima di R-07.
- T-32, T-33, T-36, T-37, T-38, T-39, T-40 non hanno un refactoring che li richieda (bot, `avvio_sistema` e servizio
  restano come sono: A-13, A-14) e possono passare al gruppo C (domanda 8). Il motivo di `segna_interrotte` non
  richiede T-40: basta un'asserzione nel test che già esiste.

### 4.2 I passi nel dettaglio

**R-02a. Vocabolario nel backend (passo 1).**
- *Che cosa cambia*: `FONTE_DI_TIPO` va in `dati/modelli.py` accanto a `TIPI_NOTIZIA`; la usano
  `esecuzione/esecutore.py` (oggi `:35`) e `dati/notizie.py` (oggi `GRUPPI_EVIDENZA`, identica, `:12`); dopo R-01 anche
  `esecuzione/metriche.py`. Il motivo "Gradiens è stato spento durante l'esecuzione." si definisce una volta in
  `dati/esecuzioni.py` (oggi `:33`) e l'esecutore lo importa (oggi `:38`). `STATI_ESECUZIONE` (`dati/modelli.py:13`) si
  cancella.
- *Che cosa NON cambia*: testi, valori nel database, pagine.
- *Test*: il motivo scritto dall'esecutore allo spegnimento è già fissato in parte da
  `test_spegnimento_durante_l_esecuzione_la_registra_come_interrotta` (`tests/esecuzione/test_esecutore.py:176-198`,
  controlla che contenga "spento"); quello di `segna_interrotte` ha un test che controlla lo stato ma non il motivo
  (`tests/dati/test_notizie.py:167-171`): si aggiunge l'asserzione sul testo intero. Nessun `monkeypatch` coinvolto.
- *Fermarsi se*: un test esistente deve cambiare un'asserzione.

**R-01. Metriche e avanzamento in un modulo proprio (passo 2).**
- *Che cosa cambia*: `Avanzamento`, `Contatori`, `Metriche` (`esecuzione/esecutore.py:45-89`) passano in
  `esecuzione/metriche.py`, che importa `FONTE_DI_TIPO` da `dati/modelli.py`. Il corpo di `Esecutore._fase`
  (`:426-427`) diventa un metodo di `Avanzamento` (per esempio `inizia_fase(fase, totale)`), così pre-filtro e raccolta
  possono cambiare fase ricevendo solo l'avanzamento; `_fase` resta come chiamata di una riga, usata anche da
  `_attendi_rete`. In `tests/dati/test_esecuzioni.py` (nuovo, è il file di T-30) un test fissa che
  `dati.esecuzioni.CONTATORI` è un **sottoinsieme** dei campi interi di `Contatori` e che gli altri campi interi sono
  esattamente quelli di un elenco scritto "da non sommare" (oggi vuoto; con la 6b-1, se accettata, `prefiltrate` e
  `promosse`).
- *Che cosa NON cambia*: il JSON salvato in `esecuzioni.metriche` (stesse chiavi, stesso ordine), `avanzamento` letto da
  dashboard, CLI e Telegram.
- *Test e proprietari*: `from gradiens.esecuzione.esecutore import Avanzamento` in `tests/app/test_servizio.py:57`
  (backend) e `tests/dashboard/test_rotte.py:11` (frontend) continua a funzionare, perché l'esecutore importa il nome.
  Il backend può aggiornare il suo file nello stesso commit; quello della dashboard lo aggiorna, se vuole, il
  frontend-engineer in un commit suo.
- *Sospetti incontrati*: S-28 (la CLI legge le metriche vecchie con chiavi a mano): non si tocca.
- *Fermarsi se*: T-03 o T-30 cambiano un'asserzione.

**R-03. Pre-filtro e tetto in `esecuzione/prefiltro.py` (passo 3).**
- *Che cosa cambia*: `_prefiltra` e `filtra` (`:381-416`) e il tetto (`:277-284`) diventano funzioni del modulo nuovo con
  parametri espliciti: sessione, candidate, provider, sistema, modello, **tetto** (`imp.tetto_arxiv`), metriche,
  avanzamento. `BLOCCO_PREFILTRO` si sposta con loro. `_tutti` (`:458-466`) si sposta in `esecuzione/parallelo.py` con
  un nome pubblico (per esempio `in_parallelo`), importato sia dal pre-filtro sia dall'esecutore (che lo usa ancora per
  la valutazione, `:321`): lasciarlo nell'esecutore e importarlo dal modulo nuovo dà l'`ImportError` detto sopra, e
  contraddirebbe A-15 (nomi privati usati da altri moduli). È il passo 1 della scheda 6b-2 ("una funzione per blocco e
  una che elabora una lista in giri; per ora un solo giro").
- *Che cosa NON cambia*: numero, ordine e contenuto delle chiamate; blocchi lanciati insieme; notizie scartate nel
  registro con un commit per blocco; contatori; semantica della quota; lettura delle risposte (`validi`, `:401-402`).
- *Test da aggiornare*: tutti quelli che sostituiscono `esecutore.BLOCCO_PREFILTRO` devono puntare al modulo nuovo:
  `tests/esecuzione/test_esecutore.py:160` e i nuovi T-02, T-05, T-27 (il documento 02 li costruisce proprio così).
  Il test esistente è al sicuro: rifatto nella rilettura con blocchi da 30, diventa **rosso** (nessuna notizia salvata,
  2 errori); se il nome sparisce dall'esecutore, `monkeypatch.setattr` dà `AttributeError`. Chi **può restare verde per
  la ragione sbagliata è T-05**: con un solo blocco la quota interrompe l'esecuzione e nessuna notizia risulta vista,
  ma la cancellazione dei blocchi fratelli non viene più provata. Per questo T-05 controlla anche quante chiamate sono
  partite.
- *Test da anticipare*: la parte di T-28 sulle risposte di forma inattesa del pre-filtro (`{}`, `pertinenti` `None` o
  stringa: S-05). Senza, una riscrittura di `validi` potrebbe cambiare il comportamento senza che un test lo veda.
- *Sospetti incontrati*: S-01 (la regola sulle sponsorizzate vale per ogni tipo), S-02 (quota insieme a un altro
  errore), S-05: si preservano.
- *Documenti che diventano superati*: ADR 0010 ("La modifica sta tutta nell'esecutore") e scheda 6b-2, passo 3
  ("costante dell'esecutore"): vanno precisati quando si implementa ADR 0010 (4.3).
- *Fermarsi se*: T-05, T-27 o la parte di T-28 sul pre-filtro non esistono ancora (la semantica della quota nel
  `TaskGroup` e la lettura delle risposte sono i punti più delicati).

**R-04. Raccolta delle fonti e politica dei siti in `esecuzione/raccolta.py` (passo 4).**
- *Che cosa cambia*: `_raccogli`, `cronometra` e `_raccogli_sito` (`:179-242`) diventano funzioni del modulo nuovo, che
  importa `Metriche` da `esecuzione/metriche.py` (per questo R-01 viene prima: oggi la raccolta usa `Metriche` a `:179`,
  `:217-218`, `:228`). `_attendi_rete` e `rete_disponibile` **restano** nell'esecutore: li sostituiscono
  `tests/conftest.py:24` (autouse) e `tests/esecuzione/test_esecutore.py:430-436`, e spostarli non serve a nessuna
  modifica.
- *Che cosa NON cambia*: argomenti passati a ogni fonte; stati e testi nel resoconto; commit dello stato del sito al
  momento della raccolta (T-07 lo fissa apposta, perché ADR 0011 salverà "coperto fino a" in un altro momento);
  rigenerazione al terzo guasto; **le fonti si leggono a ogni esecuzione** dall'attributo dell'esecutore, non una volta
  alla costruzione: `tests/esecuzione/test_esecutore.py:340` sostituisce `esecutore._fonti` dopo averlo creato, quindi
  le funzioni nuove ricevono il dizionario delle fonti a ogni chiamata.
- *Test da aggiornare*: nessun `monkeypatch`; le fonti finte (`raccolta(...)`, `SimpleNamespace(raccogli=..., rigenera=...)`)
  restano valide.
- *Prerequisiti*: T-06, T-07, T-12, T-13, la parte automatica di T-14 e T-51. T-14 richiede di spostare le fixture
  `sito` e `rete_pulita` in `tests/conftest.py`, file senza proprietario (A-15): R-04 aspetta la risposta alla domanda 4.
- *Sospetti incontrati*: S-34 (rigenerazione che svuota il profilo) e l'osservazione della mappa C4 "Nessuna fonte
  raggiungibile non scatta per i siti": si preservano (T-51 e T-14 li fissano). La protezione del profilo (decisione 21)
  è una modifica funzionale e si fa dopo (A-02, B.1).
- *Fermarsi se*: T-12, T-13 o T-51 non esistono (errori imprevisti, rigenerazione fallita e rami di `gather` sono mai
  eseguiti o non fissati, documento 02 sezione 2.1).

**R-02b. `STATI_BUONI` nel modello della sezione Siti (passo 5).** `templates/impostazioni/siti.html:12` usa il globale
che `dashboard/comune.py:105` già passa a Jinja. Prima T-08. Nessun comportamento cambia. Non tocca i letterali di
"profilo rigenerato" (A-05).

**R-05. Valutazione in `esecuzione/valutazione.py`** (aspetta la 6b-4).
- *Che cosa cambia*: `elabora` esce da `_pipeline` con parametri espliciti al posto delle 8 variabili catturate;
  `_completa` e `MAX_CONTENUTO` con lei; `_salva` diventa `dati/notizie.salva_valutata(...)` con i campi della notizia
  come argomenti (`dati/` non può importare `Candidata`). Usa `in_parallelo` da `parallelo.py`.
- *Che cosa NON cambia*: una notizia salvata appena valutata; esiti di paywall, contenuto assente, diretta, errore;
  pulizia dei punteggi.
- *Sospetti incontrati*: S-05, S-07, S-27, S-30 (errore di rete in `completa` trattato come contenuto assente), S-36:
  si preservano.
- *Fermarsi se*: T-26 o T-28 non esistono.

**R-06. Nomi pubblici nella CLI.** `_avvia_staccato` → `avvia_staccato`, `_attendi` → `attendi` (`app/cli.py:27`,
`:36`; usi in `app/pannello.py:18`, `app/aggiornamento.py:113`, `:126-127`). Aggiornare
`tests/app/test_aggiornamento.py:32`, `:34`. Nessun comportamento cambia.

**R-07. `dashboard/formato.py`.** Le funzioni pure di `comune.py:42-100` e le etichette `AVVIATA_DA`, `FONTI` passano
nel modulo nuovo (frontend); `comune.py` le registra in Jinja come oggi; poi `telegram/messaggi.py:7` le importa da lì
(backend). Prima T-35. Si fa solo se la 6b-1 porta voci nuove nel messaggio Telegram.

**R-08. Funzioni di `dati/` per gli accessi diretti.** Prima il backend aggiunge le funzioni (A-10, opzione B) con i
loro test in `tests/dati/`; poi un commit per proprietario sostituisce gli accessi diretti. `notizie.inverti_cuore` deve
preservare il 404 della dashboard (`dashboard/rotte.py:183-184`), la risposta "Notizia non più disponibile" del bot
(`telegram/bot.py:252-254`) e S-13. Prima T-31 e T-34.

**R-09. Impostazioni divise per gruppi di sezioni.** Un file per i siti e uno per Telegram, poi quello della sezione
Modelli con la 7a; `finestra`, `_esegui` e `dati_sezione` restano in `rotte_impostazioni.py`. I `monkeypatch` di
`tests/dashboard/test_rotte.py` puntano a `fonti.youtube`, `fonti.siti`, `app.avvio_sistema` e non cambiano; quelli di
`tests/telegram/test_bot.py:175-178` puntano a `telegram.bot` e non cambiano. Prima T-31.

**R-10. Provider pronti per la 7a.** `crea_provider(nome, conf)`; l'esecutore crea un'istanza per provider distinto
(un semaforo e un `pronto()` per provider: è anche la 6b-12 B); `avviso()` facoltativo nel protocollo, chiamato da Home e
Telegram al posto di `claude_code.avviso_login`; il passo della procedura usa il `pronto()` del provider configurato.
Da aggiornare: `fabbrica_provider=lambda nome: ...` in 7 punti dei test (diventa `lambda nome, conf: ...` o si lascia un
valore predefinito) e 4 `monkeypatch`: `tests/conftest.py:38`, `tests/dashboard/test_configurazione.py:35`,
`tests/dashboard/test_rotte.py:378`, `tests/telegram/test_bot.py:257`. Prima T-29 e T-24. Rischio medio: tocca la
configurazione iniziale, che blocca la dashboard finché non è completata.

### 4.3 Dopo i passi

Cosa diventa `esecuzione/esecutore.py` (stime ricontate sulle righe che escono):
- dopo R-02a, R-01, R-03 e R-04: circa **320 righe**; `_pipeline` scende a circa **70** (escono il tetto e le chiamate
  dirette alle fonti, ma `elabora`, `_completa` e `_salva` restano);
- dopo R-05: circa 250 righe e una `_pipeline` di circa 40.

Argomenti e proposte restano nell'esecutore: nessuna modifica in arrivo li tocca.

Documenti da aggiornare quando i passi sono fatti (architetto, dopo le decisioni): `struttura.md` (moduli nuovi di
`esecuzione/`, contratto dei siti, proprietari di `fonti/__init__.py` e `tests/conftest.py`, invariante della sessione,
via `llm/compatibile_openai`); i riferimenti di riga della mappa dei moduli; il documento 02 (gruppi dei test B e C, T-51,
T-28 diviso in due parti); con l'implementazione di ADR 0010, il testo dell'ADR "La modifica sta tutta nell'esecutore" e
il passo 3 della scheda 6b-2 ("costante dell'esecutore"), che dopo R-03 non sono più veri.

## 5. ADR proposti

Diventano ADR "accettato, da implementare" solo se l'utente li approva. Le estrazioni di moduli dentro `esecuzione/`
non hanno un ADR: si invertono facilmente e vanno solo in `struttura.md`.

| Codice | Titolo | Decisione in tre righe | Alternative scartate |
|---|---|---|---|
| **P-1** | L'aiuto dell'LLM al profilo del sito passa da un modulo del backend | Le chiamate LLM fuori dall'esecuzione (oggi solo la 6a-12, decisione 19) stanno in un modulo di `esecuzione/` che usa la fabbrica dei provider con il ruolo di elaborazione; `fonti/siti` fornisce solo funzioni pure (albero dei link ridotto, convalida della risposta); la dashboard chiama il modulo, mai il provider. Il tetto di 10.000 token si applica **prima** della chiamata accorciando l'ingresso (stima in caratteri) e si controlla **dopo** con i token di `Risposta`: l'interfaccia dei provider non cambia, e il tetto resta una stima. | chiamata dalla rotta della dashboard (rompe il confine); funzione `chiedi` passata a `fonti/siti` (prompt, quota e tetto nel codice di scraping); parametro di limite in `Provider.chiedi` (allarga l'interfaccia per un solo chiamante) |
| **P-2** | "Coperto fino a" avanza fino alla candidata più vecchia rimasta senza esito (precisa l'ADR 0011) | Durante l'esecuzione si annotano, per ogni sito, gli indirizzi nuovi e la loro data. A fine esecuzione "coperto fino a" avanza al minimo tra l'ora della raccolta e la data della più vecchia candidata del sito che non è nel registro delle notizie viste. Nessuna regola a parte per le esecuzioni interrotte: le candidate non elaborate trattengono il loro sito, al massimo per la durata della finestra di raccolta. | avanzare sempre salvo interruzione (perde le notizie da riprovare; con interruzioni ricorrenti per quota, decisioni 12 e 27, non avanza nessun sito); avanzare solo se tutte le candidate hanno un esito (una candidata senza esito blocca il sito, e una candidata HTML con data incerta può non uscire mai dalla finestra: `strategie/html.py:43`, `:109`); elenco di candidate in attesa nel database (più preciso, più stato da tenere; resta la strada se le esecuzioni vere mostrano siti trattenuti a lungo); campo nuovo in `Candidata` (cambia il contratto delle fonti) |
| **P-3** | Le metriche salvate cambiano solo per aggiunta | `Contatori` e `Metriche` stanno in un solo modulo (`esecuzione/metriche.py`); una chiave di `esecuzioni.metriche` non si toglie né cambia significato senza un ADR; i lettori usano `.get` per le chiavi nuove; sotto `token` stanno solo i ruoli. I contatori che si sommano nei totali sono quelli di `CONTATORI`; gli altri campi interi sono elencati come "da non sommare" e un test lo verifica. | schema JSON validato a ogni lettura (pesante per un'app personale); migrazione delle metriche vecchie (cambia dati permanenti); test di uguaglianza tra `CONTATORI` e i campi di `Contatori` (fallirebbe con i campi della 6b-1 che non vanno sommati) |
| P-4 (con la 7a) | La fabbrica dei provider riceve la configurazione | `crea_provider(nome, conf)`; un'istanza per provider distinto in un'esecuzione; le chiavi delle API stanno nel `.env` e arrivano dal `Configurazione`, mai da `os.environ`; avvisi e prontezza passano dal provider configurato. | lasciare `crea_provider(nome)` e leggere le chiavi da `os.environ` (il `.env` non ci arriva, mappa A5 (a)); una libreria di astrazione (`litellm`, scartata in `stack.md`) |

Note:
- P-2 precisa un ADR accettato senza cambiarne la sostanza ("si salva a fine esecuzione"). Va deciso prima di scrivere
  il codice di ADR 0011, insieme ai test che la scheda 6a-6 elenca, più uno per la candidata con data incerta e uno per
  due siti dello stesso dominio.
- P-3: ADR 0010 cambia il significato di `oltre_tetto`, ed è già deciso e documentato nell'ADR stesso: P-3 non lo
  blocca, ma chiede che resoconto e CLI lo spieghino. Il "da non sommare" serve alla 6b-1 solo se viene accettata.

## 6. Domande per l'utente

1. **La 6b-1 (metriche dettagliate di token) si farà?** È ancora una bozza (README, tabella 6b). *Consigliata*: sì,
   prima di ADR 0010. *Perché*: costa mezza giornata e zero quota, ed è la misura senza la quale gli effetti di ADR 0010
   e delle altre leve della 6b restano stime. R-01 si fa comunque, come base di R-03 e R-04; con la 6b-1 accettata
   ripaga anche lei e il suo test elenca già `prefiltrate` e `promosse` tra i campi da non sommare.
2. **Quanto refactoring prima delle modifiche già decise?** *Consigliata*: i cinque passi R-02a, R-01, R-03, R-04,
   R-02b, circa 1,5 giorni più circa 3 giorni di test (in tutto circa 4,5 giorni, sezione 4.1), se ADR 0011 e la
   decisione 21 seguono subito ADR 0010; altrimenti la variante minima senza R-04 (circa 3 giorni) e R-04 subito prima
   di ADR 0011. Il resto quando si tocca quel codice. *Perché*: ADR 0010, ADR 0011 e la decisione 21 cadono tutte
   nell'esecutore; R-05…R-10 non hanno una modifica decisa che li aspetti.
3. **Si anticipano T-11, T-12, T-13 e T-14 prima di R-03 e R-04?** La decisione 26 li colloca "insieme alle modifiche".
   *Consigliata*: sì. *Perché*: sono gli stessi test, scritti circa 8,5 ore prima; senza, R-03 e R-04 sposterebbero rami
   mai eseguiti (errori imprevisti, rigenerazione fallita, blocchi misti) senza una rete.
4. **Chi possiede `fonti/__init__.py` e `tests/conftest.py`?** *Consigliata*: l'architetto il primo (è il contratto tra
   backend e scraping), il tester il secondo. *Perché*: ADR 0011 cambia il contratto, T-14 (prerequisito di R-04) deve
   spostare due fixture in `tests/conftest.py`, e CLAUDE.md vieta due membri sullo stesso file.
5. **Accetti spostamenti che attraversano proprietari diversi, fatti in commit separati e in fila?** (R-02a e R-02b,
   R-07, R-08, e la decisione 21, che tocca scraping, backend e frontend: A-02, B.1.) *Consigliata*: sì, sempre prima
   chi crea la funzione e poi chi la usa. *Perché*: nessun file viene toccato da due membri, e ogni commit resta verde.
6. **Dove vive l'LLM del profilo del sito (P-1)?** *Consigliata*: in un modulo del backend, con funzioni pure in
   `fonti/siti` e il tetto di token controllato prima e dopo la chiamata. *Perché*: è l'unica opzione che lascia veri i
   due confini di `struttura.md` senza allargare l'interfaccia dei provider.
7. **Per ADR 0011, "coperto fino a" avanza fino alla candidata più vecchia rimasta senza esito (P-2)?** *Consigliata*:
   sì. *Perché*: non perde le notizie da riprovare, non blocca un sito oltre la finestra di raccolta, e non aggiunge
   tabelle; l'elenco in attesa nel database resta disponibile se servirà.
8. **`app/avvio_sistema.py`, il bot e il servizio restano come sono, e T-32, T-33, T-36…T-40 passano al gruppo C?**
   *Consigliata*: sì. *Perché*: nessuna modifica in arrivo li tocca, e si rimandano 7 test di caratterizzazione (4 di
   sforzo M e 3 di sforzo S: circa 20 ore con le stime del documento 02) che servirebbero solo a un refactoring non
   necessario.

## Che cosa non ho potuto verificare

- **Windows**: nessun passo è stato provato; l'affermazione "nessuna differenza tra Windows e Linux" viene dalla
  lettura (solo Python puro e modelli Jinja) e andrà confermata dalla CI.
- **La tabella dei punti caldi (1.9)** è una stima dai passi scritti nelle schede 6a e 6b e nella nota 7a: le
  implementazioni vere possono toccare altri file.
- **Le dimensioni dopo il refactoring (4.3)** e tutti gli sforzi sono stime, non misure.
- **Letti per intero**: esecutore, programmatore, `prompt.py` (prima parte), `llm/*`, `fonti/__init__.py`,
  `fonti/siti/__init__.py`, `fonti/siti/strategie/__init__.py`, `fonti/arxiv`, YouTube (parti rilevanti),
  `dashboard/comune.py`, `segnali.py`, `rotte.py`, `rotte_configurazione.py`, `rotte_impostazioni.py`,
  `telegram/bot.py`, `messaggi.py`, `app/servizio.py`, `cli.py`, `configurazione.py`, `aggiornamento.py`,
  `avvio_sistema.py`, `pannello.py` (prima parte), `dati/siti.py`, `notizie.py`, `esecuzioni.py`, l'inizio di
  `modelli.py`. **Solo tramite la mappa e ricerche testuali**: le strategie dei siti (tranne le righe di
  `strategie/html.py` citate in A-03), `rete.py`, `pagine.py`, `estrazione.py`, `dati/argomenti.py`, `interessi.py`,
  `proposte.py`, `impostazioni.py`, i modelli Jinja (ricerche mirate).
- **Il conteggio degli import** (1.3) conta le istruzioni, non i nomi: è diverso da quello della mappa A1 per metodo,
  non per errore.
- **I sospetti S-nn** citati vengono dal documento 02: non li ho riprovati. L'`ImportError` di `_tutti` e il test che
  diventa rosso con blocchi da 30 (R-03) sono stati riprodotti nella rilettura, non da me.
- Il perimetro dei file di `.claude/agents/` non è stato aggiornato: questo incarico produce solo questo documento.

**Parti non rilette**: dopo la rilettura del 13 novembre, A-07, A-11, A-13 e i passi R-05…R-10 sono stati controllati
solo a campione; la tabella 1.9 non è stata ricontata; niente è stato provato su Windows.
