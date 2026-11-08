# Struttura delle cartelle e ruoli

Ogni cartella ha un solo proprietario: chi ha bisogno di un cambiamento in una cartella altrui lo chiede a chi la possiede (CLAUDE.md, "Lavoro in team").

```
gradiens/
├─ pyproject.toml, uv.lock            architetto
├─ .env  (escluso da git)             chiavi API e token
├─ .gradiens/  (escluso da git)       database, configurazione, cache, log (PER-02)
├─ src/gradiens/
│  ├─ app/          avvio unico, CLI, avvio_sistema.py        backend-engineer
│  ├─ dati/         modelli SQLAlchemy e migrazioni Alembic    backend-engineer
│  ├─ esecuzione/   orchestrazione, filtro, argomenti, duplicati,
│  │                metriche, pulizia, programmazione          backend-engineer
│  ├─ llm/          interfaccia (base.py), claude_code.py,
│  │                finto.py per i test, compatibile_openai    backend-engineer
│  ├─ fonti/
│  │  ├─ youtube/, arxiv/                                       backend-engineer
│  │  └─ siti/      profilo, strategie di scoperta ed
│  │                estrazione intercambiabili                  scraping-engineer
│  ├─ telegram/     bot e comandi                              backend-engineer
│  └─ dashboard/    comune.py, rotte.py, rotte_impostazioni.py,
│                   template Jinja2, CSS, htmx                 frontend-engineer
├─ tests/
│  ├─ <stessa struttura di src/gradiens>   test di unità di chi possiede la cartella
│  └─ accettazione/                        criteri ACC-*, siti di esempio   tester
├─ mockup/          preview HTML della fase 3                  frontend-engineer
└─ docs/            requisiti/ (analista-requisiti), adr/ e architettura/ (architetto),
                    test/ (tester)
```

## Regole

- **Nomi in italiano.** Moduli, classi e funzioni usano i termini di [CONTEXT.md](../../CONTEXT.md) (`notizia`, `esecuzione`, `interesse`, `argomento`…), così codice, PRD e dashboard parlano la stessa lingua. Restano in inglese solo i nomi imposti dalle librerie.
- **Confine dashboard / backend.** Il backend espone funzioni Python che restituiscono dati (es. "notizie con questi filtri"). Il frontend possiede tutta `dashboard/`, rotte comprese: con htmx ogni rotta restituisce un pezzo di HTML, quindi rotta e template stanno nelle stesse mani. La dashboard non scrive SQL e non chiama direttamente i provider LLM.
- **Confine fonti / esecuzione.** Ogni fonte (`youtube/`, `arxiv/`, `siti/`) restituisce notizie candidate in un formato comune. La normalizzazione degli indirizzi di un sito sta in `siti/`. Il riconoscimento dei duplicati tra fonti diverse (`DUP-*`) sta in `esecuzione/`.
- **Codice specifico di un sistema operativo** solo in `app/avvio_sistema.py`, con un ramo per Windows ([ADR 0005](../adr/0005-avvio-all-accensione-con-attivita-pianificata.md)) e uno per Linux ([ADR 0007](../adr/0007-avvio-all-accensione-su-linux-con-systemd.md)). Il resto del codice usa `pathlib` e la libreria standard, e i test girano su entrambi i sistemi (`.github/workflows/test.yml`).
- **Copie di sicurezza** (`dati/database.py`): `copia_di_sicurezza` usa l'API di backup di SQLite e scrive in `.gradiens/backup/`. `migra` fa una copia prima di ogni migrazione su un database esistente (tiene le ultime 3), il programmatore una al giorno prima della pulizia delle notizie scadute (tiene le ultime 7).
- **Ricerca** (`notizie.Filtri.testo`, parametro `q`): ogni parola deve comparire nel titolo, nella traduzione, nel riassunto o nella fonte; `LIKE` di SQLite, con il limite delle lettere accentate segnato nel codice.
- **Aggiornamento** (`app/aggiornamento.py`, `gradiens aggiorna` e bottone del pannello): `git fetch`, spegnimento se acceso, `git merge --ff-only`, `uv sync`, riaccensione. Rifiuta se ci sono modifiche locali al codice. `avvio_sistema.eseguibile` trova `git` e `uv` anche in `~/.local/bin`, fuori dal `PATH` del pannello.
- **Pannello di controllo** (`AMB-05`, fetta 8, ADR 0009): `app/pannello.py`, una finestra Tkinter aperta da `gradiens pannello`. Un thread legge `/api/stato` ogni 3 secondi e passa il risultato alla finestra con una coda, perché Tkinter si usa solo nel thread principale; Accendi e Spegni riusano `cli._avvia_staccato` e `cli.richiedi_spegnimento`. Le icone che lo aprono si creano e si tolgono in `app/avvio_sistema.py` (`crea_icone`, `togli_icone`, `icone_presenti`), dalla sezione Avvio o alla fine della configurazione iniziale.
- **Configurazione iniziale** (`UI-11`, fetta 7c): `dashboard/rotte_configurazione.py`. Finché `Impostazioni.configurazione_completata` è falso, `comune.pagina` porta ogni pagina a `/configurazione` e la programmazione non parte. I passi includono i modelli delle sezioni delle Impostazioni: i loro moduli mandano le risposte a `#impostazioni`, che nella procedura è il corpo della pagina, e `rotte_impostazioni.finestra`, quando l'intestazione `HX-Current-URL` indica `/configurazione`, risponde con il passo invece che con la finestra. Così un modulo esiste una volta sola. Claude Code si controlla con `claude auth status` (`llm/claude_code.stato_account`), che è anche il `pronto()` del provider: l'esecutore lo chiama per ogni provider prima di raccogliere, e se fallisce l'esecuzione non parte (`ACC-15`). `claude_code.avviso_login` legge solo la data `refreshTokenExpiresAt` dalle credenziali di Claude Code (mai i token) e, da 3 giorni prima della scadenza, mette un avviso nella Home e in fondo al messaggio Telegram di fine esecuzione.
- **Avvio all'accensione** (`AMB-04`, fetta 7b): la sezione Avvio delle Impostazioni chiama `attiva_avvio`, `disattiva_avvio` e `stato_avvio` di `app/avvio_sistema.py`. Non c'è un campo nel database: lo stato è la registrazione nel sistema operativo, letta di nuovo al massimo ogni 60 secondi perché serve al segnale della sezione in ogni pagina. Su Linux il file del servizio deve coincidere con quello che Gradiens scriverebbe adesso (cartella, Python della `.venv`, percorso di `claude`); su Windows si confrontano programma e cartella dell'attività esportata con `schtasks /Query /XML`. Se non coincidono, la sezione chiede di spegnere e riaccendere l'interruttore. I test non leggono mai la registrazione vera (`tests/conftest.py`).
- **Dati a runtime** solo in `.gradiens/` e `.env`, entrambi esclusi da git (`PER-02`, `PER-03`). In `.env` vanno i segreti e le opzioni di avvio (prefisso `GRADIENS_`, es. `GRADIENS_PORTA`); le impostazioni che si cambiano dalla dashboard stanno nel database.
- **Sicurezza della dashboard**: risponde solo ai nomi host in `GRADIENS_HOST_CONSENTITI` (difesa dal DNS rebinding); le richieste che modificano qualcosa devono avere l'intestazione `HX-Request` (htmx) o `X-Gradiens-Cli` (CLI), che un altro sito non può aggiungere (difesa CSRF); lo spegnimento si accetta solo da `127.0.0.1`.
- **Comandi di sviluppo** con `uv` ([stack](stack.md)): `uv sync` crea l'ambiente `.venv` dentro la repo; `uv run pytest` esegue i test.

## Contratti

Regole fissate nella fetta 1 che le fette successive rispettano senza cambiarle.

**Fonti** (`fonti/__init__.py`). Ogni fonte espone `async def raccogli(client: httpx.AsyncClient, ..., dal: datetime) -> list[Candidata]` e, se il contenuto costa richieste in più, `async def completa(client, candidata) -> Candidata`. L'esecuzione chiama `completa` solo per le notizie che passano pre-filtro e tetto; se il contenuto non esiste, `completa` solleva `ContenutoAssente` con lo stato per il resoconto (es. "trascrizione assente"). Regole:
- `url` è l'indirizzo canonico, sempre `https://`: è la chiave del registro delle notizie viste e diventa un link nella dashboard, quindi la fonte scarta tutto ciò che non è un indirizzo web valido;
- le date sono in UTC senza fuso orario; con la data incerta si usa quella di scoperta e `data_incerta=True` (`WEB-15`);
- `sommario` serve al pre-filtro e viene accorciato a 1.500 caratteri; `contenuto` serve alla valutazione: testo pulito, senza HTML, vuoto finché `completa` non lo riempie;
- `tipo` è uno di `arxiv`, `sito`, `video`, `short`; `stato` contiene stati come "contenuto parziale";
- le richieste usano `fonti.USER_AGENT`, generico e senza dati personali (`WEB-18`).

**Provider LLM** (`llm/base.py`). Un provider ha `nome` e `async def chiedi(*, sistema, messaggio, schema, modello) -> Risposta`:
- `sistema` è la parte fissa dell'esecuzione (va in cache), `messaggio` la parte variabile;
- risponde con un JSON conforme a `schema` (`Risposta.dati`) e con i token usati;
- solleva `QuotaEsaurita` quando la quota è finita (l'esecuzione si interrompe) ed `ErroreLLM` per tutto il resto (la notizia si riprova la volta dopo);
- un nuovo provider si registra in `llm/__init__.py` (`PROVIDER`).

**Esecuzione** (`esecuzione/esecutore.py`). `Esecutore.avvia(avviata_da)` è l'unico modo di far partire un'esecuzione (dashboard, CLI, Telegram, programmazione). Rifiuta la seconda con `GiaInCorso` (`ESE-02`). L'avanzamento sta in `Esecutore.avanzamento`, e lo spegnimento chiama `Esecutore.ferma()`. La risposta dell'LLM è un dato esterno: si accettano solo id di interessi esistenti e punteggi da 0 a 100.

**Programmazione** (`esecuzione/programmatore.py`). `Programmatore.gira()` parte con il servizio e ogni 30 secondi chiama `controlla()`: avvia l'esecuzione quando l'orario delle Impostazioni viene superato tra un controllo e il successivo, oppure, al primo controllo dopo l'avvio, la recupera se l'orario di oggi è passato e da allora non ne è partita nessuna (`ESE-01`). In pausa non avvia niente (`TG-10`). Al primo controllo di ogni giorno cancella le notizie scadute (`ESE-09`), come fa anche l'esecutore all'inizio di ogni esecuzione. Le ore sono quelle del PC, senza fuso; `prossima()` serve a `gradiens stato` e alla Home.

**Metriche e resoconto** (`ESE-11`, `UI-03`). L'esecutore salva in `esecuzioni.metriche` un JSON con la durata totale, i token per ruolo (con provider e modello) e, per tipo di fonte, i contatori, il tempo di raccolta (`raccolta_s`, quello della fonte più lenta del tipo), `stati` (un elemento per sito, canale o arXiv, con le notizie nuove), `problemi` (notizie senza contenuto) e `notizie_escluse` (con il motivo: "a pagamento" o "sponsorizzato o offerta", che il pre-filtro restituisce in `sponsorizzate`). `dati.esecuzioni.riepilogo()` lo legge per Home, resoconto e CLI, con i totali e gli elenchi già uniti.

**Segnali delle Impostazioni** (`dashboard/segnali.py`, `UI-14`). `segnali(s)` ricalcola a ogni richiesta, da database e ultima esecuzione conclusa, i segnali di ogni sezione: tipo (avvertimento o novità, l'avvertimento prevale), motivi e voci da evidenziare dentro la sezione. Li usano la finestra delle Impostazioni e l'ingranaggio della sidebar, che la finestra aggiorna con `hx-swap-oob`.

**Telegram** (`telegram/`, sezione 7 del PRD). `bot.BotGradiens` gira dentro il servizio con il polling, quindi il PC non apre porte: risponde solo alla chat confermata (`TG-02`) e, se Telegram non era raggiungibile (per esempio all'accensione, prima che arrivi la rete), riprova dopo 5, 10, 20 e 40 secondi e poi ogni minuto; anche "Messaggio di prova" prova subito a ricollegarlo. Il servizio lo avvia prima della programmazione, così anche un'esecuzione recuperata che fallisce subito viene segnalata; ogni comando ricevuto finisce nel log. Il messaggio di fine esecuzione parte da `Esecutore.al_termine`, tranne allo spegnimento. `messaggi.py` contiene i testi, in HTML di Telegram con il testo delle fonti escapato. Il token sta nel `.env` (`configurazione.salva_segreto`, `SecretStr`), nome del bot e chat nel database; i log di httpx sono a livello WARNING perché gli indirizzi di Telegram contengono il token.

**Argomenti** (`dati/argomenti.py`, `ESE-08`, `UI-09`, ADR 0008). Dopo la valutazione, `Esecutore._argomenti` manda a Claude a blocchi di 40, uno dopo l'altro, le notizie mostrate dall'esecuzione e gli argomenti aggiornati negli ultimi 30 giorni (al massimo 100); la risposta è un dato esterno e si accettano solo id esistenti o nomi nuovi. Se il passo fallisce le notizie restano senza argomento. Gli argomenti rimasti vuoti si cancellano insieme alle notizie scadute (`ESE-10`).

**Proposte** (`dati/proposte.py`, `INT-04`, `INT-06`). Dopo gli argomenti, `Esecutore._proposte` chiede a Claude un raffinamento per ogni interesse con almeno 3 cuori messi dopo l'ultima proposta su notizie pertinenti (`Notizia.cuore_il`, `Interesse.ultima_proposta_il`), e, se ci sono almeno 3 cuori nuovi su notizie qualsiasi, un interesse nuovo: Claude riceve gli interessi e quelle notizie con i loro punteggi, e propone un interesse solo se rivelano un tema che gli interessi non coprono (decisione 57; le notizie sotto la soglia non si salvano, quindi non hanno mai il cuore). Una proposta alla volta per interesse; si approva, si modifica o si scarta nella sezione Interessi. Approvare cambia solo il raffinamento, mai la descrizione, e vale solo per le notizie nuove (`INT-07`).
