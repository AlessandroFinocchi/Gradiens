# Fase 5: dipendenze, avvisi e stile (piano)

Data: 15 novembre 2026. Stato: chiusa, decisioni 44-49; cosa è fatto e cosa resta in [README.md](README.md).

Commit di riferimento `3868260`, Linux (Debian 13), Python 3.14.10, uv 0.13.7. I riferimenti
`pacchetto/file.py:riga` sono relativi a `src/gradiens/`; quelli che iniziano con `tests/` o con il nome di una
libreria (per esempio `uvicorn/config.py`) sono relativi alla repository o a `.venv/lib/python3.14/site-packages/`.
Dati grezzi di partenza: [dati/avvisi-e-versioni-2026-11-15.md](dati/avvisi-e-versioni-2026-11-15.md) (test con gli
avvisi di deprecazione: nessuno; versioni installate). Le misure nuove di questa fase, con il metodo, sono
nell'[appendice A](#appendice-a--misure-metodo-e-dati) (M-1…M-6). Questo documento non cambia codice, test,
configurazione né dipendenze: propone.

## Riepilogo

Le dipendenze Python sono quasi tutte all'ultima versione: su 13 dirette, solo `fastapi` (9 rilasci indietro, tutti
piccoli) e `pydantic-settings` (una correzione) hanno una versione più nuova; uv e `uv_build` sono indietro di una
correzione. I test non danno avvisi di deprecazione. I rischi veri non sono in `pyproject.toml`:

1. **Claude Code** (provider predefinito, ADR 0006) si aggiorna da solo e la sua pagina ufficiale annuncia che
   `--bare` diventerà il predefinito di `-p`: in quel modo Claude Code non usa il login dell'abbonamento. Oggi
   Gradiens non se ne accorgerebbe prima di aver fallito ogni chiamata dell'esecuzione: `pronto()` controlla solo
   `claude auth status`, che non cambia.
2. **`sqlite3` di Python**: Gradiens si appoggia, senza dirlo, alla gestione "legacy" delle transazioni, che la
   documentazione di Python dice che cambierà (SQLAlchemy indica Python 3.16). Con il nuovo valore predefinito il
   `PRAGMA foreign_keys = ON` non ha più effetto (misurato, M-4): cancellazioni a cascata perse in silenzio.
3. **yt-dlp** senza un runtime JavaScript: la stessa libreria dice che è un uso deprecato, ma Gradiens nasconde
   l'avviso (`quiet`, `no_warnings`).

I 115-118 `ResourceWarning` vengono dai **test** (motori SQLAlchemy mai chiusi), non sono un problema dell'app; si
chiudono nelle fixture e nei test che creano un motore (provato chiudendoli tutti: da 115 a 1; chiudendo solo quelli delle fixture ne restano 10, vedi "Esito della rilettura"). Lo stile è già molto coerente: basta fissarlo con il
linter di ruff (circa 15 segnalazioni, stima); il formatter cambierebbe 1.000-2.000 righe (stima) e va rimandato.

| Voce | Stato | Raccomandazione | Rischio | Sforzo |
|---|---|---|---|---|
| Dipendenze Python | 11 dirette su 13 all'ultima versione; `fastapi` 0.162.0 → 0.163.1, `pydantic-settings` 2.16.2 → 2.16.3, `pydantic` (transitiva) 2.14.2 → 2.14.3 (§1) | un aggiornamento di `uv.lock` per gruppo, con la suite su Windows e Linux (§4.3, passo 1) | basso | 1 h |
| Claude Code | installato 2.1.316, ultimo 2.1.325 (13 nov); `--bare` predefinito "in una versione futura" (§4.5) | versione registrata a ogni esecuzione, errore di login che ferma subito l'esecuzione, canale `stable`, prova di fumo dopo ogni cambio di versione | **alto** (nessuna notizia finché non si interviene) | 0,5-1 g |
| `sqlite3` legacy (Python futuro) | `dati/database.py:21-25, 34-49` dipendono dalla modalità legacy (§2.1) | `autocommit` esplicito in `crea_motore`, un test su `PRAGMA foreign_keys`; da unire alla scheda 5 del documento 04 | medio, silenzioso, non imminente | 2-3 h |
| yt-dlp e runtime JavaScript | estrazione senza runtime deprecata; avviso nascosto (§2.2) | prova vera, poi `yt-dlp[default,deno]`; segnale "yt-dlp vecchio" | medio | 0,5 g |
| ResourceWarning | 115-118 nei test, 0 problemi nell'app (§3) | `dispose()` nelle fixture e nel lifespan; poi avvisi come errori, mirati | basso | 2-3 h |
| Politica delle versioni | nessun limite superiore, `uv.lock` fissa tutto | lasciare così; un pacchetto alla volta con `uv lock --upgrade-package`; `uv sync --locked` anche in `aggiorna` (§4) | — | 0,5 h |
| Stile | coerente: 98,6% delle righe entro 120 caratteri, virgolette doppie quasi sempre, import in ordine in 78 file su 83 (§5) | uniformare le poche eccezioni con il linter; il resto così | nessuno | — |
| Linter ruff | assente | sì, subito, come dipendenza di sviluppo; configurazione minima (§6) | basso | 2-3 h |
| Formatter ruff | assente | non ora: dopo i passi di refactoring R-*, una cartella alla volta, con `.git-blame-ignore-revs` (§6) | medio (blame, conflitti) | 1-2 h più rilettura |

## Esito della rilettura (15 novembre 2026)

Rilettura mirata e breve. Tornano: la tabella delle dipendenze, `lxml` e `starlette` importate ma non
dichiarate, le opzioni di yt-dlp, ciò che Gradiens usa di Claude Code, sei conteggi di stile ricontati, la
configurazione di ruff (giudicata a lettura: ruff non è stato eseguito). **Due proposte non reggono come sono
scritte**; dove questa sezione e il testo sotto dicono cose diverse, vale questa sezione.

1. **2.1, opzione B (`autocommit=True` più `BEGIN` nel gancio `begin`) non funziona.** Con `autocommit=True`
   il `commit()` di `sqlite3` non fa niente: nella prova del revisore, dopo `with motore.begin()` la
   connessione è ancora dentro la transazione, un'altra connessione non vede la tabella creata e il `BEGIN`
   successivo fallisce. Non è nemmeno la ricetta della documentazione di SQLAlchemy citata. Strade che
   reggono: aggiungere anche i ganci `commit` e `rollback`; oppure, nell'evento `connect`, attivare
   `autocommit` solo per il tempo del PRAGMA (ricetta "Foreign Key Support" di SQLAlchemy, provata:
   `foreign_keys=1` e cascata funzionante anche con `autocommit=False`). In entrambi i casi va riscritto allo
   stesso modo anche `migra` (`dati/database.py:37`, `:48`). L'opzione A (`autocommit` "legacy" esplicito)
   funziona oggi, ma ha una scadenza se Python toglie davvero la modalità legacy: è un'ipotesi da dichiarare.
   Il cambio del valore predefinito è annunciato per Python 3.16 dal sorgente di SQLAlchemy
   (`sqlalchemy/dialects/sqlite/base.py:155-156`); con Python 3.15.2 il valore è ancora quello di oggi.
   Questo punto va trattato insieme alla scheda 5 del documento 04 (migrazione fallita), che tocca lo stesso
   codice ed è anch'essa da riprogettare.
2. **3.3, opzione A, e 3.4.** La prova "da 115 a 1" chiudeva tutti i motori, non solo quelli delle fixture
   come descrive l'opzione A. Restano fuori i motori creati dentro i test (`tests/dati/test_database.py:26,
   38, 57, 71, 75, 92`; `crea_app` in `tests/app/test_servizio.py:23, 49`): chiudendo solo quelli delle
   fixture restano 10 avvisi, e con i filtri del 3.4 la suite avrebbe 2 test falliti e 3 errori, in test
   diversi da quelli colpevoli. L'opzione A deve chiudere anche quei motori. `filterwarnings` sta in
   `pyproject.toml`, che è dell'architetto (non di tester e backend).
3. **4.1, `uv sync --locked` in `aggiorna`.** La proposta è giusta, ma il messaggio d'errore di
   `app/aggiornamento.py:61-62` va cambiato insieme: oggi dice di lanciare `uv sync`, cioè proprio il comando
   che riscrive `uv.lock`.
4. **2.2, costo di `yt-dlp[default,deno]`.** Non è "un download in più": porta 6 pacchetti che oggi non sono
   in `uv.lock` (brotli, mutagen, pycryptodomex, websockets, yt-dlp-ejs, deno).
5. **Lunghezze delle righe (5 e M-3).** Sono contate in byte, non in caratteri: la riga più lunga di `src` è
   di 153 caratteri (`esecuzione/esecutore.py:241`), non 154; le altre citate sono più corte di 1-4
   caratteri. I totali non cambiano: 85 righe oltre 120 su 5.944 (98,6%).

**Non riletto**: le fonti esterne, tutto ciò che riguarda Windows, il piano 4.3, la misura M-6 sui log.

## 1. Dipendenze: stato

Ultime versioni lette su PyPI il **15 novembre 2026 alle 13:13 UTC** (M-1). "Indietro" conta i rilasci pubblicati
dopo quello installato, dove noti.

### 1.1 Dipendenze dirette

| Libreria | Installata | Vincolo | Ultima (data) | Indietro | Che cosa usa Gradiens |
|---|---|---|---|---|---|
| alembic | 1.20.1 | nessuno | 1.20.1 (22 ott) | — | `command.upgrade`, `Config`, `MigrationContext.configure(...).get_current_revision()`, `ScriptDirectory.from_config(...).get_current_head()` (`dati/database.py:7-10, 32-46`); `context.configure(..., render_as_batch=True)`, `begin_transaction`, `run_migrations` (`dati/migrazioni/env.py:3-11`); `op` e `sa` in 11 migrazioni |
| fastapi | 0.162.0 | nessuno | 0.163.1 (15 nov) | 9 rilasci (0.162.1-0.162.7, 0.163.0, 0.163.1, dal 7 al 15 nov) | `FastAPI(lifespan=..., docs_url=None, ...)` (`app/servizio.py:98`); middleware `http` (`:110`); `APIRouter`, `Request`, `JSONResponse`, `HTMLResponse`, `RedirectResponse`, `HTTPException`; `Form()` e `Query(alias=)` con `Annotated` (`dashboard/rotte*.py`); `Depends` (`dashboard/comune.py:114`); `Jinja2Templates` e `TemplateResponse(request, nome, contesto)` (`dashboard/comune.py:22, 123, 132`, `dashboard/rotte_configurazione.py:67`); `StaticFiles` (`dashboard/rotte.py:210`); `TestClient` (`tests/conftest.py:4`) |
| feedparser | 6.0.14 | `>=6.0.14` | 6.0.14 (30 lug) | — | `feedparser.parse` e i campi `entries`, `published_parsed`, `yt_videoid`, `summary` (`fonti/youtube/__init__.py:90-101`, `fonti/arxiv/__init__.py:28`, `fonti/siti/strategie/feed.py:26`, da un flusso di byte) |
| httpx | 0.28.1 | nessuno | 0.28.1 (6 dic 2024) | — (nessun rilascio da quasi due anni, vedi §2.6) | `AsyncClient(follow_redirects=True)` (`esecuzione/esecutore.py:260`, `dashboard/rotte_impostazioni.py:172, 222`); `httpx.get`/`post` sincroni (`app/cli.py:20, 81, 128, 139`); `HTTPError` (`fonti/siti/rete.py:159`, `app/pannello.py:134`); `MockTransport` nei test (`tests/fonti/test_arxiv.py:54`) |
| jinja2 | 3.1.6 | nessuno | 3.1.6 (5 mar 2025) | — | solo attraverso `Jinja2Templates`: filtri e globali (`dashboard/comune.py:103-106`) e i template di `dashboard/templates/` |
| pydantic-settings | 2.16.2 | nessuno | 2.16.3 (13 nov) | 1 correzione | `BaseSettings`, `SettingsConfigDict(env_prefix, env_file, env_file_encoding, extra)` (`app/configurazione.py:19-30`); `_env_file=None` nei test (`tests/conftest.py:31`); `SecretStr` di pydantic (`app/configurazione.py:11, 30, 55`) |
| python-multipart | 0.0.33 | nessuno | 0.0.33 (31 ott) | — | nessun import: serve a FastAPI per leggere i campi `Form()` |
| python-telegram-bot | 22.8 | `>=22` | 22.8 (12 giu) | — | `Application.builder().token().build()`, `initialize`, `start`, `updater.start_polling(drop_pending_updates, allowed_updates)`, `stop`, `shutdown` (`telegram/bot.py:111-143`); `CommandHandler`, `CallbackQueryHandler(pattern)`, `TypeHandler(group=-1)`, `filters.Chat` (`:112-118`); `Bot(token)` come contesto: `get_me`, `get_updates`, `set_my_commands`, `send_message` (`:55-79`); `ParseMode.HTML`, `LinkPreviewOptions`, `InlineKeyboard*`, `InvalidToken`, `TelegramError` |
| sqlalchemy | 2.1.8 | nessuno | 2.1.8 (4 nov) | — | `create_engine` ed `event.listens_for(motore, "connect")` (`dati/database.py:19-25`); `exec_driver_sql` (`:37, 48`); `sessionmaker(expire_on_commit=False)` (`:53`); `DeclarativeBase`, `Mapped`, `mapped_column`, `relationship`, `ForeignKey(ondelete=...)`, `CheckConstraint` (`dati/modelli.py:8-9`); `select`, `update`, `delete`, `func`, `or_`, `selectinload`; `Session.get_one`; `IntegrityError`, `NoResultFound` |
| trafilatura | 2.3.1 | `>=2.3.1` | 2.3.1 (6 ott) | — | `bare_extraction(testo, url=..., with_metadata=True, include_comments=False, date_extraction_params=DATE)` e i campi `text`, `title`, `description`, `date` del documento restituito (`fonti/siti/estrazione.py:20, 32-36`) |
| uvicorn | 0.54.0 | nessuno | 0.54.0 (25 set) | — | `uvicorn.Server(uvicorn.Config(app, host, port, log_config=None)).run()` (`app/servizio.py:137-140`); `server.should_exit = True` (`:55`); i valori predefiniti di `proxy_headers` e `forwarded_allow_ips` (§2.7) |
| youtube-transcript-api | 1.2.5 | `>=1.2.5` | 1.2.5 (5 nov) | — | `YouTubeTranscriptApi().list(id)`, `find_transcript(LINGUE)`, iterazione, `fetch()` e `.text` dei pezzi; eccezioni `AgeRestricted`, `NoTranscriptFound`, `TranscriptsDisabled`, `VideoUnavailable`, `VideoUnplayable` (`fonti/youtube/__init__.py:20-27, 114-128`) |
| yt-dlp | 2026.10.26 | `>=2026.10.26` | 2026.10.26 (26 ott) | — (20 giorni) | `YoutubeDL(opzioni)` come contesto ed `extract_info(url, download=False, process=False)` con `quiet`, `no_warnings`, `skip_download`, `cachedir=False`, `extract_flat`, `playlist_items="0"` (`fonti/youtube/__init__.py:37, 70-73`); campi `channel_id`, `channel`, `uploader`, `live_status`, `media_type` (`:82, 135-137`, documentati in `yt_dlp/extractor/common.py:392, 417`); `yt_dlp.utils.DownloadError` (`:80`) |
| httpx2 (sviluppo) | 2.16.0 | nessuno | 2.16.0 (21 ott) | — | nessun import diretto: lo sceglie il `TestClient` di Starlette se è installato (`starlette/testclient.py:24-43`) |
| pytest (sviluppo) | 9.2.0 | nessuno | 9.2.0 (27 ott) | — | fixture, `monkeypatch`, `tmp_path`, `parametrize`; `addopts = "-q --import-mode=importlib"` (`pyproject.toml`) |
| uv_build (costruzione) | 0.13.7 | `>=0.13.7,<0.14` | 0.13.8 (12 nov) | 1 correzione, già dentro il vincolo | backend di costruzione del pacchetto (`pyproject.toml`, `[build-system]`) |

### 1.2 Strumenti, file e dipendenze transitive che contano

| Voce | Installata | Ultima (data) | Note e uso |
|---|---|---|---|
| Python | 3.14.10 (`.python-version` = `3.14`; `requires-python = ">=3.14"`) | per l'elenco di uv 0.13.7 (`uv python list --offline`): 3.14.10 è l'ultima 3.14, 3.15.2 l'ultima stabile (già installata da uv su questo PC), 3.16.0a1 in prova | è il `.python-version` a tenere Gradiens su 3.14: `requires-python` non ha limite superiore (§2.1, §4) |
| uv | 0.13.7 | 0.13.8 (12 nov, PyPI) | `uv sync --locked` in CI (`.github/workflows/test.yml`), `uv sync` in `app/aggiornamento.py:60` |
| htmx | 2.0.4 (`dashboard/static/htmx.min.js`, stringa `version:"2.0.4"`, aggiunto il 6 nov, commit `34d0e81`) | non verificata (nessuna pagina letta) | file salvato nella repository (ADR 0003): si aggiorna a mano |
| Claude Code | 2.1.316 (il collegamento `~/.local/bin/claude` punta a `~/.local/share/claude/versions/2.1.316`) | 2.1.325 (13 nov, changelog ufficiale) | almeno 5 versioni pubblicate dopo (2.1.319-2.1.325, dal 6 al 13 nov); che cosa usa Gradiens: §4.5 |
| starlette (da fastapi) | 1.10.0 | 1.10.0 (24 ott) | **importata direttamente**: `TrustedHostMiddleware` (`app/servizio.py:14`), `QueryParams` (`dashboard/rotte.py:12`); FastAPI le ripubblica identiche (`fastapi/middleware/trustedhost.py`, `fastapi/datastructures.py:16`) |
| lxml (da trafilatura) | 6.1.3 | 6.1.3 (2 set) | **importata direttamente** ma non dichiarata in `pyproject.toml`: `lxml.html.document_fromstring`, `etree.XMLParser(resolve_entities=False, no_network=True, ...)`, `etree.fromstring`, `etree.QName` (`fonti/siti/pagine.py:7-21`, `fonti/siti/strategie/sitemap.py:8, 23-52`) |
| htmldate (da trafilatura) | 1.11.0 | 1.11.0 (2 ott) | date degli articoli, attraverso `date_extraction_params` (`fonti/siti/estrazione.py:20`) |
| pydantic (da fastapi e pydantic-settings) | 2.14.2 | 2.14.3 (5 nov) | `SecretStr`, validazione delle form |

Due dipendenze usate direttamente non sono dichiarate (`lxml`, `starlette`). Oggi funziona perché le portano
trafilatura e FastAPI. Proposta: dichiarare `lxml` in `pyproject.toml` (senza vincolo: `uv.lock` non cambia
versione) e importare `TrustedHostMiddleware` e `QueryParams` da `fastapi` invece che da `starlette`. Sforzo: minuti.

## 2. API deprecate o a rischio

Nei test **nessun avviso** di deprecazione (dati grezzi). Ho cercato quindi nel codice gli usi che le fonti ufficiali,
o il codice stesso delle librerie installate, segnano come deprecati o legati a una versione. Nota sul metodo: alcune
librerie usano categorie proprie; per esempio `StarletteDeprecationWarning` deriva da `UserWarning`, non da
`DeprecationWarning` (`starlette/exceptions.py:36`); la misura dei dati grezzi con `-W default` le avrebbe comunque
mostrate, e non ce n'erano.

### 2.1 `sqlite3`: la gestione "legacy" delle transazioni cambierà

- **Dove**: `dati/database.py:21-25` (`PRAGMA foreign_keys = ON` a ogni nuova connessione) e `:34-49` (`migra`:
  `PRAGMA foreign_keys = OFF` "fuori transazione", poi `begin()`); la mappa (B4, punto 2) e il documento 04 (scheda 5)
  spiegano perché oggi funziona: in modalità legacy `sqlite3` apre una transazione solo davanti a
  `INSERT`/`UPDATE`/`DELETE`/`REPLACE`.
- **Fonte**: documentazione di Python 3.14, `sqlite3.connect`
  (https://docs.python.org/3.14/library/sqlite3.html, letta il 15 nov 2026): "*autocommit* currently defaults to
  `LEGACY_TRANSACTION_CONTROL`. The default will change to `False` in a future Python release." SQLAlchemy 2.1.8,
  nel testo della sua documentazione dentro il pacchetto installato (`sqlalchemy/dialects/sqlite/base.py`, sezione
  sulle transazioni di pysqlite): "legacy transaction mode will no longer be the default in a future Python version
  (3.16 as of this writing)".
- **Che cosa succede**: misurato (M-4). Con `autocommit=False` `sqlite3` tiene sempre aperta una transazione e
  `PRAGMA foreign_keys = ON` non ha effetto. In Gradiens le chiavi esterne resterebbero spente **senza errori**:
  niente `ON DELETE CASCADE` e `SET NULL` (`dati/modelli.py:114-115, 139-140, 154`), cioè pertinenze e proposte
  orfane quando si cancellano notizie o interessi (per esempio la pulizia dei 7 giorni, che cancella con un `DELETE`
  diretto e conta sulla cascata del database: `dati/notizie.py:108`). Anche la correzione A della scheda 5 del documento 04 (connessione
  con `isolation_level = None` e `BEGIN` esplicito) smetterebbe di funzionare: con `autocommit=False`
  `isolation_level` non conta più (M-4, terza riga).
- **Quando**: non prima di Python 3.16 secondo SQLAlchemy (oggi 3.16.0a1 è in prova). Gradiens ci arriverebbe solo
  cambiando `.python-version`: `requires-python = ">=3.14"` non lo impedisce. Oggi lo impedirebbe di fatto
  youtube-transcript-api 1.2.5, che dichiara `requires_python = "<3.16,>=3.8"` (M-1): un limite che una sua versione
  futura potrà togliere.
- **Come sostituirla**: rendere esplicita la scelta in `crea_motore`, così non dipende più dalla versione di Python:
  - **A (minima)**: `create_engine(url, connect_args={"autocommit": sqlite3.LEGACY_TRANSACTION_CONTROL})`: congela il
    comportamento di oggi. Una riga.
  - **B (raccomandata, insieme alla scheda 5 del documento 04)**: `connect_args={"autocommit": True}` più un `BEGIN`
    emesso da SQLAlchemy nel gancio `begin`, la ricetta della documentazione di SQLAlchemy per il DDL transazionale
    (stesso file, sezione "Enabling Non-Legacy SQLite Transactional Modes"). Il PRAGMA funziona (M-4, ultima riga)
    e la migrazione diventa atomica (S-18). Cambia il comportamento di tutte le transazioni: va provata con la suite e
    con una copia del database vero.
  - In entrambi i casi un test che legga `PRAGMA foreign_keys` da una sessione del motore e si aspetti 1 (tester), e
    una nota nell'ADR 0004 (architetto).

### 2.2 yt-dlp: YouTube senza runtime JavaScript

- **Dove**: `fonti/youtube/__init__.py:37` (`quiet: True, no_warnings: True`), `:70-73` (`_info`), `:79` e `:134`
  (canali e completamento dei video).
- **Fonte**: il codice di yt-dlp 2026.10.26 (`yt_dlp/extractor/youtube/_video.py`, avviso emesso quando non trova un
  runtime): "No supported JavaScript runtime could be found. Only deno is enabled by default [...] YouTube extraction
  without a JS runtime has been deprecated, and some formats may be missing." La pagina ufficiale
  https://github.com/yt-dlp/yt-dlp/wiki/EJS (modificata il 12 lug 2026, letta il 15 nov 2026): Deno abilitato per
  default (minimo 2.3.0), Node con `--js-runtimes node` (minimo 22.0.0); il componente `yt-dlp-ejs` arriva con
  `pip install -U "yt-dlp[default]"` e la sua versione "MUST match" quella indicata da yt-dlp. Il `METADATA` di
  yt-dlp 2026.10.26 ha gli extra `default` (con `yt-dlp-ejs==0.8.0`) e `deno` (`deno>=2.9.8`, da PyPI).
- **Che cosa succede**: Gradiens dipende da `yt-dlp` senza extra e non passa `js_runtimes`; su questo PC `deno` non
  c'è (`node` sì, in `~/.local/bin`, ma non è abilitato per default). L'avviso di yt-dlp non arriva mai nei log
  perché `no_warnings` lo spegne. Gradiens non scarica video: usa solo `live_status` e `media_type`. **Non ho
  verificato** con una richiesta vera se oggi quei campi arrivano completi senza runtime. La pagina non dà una data
  per la fine del supporto senza runtime.
- **Come sostituirla**: dipendenza `yt-dlp[default,deno]`: uv installa `yt-dlp-ejs` e il binario di Deno come
  pacchetti Python, uguali su Windows e Linux, senza installazioni di sistema. Costo: un download in più (dimensione
  non verificata) e una dipendenza che cambia insieme a yt-dlp. Prima, una prova vera su un canale seguito (da
  chiedere all'utente, §7). Indipendente da questo: un segnale quando yt-dlp è vecchio (§4.4).

### 2.3 Claude Code: `--bare`, campi non documentati, file delle credenziali

Trattato come dipendenza in §4.5. In breve, che cosa è a rischio:

| Che cosa | Dove | Documentato? (pagine lette il 15 nov 2026) |
|---|---|---|
| `-p` con il login dell'abbonamento | `llm/claude_code.py:18-25, 86-92` | sì oggi; la pagina headless avvisa che `--bare` "will become the default for `-p` in a future release" e che in bare Claude Code "never reads OAuth credentials or the system keychain" |
| opzioni `--model`, `--system-prompt`, `--json-schema`, `--output-format json`, `--tools ""`, `--strict-mcp-config`, `--safe-mode`, `--disable-slash-commands`, `--no-session-persistence` | `llm/claude_code.py:18-25, 86-92` | sì, tutte nella CLI reference |
| campi `structured_output`, `result`, `usage` della risposta | `llm/claude_code.py:51-61` | sì (headless: "metadata about the request (session ID, usage, etc.) with the structured output in the `structured_output` field"; il campo manca se la risposta non è valida, e Gradiens lo gestisce a `:56-58`) |
| campi `is_error`, `api_error_status` e i sotto-campi di `usage` (`input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`) | `llm/claude_code.py:51-53, 59-61` | non trovati nelle due pagine lette |
| parole dell'errore di quota (`"usage limit"`, `"rate limit"`, `"limit reached"`, `"quota"`) | `llm/claude_code.py:26, 53` | no: dipende dal testo inglese dei messaggi |
| `claude auth status`: campi `loggedIn` e `subscriptionType` | `llm/claude_code.py:121-129` | **no**: la CLI reference documenta per quel comando il codice di uscita (0 collegato, 1 no), `configDirectory` (dalla 2.1.268) e `authMethod` (`none`, `claude.ai`, `oauth_token`, `api_key`, `api_key_helper`, `third_party`) |
| file `~/.claude/.credentials.json`, campo `claudeAiOauth.refreshTokenExpiresAt` | `llm/claude_code.py:136-138` (`scadenza_login`) | **no**: file interno dello strumento (l'ADR 0006 parla invece di `credential_expires_at` nella risposta: il codice non lo usa) |
| su Windows, l'eseguibile dentro il pacchetto npm (`node_modules/@anthropic-ai/claude-code/bin/claude.exe`) | `app/avvio_sistema.py:38-39` | no: la pagina di installazione dice che il pacchetto npm porta il binario "through a per-platform optional dependency [...] and a postinstall step links it into place"; provato su Windows il 12 nov (`piano-fase-4.md`); `avvio_sistema` resta com'è (decisione 35) |

### 2.4 FastAPI e Starlette

- **Form con booleani** (FastAPI 0.162.0, 23 ott, "Breaking Changes": "FastAPI no longer infers `False` for omitted
  booleans", dalle note di rilascio su GitHub lette il 15 nov 2026). Gradiens è già al sicuro: tutti i campi
  `Annotated[bool, Form()]` hanno `= False` (`dashboard/rotte_impostazioni.py:195, 244-245, 319, 334`,
  `dashboard/rotte_configurazione.py:81`; controllato con `grep`).
- **Lifespan**: Starlette 1.10 deprecava solo i lifespan scritti come generatori (`starlette/routing.py:606-617`);
  Gradiens usa `@asynccontextmanager` (`app/servizio.py:81-91`). A posto.
- **`TemplateResponse`**: Gradiens usa già la firma con `request` per primo (`dashboard/comune.py:123, 132`). A posto.
- **`TestClient` e `httpx2`**: Starlette 1.10 usa `httpx2` se c'è; se manca ripiega su `httpx` con un
  `StarletteDeprecationWarning` (`starlette/testclient.py:24-43`). Se un giorno si togliesse `httpx2` dalle
  dipendenze di sviluppo, i test girerebbero con un avviso. Non usare `timeout=` nelle richieste del `TestClient`
  (deprecato, `starlette/testclient.py:509-515`): oggi nessun test lo fa.
- Gli altri rilasci di FastAPI dopo 0.162.0 (fino a 0.163.1) non hanno voci "Deprecations"; 0.162.6 toglie Python
  3.10, che non riguarda Gradiens.

### 2.5 Le altre librerie: niente di deprecato in uso

| Libreria | Controllo fatto | Esito |
|---|---|---|
| trafilatura 2.3.1 | parametri deprecati in `trafilatura/core.py:616-640`: `no_fallback`, `as_dict`, `max_tree_size` | Gradiens non li usa (`fonti/siti/estrazione.py:32-33`) |
| youtube-transcript-api 1.2.5 | in 1.2.5 esistono solo i metodi d'istanza `fetch` e `list` (`youtube_transcript_api/_api.py:51, 76`); le funzioni statiche della 0.x non ci sono più | Gradiens usa i metodi d'istanza. Non intercetta però `YouTubeRequestFailed`, `RequestBlocked`, `PoTokenRequired` (`_errors.py:83, 131, 268`): finiscono nell'`except Exception` dell'esecutore (`esecuzione/esecutore.py:312`) come "errore" generico, e si riprova alla volta dopo. Non è una deprecazione; il messaggio all'utente potrebbe essere più chiaro |
| python-telegram-bot 22.8 | punti che emettono `PTBDeprecationWarning` nel pacchetto (`telegram/_bot.py:7601` per i sondaggi, `inputmedia`, `_poll`...) | nessuno riguarda i metodi usati da `telegram/bot.py` |
| feedparser 6.0.14 | nessun `deprecat` nel sorgente | — |
| SQLAlchemy 2.1.8 e Alembic 1.20.1 | API 2.0 (`select`, `Mapped`, `mapped_column`, `DeclarativeBase`, `Session.get_one`); nessun `Query` legacy (`.query(` assente) | a posto; resta solo il punto 2.1, che è di Python |
| pydantic-settings | `_env_file` è il modo documentato di scegliere il file all'istanza | a posto |
| libreria standard (Python 3.14) | `datetime.utcnow`, `utcfromtimestamp`, `asyncio.get_event_loop`, politiche dei cicli `asyncio`, `asyncio.iscoroutinefunction`, `codecs.open`, adattatori predefiniti di `sqlite3` (deprecati dalla 3.12): cercati con `ast` e `grep` | **nessun uso** |

### 2.6 `httpx`, fermo da quasi due anni

`httpx` 0.28.1 è del 6 dicembre 2024 (M-1). Il suo successore è `httpx2` (`METADATA`: "The next generation HTTP
client", stesso autore), già usato dal `TestClient` di Starlette e con una funzione `alias_httpx()` "for
applications migrating from `httpx`" (`httpx2/_alias.py:58-63`). Gradiens non può lasciare `httpx` finché
python-telegram-bot 22.8 lo richiede (`httpx<0.29,>=0.27`, dal suo `METADATA`). **Raccomandazione**: niente ora;
ricontrollare a ogni rilascio di python-telegram-bot. Non è una deprecazione annunciata: è una libreria ferma.

### 2.7 API interne e comportamenti che dipendono dalla versione

- **Nomi privati di librerie esterne**: nessuno. Nessun import di nomi con il trattino basso da librerie, nessun
  accesso ad attributi privati (cercato con `ast`). I nomi privati di Gradiens usati da altri moduli sono già nel
  documento 03 (sezione 1.7 e A-15).
- **Moduli di yt-dlp**: `yt_dlp.utils.DownloadError` (`fonti/youtube/__init__.py:80`) sta in un modulo di servizio;
  non ho verificato che sia dichiarato come API pubblica.
- **uvicorn**: `server.should_exit` (`app/servizio.py:55`) è un attributo senza trattino basso ma non ho verificato
  che sia documentato. Il controllo di `/api/spegni` (`app/servizio.py:50`) dipende da due valori predefiniti di
  uvicorn: `proxy_headers=True` e `forwarded_allow_ips` preso dalla variabile d'ambiente `FORWARDED_ALLOW_IPS` o, se
  manca, `"127.0.0.1,::1"` (`uvicorn/config.py:225, 228, 361-365`). Una versione nuova o la variabile d'ambiente
  cambiano chi è "locale". Proposta: passare i due valori in modo esplicito in `uvicorn.Config` (`app/servizio.py:137`),
  scegliendoli con la proposta 6c (S-14 del documento 02). Anche l'ordine "lifespan prima della porta"
  (`uvicorn/server.py:115-118`), su cui si basa la scheda 6 del documento 04, è un dettaglio del sorgente: va
  riletto quando si aggiorna uvicorn.
- **`sqlite3`**: punto 2.1.
- **Avvisi di risorse in Python 3.13+**: "A `ResourceWarning` is emitted if `close()` is not called before a
  `Connection` object is deleted" (documentazione di `sqlite3`, "Changed in version 3.13"): è l'origine degli avvisi
  del punto 3.

## 3. I ResourceWarning

### 3.1 Da dove vengono

Misura M-2 (`tracemalloc` su tutta la suite): **tutti** gli avvisi "unclosed database" nascono da connessioni del pool
di un motore SQLAlchemy creato **dai test** e mai chiuso, più una connessione `sqlite3` aperta da un test:

- 40 dalla fixture `client_nuovo` (`tests/conftest.py:39`: `TestClient(crea_app(conf))`, senza `with`, quindi il
  lifespan non gira e nessuno chiude il motore creato a `app/servizio.py:95`);
- 2 da `crea_app` chiamata direttamente in `tests/app/test_servizio.py:23, 49`;
- 63 dai motori creati nei test di 7 file, quasi tutti in fixture identiche (`tests/esecuzione/test_esecutore.py:23`,
  `tests/dati/test_notizie.py:14`, `tests/esecuzione/test_programmatore.py:26`, `tests/dati/test_argomenti.py:14`,
  `tests/dashboard/test_segnali.py:12`, `tests/dati/test_proposte.py:15`, più diversi test di
  `tests/dati/test_database.py`);
- 9 da connessioni aperte nei thread del `TestClient` (prima lettura a `dati/impostazioni.py:20`), dello stesso motore;
- 1 da `tests/dati/test_database.py:84`: `with sqlite3.connect(copia) as c:`. Il `with` di `sqlite3` fa commit o
  rollback ma **non chiude** la connessione (documentazione di `sqlite3`: "The context manager neither implicitly
  opens a new transaction nor closes the connection").

La connessione nasce quasi sempre a `dati/database.py:34` (`motore.connect()` in `migra`) perché è la prima del pool:
torna nel pool alla fine del `with` e resta aperta finché il motore vive. L'avviso compare quando il garbage
collector distrugge il motore, cioè durante un test successivo: per questo i nomi dei test nel riepilogo di pytest
non sono quelli giusti.

L'avviso sul sottoprocesso viene da `tests/app/test_avvio_reale.py`: `cli.avvia` lancia Gradiens staccato con
`subprocess.Popen` (`app/avvio_sistema.py:25`) e non tiene l'oggetto, come deve fare un avvio staccato.

### 3.2 Sono un problema reale?

**No per l'app, sì solo come igiene dei test.**

- In produzione c'è **un solo motore per processo**: `crea_motore` si chiama solo in `crea_app`
  (`app/servizio.py:95`, unico uso in `src`). Il pool tiene aperte fino a 5 connessioni (più 10 temporanee, mappa
  B4) per tutta la vita del servizio; alla fine del processo il sistema operativo chiude i file. Nessuna perdita che
  cresce nel tempo.
- **Windows**: il database resta aperto mentre il servizio gira, e questo è voluto. Le copie di sicurezza usano
  connessioni chiuse esplicitamente (`dati/database.py:63-68`), quindi la rotazione con `unlink` (`:69-70`) funziona
  anche su Windows. Nei test su Windows i file `prova.db` restano aperti fino al garbage collector; pytest pulisce le
  cartelle temporanee vecchie ignorando gli errori, e la suite su Windows è verde (prova del 12 nov). Non ho una
  misura su Windows degli avvisi.
- Il vero costo è un altro: 115-118 avvisi nascondono quello che conta. Un avviso nuovo (per esempio una
  deprecazione dopo un aggiornamento) si perde nel rumore.

### 3.3 Come si chiudono

| Opzione | Che cosa | Chi | Effetto | Costo |
|---|---|---|---|---|
| **A (raccomandata)** | Una fixture `motore` in `tests/conftest.py` che crea, migra e alla fine chiude (`yield`, poi `motore.dispose()` **dopo** la chiusura delle sessioni); le 7 fixture duplicate la usano. Per `client_nuovo`: fixture con `yield` che alla fine chiude il motore dell'app (con B: `app.state.motore.dispose()`), senza avviare il lifespan, che farebbe partire bot e programmatore | tester | provato con un plugin esterno (M-2): da 115 a 1 avviso, 182 test verdi; toglie anche codice duplicato | 1-2 h |
| B (con A) | `app.state.motore = motore` in `crea_app` e `motore.dispose()` alla fine di `ciclo_di_vita` (`app/servizio.py:87-91`) | backend | spegnimento più pulito in produzione; nei test serve comunque A, perché `client_nuovo` non avvia il lifespan | 15 min |
| C | `tests/dati/test_database.py:84`: `with contextlib.closing(sqlite3.connect(copia)) as c:` | tester | toglie l'ultimo avviso "unclosed database" | 5 min |
| D | Sottoprocesso di `test_avvio_reale`: `@pytest.mark.filterwarnings("ignore:subprocess .* is still running:ResourceWarning")` sul test | tester | l'avviso è atteso: l'avvio staccato non aspetta il figlio | 5 min |
| E (scartata) | Ignorare `ResourceWarning` in `pyproject.toml` | — | nasconde anche gli avvisi futuri utili | — |

Attenzione: `dispose()` prima del teardown delle fixture non basta (22 avvisi restano): le sessioni aperte delle
fixture tengono le loro connessioni.

### 3.4 Far fallire i test sugli avvisi?

Oggi `filterwarnings = ["error"]` romperebbe la suite: solo su `tests/dati`, **1 test fallito e 9 errori** (M-2),
perché pytest trasforma l'avviso di un finalizzatore in `PytestUnraisableExceptionWarning`. `-W error::ResourceWarning`
da solo non basta: quegli avvisi nascono fuori dal test e diventano solo altri avvisi.

Raccomandazione: **dopo** A, C e D, in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
filterwarnings = [
    "error::ResourceWarning",
    "error::pytest.PytestUnraisableExceptionWarning",  # gli avvisi nati nei finalizzatori (connessioni non chiuse)
    "error::DeprecationWarning",
]
```

Costo: quando si aggiorna una libreria che emette una deprecazione, la suite diventa rossa su Windows e Linux
anche se Gradiens funziona. È il momento giusto per saperlo (il piano del punto 4 aggiorna una libreria alla volta);
se la deprecazione non dipende da Gradiens si aggiunge una riga `ignore` mirata, con un commento e il nome della
libreria. Non metterei `"error"` per tutte le categorie: un `UserWarning` di una libreria non è un difetto di
Gradiens.

## 4. Politica delle versioni e piano degli aggiornamenti

### 4.1 Oggi

`pyproject.toml` ha 13 dipendenze dirette: 8 senza vincolo, 5 con un solo minimo (`feedparser>=6.0.14`,
`python-telegram-bot>=22`, `trafilatura>=2.3.1`, `youtube-transcript-api>=1.2.5`, `yt-dlp>=2026.10.26`); nessun
limite superiore tranne `uv_build<0.14`. `uv.lock` fissa tutte le versioni, anche le transitive, per Windows e Linux;
la CI usa `uv sync --locked` (`.github/workflows/test.yml`), che dà errore se il lock non corrisponde a
`pyproject.toml`. Per un'applicazione (non una libreria) è la scelta giusta: le versioni cambiano solo quando
qualcuno aggiorna `uv.lock` e fa il commit.

Un punto debole: `gradiens aggiorna` lancia `uv sync` **senza** `--locked` (`app/aggiornamento.py:60`). La
documentazione di uv (pagina "Syncing", letta il 15 nov 2026) dice che "Locking and syncing are *automatic*" e che
con `--locked` "If the lockfile is not up-to-date, uv will raise an error instead of updating the lockfile".
Se un commit avesse `pyproject.toml` e `uv.lock` non allineati (la CI lo vedrebbe, ma l'utente potrebbe aggiornare
prima), il PC dell'utente riscriverebbe il lock (è il comportamento "automatico" descritto dalla pagina; non l'ho
provato): un file modificato che poi blocca il `gradiens aggiorna`
successivo, perché `aggiorna` rifiuta le modifiche locali (`app/aggiornamento.py:32-33`). Proposta: `uv sync --locked`
anche lì (backend, una riga; il messaggio d'errore di `:61-62` resta valido).

### 4.2 Opzioni

| Opzione | Pro | Contro | Raccomandazione |
|---|---|---|---|
| **A. Lasciare così** (minimi, niente massimi, lock) | semplice; nessuna sorpresa: cambia solo ciò che si aggiorna | un `uv lock --upgrade` generale può portare versioni maggiori di tutto insieme | **sì**, con la regola sotto |
| B. Limiti superiori sulle librerie che rompono (per esempio `python-telegram-bot<23`, `sqlalchemy<2.2`) | `uv lock --upgrade` non salta una versione maggiore | va alzato a mano; con il lock e la regola "un pacchetto alla volta" protegge da un errore che non si fa; uv rispetta i limiti ("an upgrade will not go beyond that version", pagina "Syncing") | no, salvo un caso concreto |
| C. Aggiornamento periodico di `uv.lock` con la suite in CI su Windows e Linux | si resta vicini alle versioni nuove; problemi piccoli e uno alla volta | un'ora al mese di lavoro e la prova manuale per YouTube e Claude Code | **sì**, mensile, a mano |
| D. Dependabot o Renovate | segnala da solo le versioni nuove (Dependabot elenca `uv` tra gli ecosistemi supportati, pagina di GitHub letta il 15 nov 2026) | apre una pull request per ogni pacchetto: con yt-dlp (650 rilasci su PyPI) e un solo sviluppatore che lavora su `main` senza pull request è rumore; i commit li fa solo l'utente; Renovate è un'app esterna da autorizzare | no per ora; eventualmente Dependabot solo per `github-actions` (`actions/checkout@v4`, `astral-sh/setup-uv@v6`) |
| E. Un controllo "canarino" in CI: ogni mese `uv lock --upgrade` in una copia e la suite, senza commit | dice in anticipo che cosa si romperebbe | minuti di CI (Windows conta di più; limiti del piano GitHub non verificati); un fallimento che nessuno guarda | facoltativo, dopo C |

**Regola proposta**: mai `uv lock --upgrade` su tutto; sempre `uv lock --upgrade-package <nome>` (la pagina
"Syncing" di uv: aggiorna "a single package to the latest version, while retaining the locked versions of all
other packages"), un pacchetto o un gruppo coerente per commit, con la suite verde su Windows e Linux.

### 4.3 Il piano, in ordine

Comandi uguali su Windows (PowerShell) e Linux (bash), dalla cartella di Gradiens. "Indietro" = come tornare alla
versione prima. I commit li fa l'utente.

| Passo | Che cosa | Beneficio | Rischio | Come si prova | Come si torna indietro |
|---|---|---|---|---|---|
| 0 | `uv self update` (uv 0.13.7 → 0.13.8) su ogni PC; `uv_build` è già dentro `<0.14` | correzioni di uv | basso | `uv --version`; la suite | `uv self update 0.13.7` (se uv è stato installato con l'installatore ufficiale; non verificato per altre installazioni) |
| 1 | `uv lock --upgrade-package fastapi --upgrade-package pydantic-settings --upgrade-package pydantic`; poi `uv sync --locked` | 9 rilasci di FastAPI (correzioni della pulizia delle dipendenze, limiti di concorrenza delle dipendenze), correzioni di pydantic | basso: nessuna voce "Breaking" che riguardi Gradiens (§2.4) | suite (`uv run pytest`) su Linux e in CI su Windows; a mano: dashboard, una form con casella di spunta (Impostazioni > Esecuzione), configurazione iniziale con un Gradiens nuovo | `git checkout HEAD~1 -- uv.lock` (o `git revert` del commit) e `uv sync --locked` |
| 2 | dipendenze di sviluppo: `ruff` (§6) e `pytest-cov` (decisione 23), insieme | linter; rapporto di copertura | nessuno per l'app | `uv run ruff check`, `uv run pytest --cov` | togliere le righe da `[dependency-groups]` e rifare il lock |
| 3 | yt-dlp (con la decisione sul runtime JavaScript, §2.2) e youtube-transcript-api, quando escono versioni nuove | YouTube cambia spesso | medio: i test simulano la rete | suite **e** prova vera chiesta all'utente: `gradiens esegui` con un canale, oppure uno script che chiama `risolvi_canale` e `completa` su un video recente (nessuna quota LLM) | come il passo 1 |
| 4 | SQLAlchemy e Alembic | correzioni | medio: tocca migrazioni e transazioni | suite; migrazione di una **copia** del database vero (`.gradiens/gradiens.db` copiato in una cartella di prova, `GRADIENS_CARTELLA_DATI` puntato lì) | come il passo 1; il database vero non va toccato |
| 5 | python-telegram-bot | API di Telegram | medio | suite; a mano: `/stato`, un cuore da Telegram, il messaggio di fine esecuzione | come il passo 1 |
| 6 | trafilatura, htmldate, lxml, feedparser | estrazione e date | medio (cambia che cosa si estrae) | suite (pagine salvate); poi confronto delle metriche dei siti nelle due esecuzioni successive | come il passo 1 |
| 7 | uvicorn, Starlette (attraverso FastAPI), httpx | servizio | medio | suite, compreso `tests/app/test_avvio_reale.py`; a mano `gradiens avvia`, `stato`, `spegni` su Windows e Linux; rileggere `uvicorn/server.py` per l'ordine lifespan-porta (scheda 6 del documento 04) | come il passo 1 |
| 8 | htmx (file statico) | correzioni | basso | tutte le pagine con htmx (cuore, filtri, avanzamento, Impostazioni) | `git revert` |
| 9 | Python: correzioni 3.14.x | sicurezza | basso | suite; avvio vero | rimettere la versione precedente con uv |
| — | Python 3.15 o 3.16 | — | **alto** con 3.16 (§2.1) | solo dopo il punto 2.1 e una decisione apposta | — |

Per il passo 9 non ho verificato il comando esatto di uv 0.13.7 per spostare un ambiente esistente a una correzione
nuova (`.python-version` dice solo `3.14`): da controllare nella documentazione di uv quando serve.

### 4.4 yt-dlp, un caso a parte

stack.md dice che va aggiornato spesso. Come farlo senza toccare il resto:

1. `uv lock --upgrade-package yt-dlp` cambia solo yt-dlp e, se servono, le sue dipendenze (con l'extra `default`
   anche `yt-dlp-ejs`, la cui versione è fissata da yt-dlp stesso). Poi `uv sync --locked`, la suite, la prova vera
   del passo 3, il commit. Uguale su Windows e Linux.
2. Sul PC dell'utente arriva con `gradiens aggiorna` (che fa `git merge` e `uv sync`), come ogni altro aggiornamento.
3. Il minimo in `pyproject.toml` (`yt-dlp>=2026.10.26`) **non** va alzato a ogni aggiornamento: basta il lock.

**Come se ne accorge l'utente quando è vecchio**: oggi in nessun modo. yt-dlp ha un suo avviso "Your yt-dlp version
(...) is older than 90 days!" (`yt_dlp/update.py:182-194`), ma lo emette solo quando yt-dlp si usa da riga di comando (parametro `warn_when_outdated`, `yt_dlp/YoutubeDL.py:708-710`, impostato solo in `yt_dlp/__init__.py:957`): usato come libreria, come fa Gradiens, non lo emette mai, nemmeno togliendo `quiet` e `no_warnings`. Resta vero che `no_warnings` nasconde l'avviso sul runtime JavaScript.
Proposta (backend, poche righe): un segnale nella dashboard (`dashboard/segnali.py`, `UI-14`) quando la data di
`yt_dlp.version.__version__` (è una data, `2026.10.26`) è più vecchia di 60 giorni e ci sono canali YouTube, con il
testo "yt-dlp ha più di 60 giorni: aggiorna Gradiens (se c'è una versione nuova) o chiedi un aggiornamento delle
dipendenze". Senza rete né costi. Il segnale più forte resta lo stato dei canali che vanno in errore (stack.md, nota
1), che però arriva dopo il guasto.

### 4.5 Claude Code come dipendenza

Claude Code non è in `pyproject.toml` ma è la dipendenza più importante (ADR 0006): senza, nessuna notizia viene
valutata.

**Che cosa usa Gradiens** (tabella del punto 2.3): `claude -p` con 9 opzioni e il messaggio su stdin
(`llm/claude_code.py:86-100`); il JSON della risposta (`interpreta`, `:45-61`); `claude auth status` (`:117-129`); il
file delle credenziali per la scadenza del login (`:132-141`); l'ambiente senza `ANTHROPIC_API_KEY` e
`ANTHROPIC_AUTH_TOKEN` (`:40-42`); `GRADIENS_CLAUDE` o il `PATH` (`:29-37`); su Windows il percorso dentro il
pacchetto npm (`app/avvio_sistema.py:38-39`).

**Come si aggiorna**: l'installazione nativa (quella di questo PC) "automatically update[s] in the background";
l'aggiornamento "take[s] effect the next time you start Claude Code" (pagina "Advanced setup", letta il 15 nov
2026). Quindi la versione può cambiare tra un'esecuzione e l'altra senza che l'utente faccia nulla. Su questo PC c'è
ancora la 2.1.316, mentre il changelog ufficiale arriva alla 2.1.325 (13 nov): non ho verificato perché non si sia
aggiornato (impostazioni di `~/.claude`, fuori dalla cartella del progetto, non lette).

**Che cosa può cambiare con un aggiornamento, e che cosa vedrebbe Gradiens oggi**:

| Cambiamento | Effetto su Gradiens oggi |
|---|---|
| `--bare` diventa il predefinito di `-p` | ogni chiamata fallisce per il login; la risposta arriva su stdout con `is_error` ("When a failure happens inside the run, such as missing authentication, Claude Code prints the failure as the result on stdout", pagina headless); se il testo non contiene le parole della quota (ipotesi: il testo esatto non è documentato), `ErroreLLM`, un nuovo tentativo (`:81-83`), e la notizia conta come errore. `pronto()` (`:72-74`) non lo vede, perché `claude auth status` non usa `-p`. Risultato: un'esecuzione intera di errori, il doppio delle chiamate, nessuna notizia |
| un'opzione cambia nome o sparisce | "If you pass an invalid flag, Claude Code reports the error to stderr before the run starts": stdout vuoto, `ErroreLLM` con l'inizio di stderr (`:108-109`); stesso effetto a cascata |
| cambia un campo del JSON (`is_error`, `api_error_status`, `usage`...) | token contati a zero (`:59-61`); una quota esaurita non più riconosciuta diventa un errore generico e l'esecuzione continua a chiamare invece di fermarsi (`LLM-06`); nessun avviso |
| cambia `claude auth status` (`loggedIn`, `subscriptionType`) | la configurazione iniziale e `pronto()` direbbero "non collegato" anche con il login valido: esecuzioni bloccate (`ACC-15`) |
| cambia il file delle credenziali | `scadenza_login` restituisce `None`: sparisce l'avviso di scadenza del login, in silenzio |
| su Windows cambia la struttura del pacchetto npm | "Eseguibile di Claude Code non trovato" (`llm/claude_code.py:35-36`) |

**Come accorgersene presto** (in ordine di costo):

1. **Versione registrata a ogni esecuzione** (backend): `claude --version` (opzione documentata) all'inizio di
   `pronto()`, scritta nel log e nelle metriche; se è diversa da quella dell'ultima esecuzione riuscita, un segnale
   nella dashboard e una riga nel messaggio Telegram ("Claude Code è passato da X a Y"). Ipotesi da verificare: che
   `--version` non consumi quota (non contatta il modello).
2. **Errore di login che ferma subito l'esecuzione** (backend): in `interpreta`, riconoscere gli errori di
   autenticazione (`api_error_status` 401 o 403, o il testo) e sollevare un'eccezione che, come `QuotaEsaurita`, ferma
   l'esecuzione al primo errore con un motivo chiaro ("Claude Code non usa il login dell'abbonamento: vedi l'Aiuto")
   invece di fallire notizia per notizia. Va scritto con un test che usa il finto `claude` dei test.
3. **Prova di fumo dopo ogni cambio di versione** (manuale, segnalata dal punto 1): uno script in `scripts/misura/`
   (decisione 14) che fa **una** chiamata con le stesse opzioni e lo schema del pre-filtro, e controlla
   `structured_output`, `usage`, `is_error`, poi `claude auth status`. Costo: una chiamata breve (la misura del 12
   nov dava circa 1.300 token di contesto con lo schema); va autorizzata dall'utente come abitudine (§7). Uguale su
   Windows e Linux: `uv run python scripts/misura/prova_claude.py`.
4. **Campi documentati al posto di quelli interni**: per `auth status` usare il codice di uscita (documentato) e
   `authMethod` (`claude.ai` per l'abbonamento) come prima scelta, `loggedIn` e `subscriptionType` solo per il testo;
   per il file delle credenziali partire da `configDirectory` della stessa risposta (documentato dalla 2.1.268)
   invece di ricostruire `~/.claude` e `CLAUDE_CONFIG_DIR`.

**Fissare la versione?** Opzioni documentate nella pagina "Advanced setup":

| Opzione | Effetto | Contro |
|---|---|---|
| lasciare l'aggiornamento automatico (canale `latest`, il predefinito) | sempre l'ultima | il cambio arriva quando arriva |
| **canale `stable`** (`"autoUpdatesChannel": "stable"` in `~/.claude/settings.json`, con `minimumVersion` per non tornare indietro) | "a version that is typically about one week old, skipping releases with major regressions" | una settimana di ritardo anche per l'uso interattivo; "A newly launched model can require a Claude Code version newer than the stable channel serves" |
| `DISABLE_AUTOUPDATER=1` (in `env` di `~/.claude/settings.json`) e aggiornamento a mano con `claude update` dopo aver letto il changelog | nessuna sorpresa | ci si deve ricordare di aggiornare; vale anche per lo sviluppo di Gradiens con Claude Code |

Il file è dello strumento e vale per tutto l'utente, sviluppo di Gradiens compreso: la scelta è dell'utente (§7). Su
Windows il file è `%USERPROFILE%\.claude\settings.json`, su Linux `~/.claude/settings.json`. Gradiens non deve
scriverlo (`PER-03`: dati solo nella cartella del progetto). Raccomandazione: canale `stable` più i punti 1 e 2.

**Se `--bare` diventa il predefinito**:

1. Leggere il changelog: oggi la CLI reference non ha un'opzione per disattivare la modalità bare (le opzioni `--no-*`
   documentate sono `--no-browser`, `--no-chrome`, `--no-post`, `--no-session-persistence`). Se il cambio porta
   un'opzione per tornare al comportamento di oggi, aggiungerla a `OPZIONI_ISOLAMENTO` (`llm/claude_code.py:18-25`):
   una riga, uguale su Windows e Linux.
2. Finché non c'è: restare sulla versione precedente (`DISABLE_AUTOUPDATER=1` e `claude install <versione>`,
   comando documentato).
3. Da verificare allora: se in bare un token creato con `claude setup-token` (documentato "for CI and scripts",
   "Requires a Claude subscription") viene accettato. La pagina headless dice solo che in bare Claude Code "never reads
   OAuth credentials or the system keychain" e che servono `ANTHROPIC_API_KEY` o `apiKeyHelper`.
4. Ultima scelta: un altro provider dietro l'interfaccia (ADR 0006, `LLM-03`), per esempio l'API di Claude, a
   pagamento: cambia la decisione 6, va chiesto.

Proposta per l'ADR 0006 (architetto): una sezione "Rischi" con `--bare`, i campi non documentati e il piano sopra.

## 5. Stile: incoerenze e convenzioni prevalenti

Misure M-3. Per ogni aspetto: la convenzione prevalente, le eccezioni, la proposta. Il principio: uniformare alla
convenzione di Gradiens, non a una esterna; dove l'incoerenza non costa niente, lasciare così.

| Aspetto | Convenzione prevalente | Eccezioni | Proposta |
|---|---|---|---|
| Lunghezza delle righe | entro **120 caratteri**: 98,6% delle righe di `src` (85 oltre su 5.944), 97,6% di `tests` (73 su 3.096); mediana 49 | 16 righe oltre 130 in `src` (elenco in M-3), massima 154 (`esecuzione/esecutore.py:241`) | 120 come limite dichiarato (ruff); le righe lunghe si spezzano quando si tocca il file, o con il formatter |
| Continuazione delle righe | due stili quasi alla pari in `src`: 72 istruzioni allineate alla parentesi aperta (`llm/claude_code.py:121-122`), 57 con la parentesi a fine riga | in `tests` prevale l'allineamento (55 contro 16) | lasciare così finché non si adotta il formatter: è l'unico punto in cui il formatter cambia molto |
| Apici | virgolette doppie: **100%** delle stringhe che non contengono `"` (1.942 stringhe e 150 f-string in `src`) | 1 in `tests/dashboard/test_rotte.py:344`; apici singoli solo dentro le f-string (`app/cli.py:103`) o per contenere `"` | lasciare così |
| Import | ordine "isort" in **56 moduli su 58** di `src` e 22 su 25 di `tests` | `dashboard/rotte.py:3-6, 20-21`, `dashboard/rotte_impostazioni.py:7-8, 23`, 3 file di test (M-3) | correggere con `ruff check --fix` (regola I) |
| Import dentro le funzioni | in cima al modulo (6 eccezioni in `src`, tutte motivate: avvio più leggero della CLI, `ctypes` solo per Windows, un ciclo di import) | 34 in `tests` | lasciare così; il ciclo di `dashboard/rotte_impostazioni.py:45` è materia del documento 03 |
| Nomi | italiano per tutto, inglese solo per termini tecnici (`feed`, `sitemap`, `token`, `url`, `host`) o imposti (`upgrade`/`downgrade` di Alembic); `snake_case`, `PascalCase` per le classi, MAIUSCOLO per le costanti di modulo (121); `_nome` per ciò che resta nel modulo (106 funzioni su 431) | 5 variabili `l` (`dashboard/comune.py:48, 53, 58, 63`, `fonti/siti/strategie/feed.py:48`): si confonde con `1`; nomi privati usati da altri moduli: già nel documento 03 (1.7, A-15) | rinominare le 5 `l` (per esempio `ora`, `locale`); nessuna regola di nomi in ruff (le regole `N` riguardano maiuscole e minuscole, non la lingua) |
| Errori | eccezioni specifiche (71 `except` su 81 in `src`), 9 eccezioni proprie per pacchetto, messaggi in italiano pensati per l'utente con il rimedio (`llm/claude_code.py:33, 113, 125`); `raise ... from None` dove la causa non serve; nessun `raise` in un `except` senza `from` | 10 `except` larghi, tutti alle frontiere (esecuzione, programmatore, bot, pannello), tutti commentati, 8 con `log` (`esecuzione/esecutore.py:153, 224, 236, 312, 339, 374`, `esecuzione/programmatore.py:76`, `telegram/bot.py:177`); il pannello (`app/pannello.py:147`) mostra l'errore all'utente invece di scriverlo nel log; 3 `except ... pass` motivati | lasciare così; è una convenzione buona e coerente |
| Logging | un logger per modulo, solo nei 5 moduli che scrivono nei log; **100%** delle chiamate con parametri `%s` o testo fisso, nessuna f-string; livelli: `info` per gli eventi, `warning` per ciò che si recupera, `exception` per l'imprevisto; nessun `debug` | `app/servizio.py:30` usa `getLogger("gradiens")` invece di `__name__` (nei log compare `gradiens` invece di `gradiens.app.servizio`) | lasciare così (non costa niente) |
| Segreti nei log (`PER-04`) | `httpx` portato a `WARNING` (`app/servizio.py:129-130`), `InvalidToken` non scritto (`telegram/bot.py:127`), `SecretStr` per il token (`app/configurazione.py:30`) | controllo dei 4 file di log veri: **0** stringhe con la forma di un token Telegram (`bot<numeri>:<35+ caratteri>`, contate senza stamparle); 52 righe `INFO httpx` solo il 6 nov tra le 23:20 e le 23:27, prima della correzione, verso arXiv, YouTube e due siti; `uvicorn.access` scrive ogni richiesta con la query (2.056 righe), compreso il testo cercato nella dashboard: dati dell'utente, non segreti | lasciare così; non ho verificato che le eccezioni di python-telegram-bot scritte da `log.exception` (`telegram/bot.py:178`) non contengano mai l'indirizzo con il token |
| Type hint | firme complete nell'**80%** delle funzioni di `src` (343 su 431; `dati` 98%, `app` 93%, `fonti` 79%); `Any` mai usato | `dashboard` 39% (31 su 79: le rotte non dichiarano il ritorno); 35 annotazioni `dict` senza parametri (dati JSON, schemi); `tests` quasi senza annotazioni (13 su 286) | lasciare così: senza un controllo dei tipi (mypy) aggiungere annotazioni non porta nulla di verificabile |
| Docstring | modulo con docstring nel 91% dei file di `src`; funzioni solo dove serve (37%; pubbliche 40%); una o due frasi in italiano, spesso con il codice del PRD tra parentesi; nessuna sezione `Args:`/`Returns:` | `tests`: 4 moduli su 25 | lasciare così; nessuna regola `D` in ruff |
| Rimandi ai requisiti | 98 commenti e 106 docstring citano un codice del PRD, 9 commenti un ADR | — | lasciare così: è il legame più utile tra codice e documenti |
| `shortcut:` | 3 commenti, tutti limiti noti e voluti (`dati/notizie.py:65`, `fonti/siti/__init__.py:60`, `fonti/youtube/__init__.py:108`); nessun `TODO`/`FIXME` | — | lasciare così |
| Righe vuote | due righe vuote attorno alle definizioni di primo livello | 17 punti in `src`, 4 in `tests` (per esempio `dashboard/comune.py:30`) | solo con il formatter |
| Codifica dei file (CLAUDE.md, portabilità) | `encoding="utf-8"` sempre in `src` | `tests/llm/test_claude_code.py:40, 57, 68` (`write_text`/`read_text` senza `encoding`) | correggere (tester, minuti): su Windows la codifica predefinita non è UTF-8 |

## 6. Linter e formatter

### 6.1 Proposta: ruff

ruff fa le due cose con un solo strumento e una sola configurazione in `pyproject.toml`, gira uguale su Windows e
Linux e non ha dipendenze. Alternative scartate: flake8 con isort e black (tre strumenti e tre configurazioni per lo
stesso risultato); pylint (lento, molte segnalazioni di stile da spegnere).

Configurazione minima (da aggiungere a `pyproject.toml`; è una proposta, non l'ho applicata):

```toml
[dependency-groups]
dev = ["httpx2", "pytest", "ruff"]  # ruff fissato da uv.lock, uguale su Windows, Linux e CI

[tool.ruff]
line-length = 120  # la lunghezza prevalente misurata (punto 5)
# target-version non serve: ruff lo ricava da requires-python (>=3.14).

[tool.ruff.lint]
# Le regole predefinite (E4, E7, E9, F) più import in ordine (I), errori probabili (B), sintassi moderna (UP).
# E501 (righe lunghe) resta fuori finché non c'è il formatter. Niente regole N: i nomi italiani vanno bene così.
select = ["E4", "E7", "E9", "F", "I", "B", "UP"]

[tool.ruff.lint.isort]
known-first-party = ["gradiens"]

[tool.ruff.format]
# Solo se si adotta il formatter (6.3). Le migrazioni restano come Alembic le ha scritte.
exclude = ["src/gradiens/dati/migrazioni/versions/*"]
```

Le eccezioni per i nomi italiani non servono perché non si attivano le regole `N`; quelle per le migrazioni non
servono al linter (nessuna segnalazione stimata: `sa` e `op` sono usati in tutte le 11 migrazioni, nessuna riga oltre
120) e servono solo al formatter. `# noqa: E731` già presenti (3) restano validi.

Regole utili trovate al punto 5 che questa configurazione non copre: la codifica dei file (in ruff esiste una regola
per la codifica non indicata, `PLW1514`, ma non ho verificato se nella versione da adottare è ancora in anteprima né
quali chiamate controlla); le connessioni non chiuse del punto 3 (non conosco una regola che le prenda).

### 6.2 Impatto del linter (stima)

**È una stima**: ruff non è installato e installarlo era vietato in questa fase. I numeri vengono dagli script di M-3,
che imitano le regole in modo approssimato. Il numero vero si ottiene con `uvx ruff check --statistics` (scarica
ruff: serve la rete e il permesso dell'utente) o, dopo il passo 2 del piano, con `uv run ruff check --statistics`.

| Regola | Stima | Dove | Correzione |
|---|---|---|---|
| I001 (import in ordine) | 5 file | `dashboard/rotte.py`, `dashboard/rotte_impostazioni.py`, `tests/esecuzione/test_esecutore.py`, `tests/fonti/siti/test_sicurezza.py`, `tests/dashboard/test_rotte.py` | automatica |
| F401 (import non usati) | 3 | `tests/dati/test_proposte.py:1, 6`, `tests/telegram/test_bot.py:15` | automatica |
| E741 (nome `l`) | 5 | `dashboard/comune.py:48, 53, 58, 63`, `fonti/siti/strategie/feed.py:48` | a mano |
| B007 (variabile di ciclo non usata) | 1 | `tests/dati/test_notizie.py:102` | a mano (`_`) |
| B905 (`zip` senza `strict`) | 1 | `esecuzione/esecutore.py:202` | a mano: `strict=True` (le due liste hanno per costruzione la stessa lunghezza) |
| E731 | 0 | i 3 casi hanno già `noqa` | — |
| UP, B904, B006, B008, E711-E722, E402, F841 | 0 trovati | — | — |
| **Totale** | **circa 15 segnalazioni, 15-25 righe cambiate in 11 file** | | |

Il linter tocca pochi file per proprietario (backend, scraping, tester): si può fare in passi separati, come chiede
la decisione 32.

### 6.3 Impatto del formatter (stima)

`ruff format` con `line-length = 120` (stile di black) cambierebbe, secondo i conteggi di M-3:

| Che cosa | Righe coinvolte oggi | Effetto |
|---|---|---|
| righe oltre 120 | 158 (85 `src`, 73 `tests`) | spezzate su più righe (2-5 l'una) |
| istruzioni con continuazione allineata alla parentesi | 127 istruzioni, 312 righe | riscritte tutte: unite in una riga se ci stanno, altrimenti un argomento per riga con la virgola finale |
| istruzioni già a parentesi aperta | 73 istruzioni, 506 righe | in parte unite in una riga se ci stanno (quante, non stimabile senza ruff) |
| righe vuote attorno alle definizioni | 21 punti | aggiunte o tolte |
| slice con espressioni (`a[x + 1 :]`) | 6-11 | spazi attorno ai due punti |
| apici | 1 | — |

**Stima**: tra **50 e 80 file su 89** e tra **1.000 e 2.000 righe di diff** (aggiunte più tolte). Il numero vero:
`uvx ruff format --check` (elenca i file) e `uvx ruff format --diff` (mostra il diff), con la rete e il permesso
dell'utente. I template Jinja, il CSS e il JavaScript non vengono toccati.

### 6.4 Linter e formatter: compromessi

| | Linter | Formatter |
|---|---|---|
| Che cosa cambia | 15-25 righe mirate (stima) | quasi tutti i file |
| Che cosa trova | import non usati, nomi ambigui, errori probabili nei refactoring futuri | niente: solo forma |
| `git blame` | invariato | ogni riga riformattata punta al commit di formattazione; si mitiga con `.git-blame-ignore-revs` nella radice (gli hash dei commit di sola formattazione) e `git config blame.ignoreRevsFile .git-blame-ignore-revs` su ogni clone, Windows e Linux (che GitHub lo legga da solo non l'ho verificato oggi) |
| Proprietari delle cartelle | pochi file per proprietario | un commit tocca tutte le cartelle: va diviso in un commit per proprietario (`src/gradiens/fonti`, `src/gradiens/dashboard`, ..., `tests`), uno dopo l'altro, in un momento senza lavori in corso |
| Conflitti | nessuno | con le modifiche già decise (ADR 0010, 0011, 0012, passi R-*) ancora da scrivere: chi lavora dopo parte dalla forma nuova, ma un lavoro a metà va rifatto o riformattato |
| Agenti | aiuta: `uv run ruff check` è una prova oggettiva prima di dire "fatto" | aiuta dopo: niente discussioni di forma nelle revisioni |

### 6.5 Dove gira, e come dipendenza

- **CI**: un passo `uv run ruff check` in `.github/workflows/test.yml`, sulla matrice Windows e Linux (costa pochi
  secondi; un solo sistema basterebbe, ma tenere un solo flusso è più semplice). Con il formatter, anche
  `uv run ruff format --check`. ruff con `line-ending = "auto"` (il predefinito) rispetta i fine riga del file, quindi
  i checkout di Windows con CRLF non danno differenze (non verificato su Windows).
- **pre-commit**: un altro strumento da installare su ogni PC, e i commit li fa solo l'utente; un gancio che blocca il
  commit è attrito. Raccomandazione: niente pre-commit; `uv run ruff check --fix` prima di dire "fatto" (si può
  aggiungere alla definizione di "fatto" in CLAUDE.md, decisione dell'utente) e la CI come rete.
- **Dipendenza di sviluppo o `uvx`**: come dipendenza di sviluppo la versione sta in `uv.lock`, è la stessa su
  Windows, Linux e CI, funziona senza rete dopo `uv sync`, e si aggiorna come le altre (con
  `--upgrade-package ruff`); con `uvx` non c'è niente nel lock, ma ogni PC scarica la versione che trova (o una fissata
  a mano con `uvx ruff@<versione>`) e serve la rete. Raccomandazione: **dipendenza di sviluppo**, come pytest. Per
  orientarsi sulla versione: trafilatura 2.3.1 dichiara `ruff==0.16.10` tra i suoi strumenti di sviluppo (dal suo
  `METADATA`); l'ultima va letta su PyPI al momento.

### 6.6 Raccomandazione

1. **Linter subito**, prima dei passi di refactoring della decisione 28: costa poco e fa da rete durante gli
   spostamenti di codice (import rimasti, variabili non usate).
2. **Formatter dopo** i cinque passi R-* e le modifiche già decise, una cartella per proprietario per commit, con
   `.git-blame-ignore-revs`. Oppure mai: lo stile è già coerente e l'unico vero guadagno sarebbe non pensarci più.
   Decide l'utente (§7).

## 7. Ordine consigliato e domande per l'utente

### 7.1 Ordine

| # | Che cosa | Chi | Perché qui |
|---|---|---|---|
| 1 | Nota sui rischi nell'ADR 0006 (`--bare`, campi interni, piano del 4.5) e nell'ADR 0004 (`autocommit` esplicito) | architetto | solo documenti; fissa le decisioni prima del codice |
| 2 | Claude Code: versione registrata e segnalata, errore di login che ferma l'esecuzione (4.5, punti 1 e 2) | backend, tester | il rischio più alto, e non costa quota |
| 3 | Pulizia dei `ResourceWarning` (3.3 A, B, C, D), poi `filterwarnings` mirato (3.4) | tester, backend | rende visibili gli avvisi degli aggiornamenti che seguono |
| 4 | `autocommit` esplicito in `crea_motore` e test su `PRAGMA foreign_keys` (2.1), insieme alla scheda 5 del documento 04 | backend, tester | la stessa parte di codice |
| 5 | Ruff linter e `pytest-cov` come dipendenze di sviluppo, passo in CI, correzioni (6.2) | architetto (`pyproject.toml`, CI), poi ogni proprietario | prima dei refactoring |
| 6 | Aggiornamento del gruppo del passo 1 (4.3) e `uv sync --locked` in `aggiorna` (4.1); `lxml` dichiarata (1.2) | backend | piccolo e verificabile |
| 7 | yt-dlp: prova vera, runtime JavaScript, segnale "yt-dlp vecchio" (2.2, 4.4) | scraping, backend | serve una prova autorizzata |
| 8 | Abitudine mensile: un pacchetto alla volta (4.3) | utente con gli agenti | — |
| 9 | Formatter, se l'utente lo vuole (6.6) | ogni proprietario | dopo i passi R-* |

**Mai**: `uv lock --upgrade` su tutto insieme; `filterwarnings = ["error"]` prima della pulizia; il formatter in mezzo
ai refactoring; Python 3.16 prima del punto 2.1; scrivere da Gradiens nelle impostazioni di Claude Code (`~/.claude`).

### 7.2 Domande (una alla volta, nell'ordine)

1. **Aggiornamenti di Claude Code**: canale `stable` (con `minimumVersion`), aggiornamento automatico come oggi, o
   aggiornamenti spenti e fatti a mano? *Consigliata*: `stable`. Dà una settimana di margine e salta le versioni con
   regressioni gravi, senza doversi ricordare di aggiornare; vale anche per l'uso interattivo.
2. **Prova di fumo di Claude Code**: autorizzi come abitudine una chiamata breve (circa 1.300-2.000 token, stima) ogni
   volta che Gradiens segnala una versione nuova di Claude Code? *Consigliata*: sì. Costa meno di una notizia valutata
   e scopre `--bare` prima di un'esecuzione intera fallita.
3. **yt-dlp e il runtime JavaScript**: autorizzi una prova vera su un canale seguito (poche richieste a YouTube,
   nessuna quota LLM) e poi l'aggiunta di `yt-dlp[default,deno]`? *Consigliata*: sì. yt-dlp dichiara deprecato l'uso
   senza runtime; la prova dice se oggi manca qualcosa e se Deno funziona su Windows e Linux.
4. **Formatter**: dopo i refactoring, una cartella alla volta; mai; o subito? *Consigliata*: dopo i refactoring. Lo
   stile è già coerente; farlo ora sporcherebbe `git blame` proprio mentre si riscrivono quei moduli.
5. **Avvisi come errori nei test**, dopo la pulizia: `ResourceWarning`, avvisi dei finalizzatori e
   `DeprecationWarning` fanno fallire la suite? *Consigliata*: sì. Una deprecazione nuova si vede nel commit
   dell'aggiornamento che la porta, non mesi dopo.
6. **Strumenti automatici per le versioni** (Dependabot o Renovate)? *Consigliata*: no, un controllo mensile a mano.
   Un solo sviluppatore che lavora su `main` e fa i commit da sé riceverebbe soprattutto pull request di yt-dlp da
   chiudere.

Non sono domande (scelte tecniche): la pulizia dei `ResourceWarning`, `autocommit` esplicito, `uv sync --locked` in
`aggiorna`, `lxml` dichiarata, il linter come dipendenza di sviluppo.

## 8. Fonti esterne

Tutte lette il **15 novembre 2026**.

| Fonte | Che cosa ne ho preso |
|---|---|
| `https://pypi.org/pypi/<pacchetto>/json`, 21 pacchetti, una richiesta ciascuno alle 13:13 UTC (M-1) | ultima versione, data, Python richiesto |
| https://code.claude.com/docs/en/headless | `--bare` "is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release"; in bare "Claude Code never reads OAuth credentials or the system keychain", servono `ANTHROPIC_API_KEY` o `apiKeyHelper`; errori di autenticazione stampati come risultato su stdout; opzioni non valide su stderr prima dell'avvio; `structured_output` assente se la risposta non è valida; stdin fino a 10 MB |
| https://code.claude.com/docs/en/cli-reference | righe di `--bare`, `--safe-mode` ("Authentication, model selection, built-in tools, and permissions work normally, which differs from `--bare`"), `--tools`, `--strict-mcp-config`, `--disable-slash-commands`, `--no-session-persistence`, `--output-format`, `--json-schema`, `--system-prompt`, `--model`, `--version`; `claude auth status` (codice di uscita, `configDirectory`, `authMethod`); `claude setup-token`, `claude update`, `claude install [version]`; nessuna opzione per disattivare bare |
| https://code.claude.com/docs/en/setup | aggiornamento automatico in background dell'installazione nativa; canali `latest` e `stable`; `minimumVersion`; `DISABLE_AUTOUPDATER` e `DISABLE_UPDATES`; installazione di una versione precisa; struttura del pacchetto npm |
| https://code.claude.com/docs/en/changelog | ultima versione 2.1.325 (13 nov 2026); versioni dalla 2.1.319 in poi; nessuna voce su `--bare` nella parte letta (la pagina è stata letta solo in parte) |
| https://docs.python.org/3.14/library/sqlite3.html | `autocommit` predefinito `LEGACY_TRANSACTION_CONTROL`, "The default will change to `False` in a future Python release"; `ResourceWarning` per le connessioni non chiuse dalla 3.13; il `with` non chiude la connessione; adattatori predefiniti deprecati dalla 3.12 |
| https://github.com/yt-dlp/yt-dlp/wiki/EJS (modificata il 12 lug 2026) | perché serve un runtime JavaScript; runtime supportati e versioni minime; `yt-dlp[default]` porta `yt-dlp-ejs` |
| https://github.com/fastapi/fastapi/releases | rilasci 0.162.0-0.163.1 con le date; unica voce "Breaking" rilevante: booleani delle form (0.162.0) |
| https://fastapi.tiangolo.com/release-notes/ | letta, ma il contenuto utile non è arrivato (solo l'indice): ho usato le note su GitHub |
| https://docs.astral.sh/uv/concepts/projects/sync/ | sincronizzazione automatica, `--locked`, `--frozen`, `uv lock --upgrade-package`, limiti superiori rispettati negli aggiornamenti |
| https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories | `uv` e `github-actions` tra gli ecosistemi supportati da Dependabot (la riga di `uv` letta solo in parte) |

Fonti locali (sorgenti delle librerie installate da `uv.lock`, nessuna rete): `sqlalchemy/dialects/sqlite/base.py`
(transazioni legacy, Python 3.16), `starlette/testclient.py`, `starlette/routing.py`, `starlette/exceptions.py`,
`uvicorn/config.py`, `uvicorn/server.py`, `yt_dlp/extractor/youtube/_video.py`, `yt_dlp/update.py`,
`yt_dlp/extractor/common.py`, `trafilatura/core.py`, `youtube_transcript_api/_api.py` e `_errors.py`,
`telegram/_bot.py`, `httpx2/_alias.py`, e i file `METADATA` di yt-dlp, trafilatura, python-telegram-bot, httpx2,
youtube-transcript-api.

## Appendice A — Misure (metodo e dati)

### M-1. Ultime versioni su PyPI (15 nov 2026, 13:13 UTC)

Metodo: uno script fuori dal progetto ha fatto **una** richiesta a `https://pypi.org/pypi/<pacchetto>/json`
per ognuno dei 21 pacchetti, con 2 secondi di pausa tra una e l'altra; `info.version` è l'ultima
versione, la data è il primo file caricato di quella versione (`urls[].upload_time_iso_8601`).

| Pacchetto | Installato (uv.lock) | Ultima su PyPI | Data dell'ultima | Python richiesto |
|---|---|---|---|---|
| alembic | 1.20.1 | 1.20.1 | 22 ott 2026 | >=3.10 |
| fastapi | 0.162.0 | **0.163.1** | 15 nov 2026 | >=3.11 |
| feedparser | 6.0.14 | 6.0.14 | 30 lug 2026 | >=3.10 |
| httpx | 0.28.1 | 0.28.1 | 6 dic 2024 | >=3.8 |
| jinja2 | 3.1.6 | 3.1.6 | 5 mar 2025 | >=3.7 |
| pydantic-settings | 2.16.2 | **2.16.3** | 13 nov 2026 | >=3.11 |
| python-multipart | 0.0.33 | 0.0.33 | 31 ott 2026 | >=3.11 |
| python-telegram-bot | 22.8 | 22.8 | 12 giu 2026 | >=3.10 |
| sqlalchemy | 2.1.8 | 2.1.8 | 4 nov 2026 | >=3.11 |
| trafilatura | 2.3.1 | 2.3.1 | 6 ott 2026 | >=3.10 |
| uvicorn | 0.54.0 | 0.54.0 | 25 set 2026 | >=3.10 |
| youtube-transcript-api | 1.2.5 | 1.2.5 | 5 nov 2026 | <3.16,>=3.8 |
| yt-dlp | 2026.10.26 | 2026.10.26 | 26 ott 2026 | >=3.11 |
| httpx2 (sviluppo) | 2.16.0 | 2.16.0 | 21 ott 2026 | >=3.11 |
| pytest (sviluppo) | 9.2.0 | 9.2.0 | 27 ott 2026 | >=3.10 |
| uv-build (costruzione) | 0.13.7 | **0.13.8** | 12 nov 2026 | >=3.8 |
| uv (strumento) | 0.13.7 | **0.13.8** | 12 nov 2026 | >=3.8 |
| starlette (transitiva) | 1.10.0 | 1.10.0 | 24 ott 2026 | >=3.11 |
| pydantic (transitiva) | 2.14.2 | **2.14.3** | 5 nov 2026 | >=3.10 |
| lxml (transitiva, usata direttamente) | 6.1.3 | 6.1.3 | 2 set 2026 | >=3.8 |
| htmldate (transitiva) | 1.11.0 | 1.11.0 | 2 ott 2026 | >=3.10 |

Altre versioni lette sul disco: htmx **2.0.4** (`dashboard/static/htmx.min.js`, stringa `version:"2.0.4"`,
file aggiunto il 6 nov 2026, commit `34d0e81`); Claude Code **2.1.316** (il comando `claude` in
`~/.local/bin` punta a `~/.local/share/claude/versions/2.1.316`; non è stato eseguito `claude --version`,
vietato in questa fase).

### M-2. Da dove vengono i ResourceWarning (15 nov 2026)

Metodo: suite intera con `PYTHONTRACEMALLOC=30 PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest -q -p no:cacheprovider
-W default::ResourceWarning`, poi uno script che raggruppa gli avvisi per le ultime righe del progetto
(`src/` o `tests/`) nella traccia di allocazione stampata da pytest ("Object allocated at").

| Avvisi | Dove nasce la connessione SQLite non chiusa | Chi la crea |
|---|---|---|
| 40 | `dati/database.py:34` (`motore.connect()` in `migra`) | `app/servizio.py:96` da `tests/conftest.py:39` (fixture `client_nuovo`, quindi tutti i test della dashboard) |
| 19 | `dati/database.py:34` | `tests/esecuzione/test_esecutore.py:24` (fixture) |
| 14 | `dati/database.py:34` | `tests/dati/test_notizie.py:15` (fixture) |
| 10 | `dati/database.py:34` | `tests/esecuzione/test_programmatore.py:27` (fixture) |
| 9 | `dati/impostazioni.py:20` (prima lettura in un thread del `TestClient`) | `esecuzione/programmatore.py:41` da `dashboard/rotte.py:39` |
| 4 + 3 + 3 + 3 | `dati/database.py:34` | fixture di `test_argomenti.py:15`, `test_segnali.py:13`, `test_database.py:14`, `test_proposte.py:16` |
| 2 + 1 + 1 | `tests/dati/test_database.py:60`, `:41`, `:78` (`with motore.begin()` su motori del test) | il test stesso |
| 1 | `tests/dati/test_database.py:84` (`with sqlite3.connect(copia) as c:`: il `with` di `sqlite3` fa commit, **non** chiude) | il test stesso |
| 1 + 1 + 1 + 1 + 1 | `dati/database.py:34` | `test_servizio.py:23`, `:49`, `test_database.py:26`, `:72`, `:93` |
| **115** | | totale "unclosed database" in questa esecuzione (118 nell'esecuzione dei dati grezzi: il numero varia con il momento in cui gira il garbage collector) |
| 1 | `subprocess ... is still running`: `app/avvio_sistema.py:25` (`subprocess.Popen` del processo staccato) | `app/cli.py:39` da `tests/app/test_avvio_reale.py` |

Effetto collaterale della misura: con `PYTHONTRACEMALLOC` il processo figlio di `test_avvio_reale` eredita la
variabile, parte troppo lentamente e il test fallisce (`assert 1 == 0` a `tests/app/test_avvio_reale.py:9`). Non è
un difetto: senza `tracemalloc` la stessa suite è verde. Dopo la misura nessun processo di prova è rimasto acceso
(controllato con `ps`).

Prova in più (solo `tests/dati`, 30 test): con `-W error::ResourceWarning` i test restano **verdi** (30 passati,
28 avvisi `PytestUnraisableExceptionWarning`), perché l'avviso nasce nel finalizzatore della connessione e Python
non può trasformarlo in un'eccezione del test; con `-W error` (tutte le categorie) **1 test fallisce e 9 danno
errore**, perché pytest ritrasforma quegli avvisi in eccezioni.

Controprova (senza toccare il progetto): un plugin di pytest scritto nella cartella temporanea
(`-p chiudi_motori`, con `PYTHONPATH` verso quella cartella) avvolge `dati.database.crea_motore`, ricorda ogni
motore creato e chiama `motore.dispose()` **dopo** il teardown delle fixture di ogni test (`hookimpl(wrapper=True)`
su `pytest_runtest_teardown`). Risultato: **182 passati, da 115 a 1 "unclosed database"** (resta
`tests/dati/test_database.py:84`) più l'avviso del sottoprocesso. Un primo tentativo che chiudeva i motori
*prima* del teardown delle fixture lasciava 22 avvisi: `dispose()` chiude solo le connessioni restituite al pool,
non quelle ancora tenute da una sessione aperta della fixture (`with fabbrica_sessioni(motore)() as sessione: yield
sessione`, per esempio `tests/dati/test_notizie.py:12-17`).

### M-3. Misure di stile (15 nov 2026)

Metodo: tre script in sola lettura (`ast` e `tokenize` della libreria standard, Python 3.13.5 di sistema con `-I`;
il codice è compatibile e l'analisi sintattica non ha dato errori) su tutti i `.py` di `src/gradiens` (64 file,
5.944 righe) e di `tests` (25 file, 3.096 righe), più `awk` per le lunghezze esatte. Conteggi grezzi:

- **Lunghezza delle righe** (caratteri). `src`: mediana 49 (righe non vuote), 90° percentile 103, 95° 112,
  99° 124, massima 154 (`esecuzione/esecutore.py:241`). Righe oltre 79: 1.185; oltre 88: 937; oltre 100: 563;
  oltre 110: 288; oltre 115: 159; **oltre 120: 85**; oltre 125: 38; oltre 130: 16. `tests`: massima 158; oltre
  100: 315; oltre 110: 174; **oltre 120: 73**; oltre 130: 24. Righe per lunghezza esatta in `src`: da 110 a 119
  caratteri fra 17 e 30 righe per valore; a 120 crollano a 8 e da 121 a 130 restano fra 3 e 13: il "muro" pratico
  è 120.
- **Righe oltre 130 in `src`** (16): `esecuzione/esecutore.py:241` (154), `:274` (135), `app/avvio_sistema.py:207`
  (137), `app/cli.py:146` (141), `app/aggiornamento.py:61` (133), `dashboard/comune.py:103` e `:105` (138),
  `dashboard/rotte.py:153` (131), `llm/claude_code.py:138` (137), `telegram/messaggi.py:41` (142), `:59` (147),
  `telegram/bot.py:194` (132), `fonti/siti/indirizzi.py:15` (132), `fonti/siti/profilo.py:30` (132),
  `fonti/siti/strategie/feed.py:95` (141), `fonti/siti/strategie/sitemap.py:18` (143).
- **Istruzioni su più righe**: `src` 192 (836 righe fisiche), di cui 57 nello stile "parentesi aperta a fine riga,
  chiusa su una riga sua", 63 docstring o stringhe su più righe, **72 con le righe di continuazione allineate
  alla parentesi** (per esempio `llm/claude_code.py:121-122`); `tests` 78 (314 righe), 16 nello stile a parentesi,
  55 allineate.
- **Righe vuote**: 17 punti in `src` e 4 in `tests` dove una definizione di primo livello non ha due righe vuote
  prima o dopo (per esempio `dashboard/comune.py:30`, `PAGINE` subito dopo `statico`). Nessuno spazio in fondo alle
  righe, nessun punto e virgola, nessuna istruzione composta su una riga (`if x: return`).
- **Apici**: `src` 1.942 stringhe e 150 f-string con le virgolette doppie; **nessuna** stringa con apici singoli
  fuori da una f-string, tranne quelle che contengono una virgoletta doppia (61 apici singoli contati, tutti dentro
  f-string, come `f"{m['stato']}"` a `app/cli.py:103`, o con `"` dentro). `tests`: 1 sola eccezione
  (`tests/dashboard/test_rotte.py:344`).
- **Import**: blocchi iniziali in ordine "isort" (libreria standard, terze parti, `gradiens`, separati da una riga
  vuota; `import x` prima di `from x import`; nomi in ordine costanti, classi, funzioni) in 56 moduli su 58 di
  `src` e 22 su 25 di `tests`. Fuori ordine: `dashboard/rotte.py:3-6` (riga vuota dentro la libreria standard;
  `gradiens.dati.modelli` prima di `gradiens.dati.impostazioni`, `:20-21`), `dashboard/rotte_impostazioni.py:7-8`
  (`from typing` dopo `import httpx`; `gradiens.app` dopo `gradiens.fonti`, `:23`), `tests/esecuzione/test_esecutore.py`
  (`types` prima di `datetime`), `tests/fonti/siti/test_sicurezza.py`, `tests/dashboard/test_rotte.py:7`. Import
  dentro le funzioni: 6 in `src` (4 in `app/cli.py:47, 101, 179, 188`, per caricare il servizio solo quando
  serve; `app/avvio_sistema.py:222` `ctypes`, solo Windows; `dashboard/rotte_impostazioni.py:45`, per un ciclo di
  import), 34 in `tests`. Import non usati (stima con `ast`): 0 in `src`, 3 in `tests`
  (`tests/dati/test_proposte.py:1` `timedelta`, `:6` `impostazioni`; `tests/telegram/test_bot.py:15` `messaggi`).
- **Nomi**: 431 funzioni in `src`, 106 private (`_nome`); classi in `PascalCase`, funzioni e variabili in
  `snake_case`, costanti di modulo in maiuscolo (121 assegnazioni di modulo in maiuscolo, 58 in minuscolo: 44 sono
  `revision`/`down_revision`/... delle migrazioni, imposte da Alembic, le altre sono oggetti come `log`, `router`,
  `modelli`, `Sessione`). Le parole dei nomi sono italiane; l'inglese compare solo per termini tecnici (`feed`,
  `sitemap`, `token`, `url`, `host`, `timeline`, `home`) o imposti (`upgrade`/`downgrade` di Alembic, `main`).
  Variabili di modulo private: 6 (`_cache`, `_robots`, `_prossima`, `_limiti`...). Nomi ambigui (`l`): 5
  (`dashboard/comune.py:48, 53, 58, 63`, `fonti/siti/strategie/feed.py:48`). Lambda assegnate a un nome: 3, già con
  `# noqa: E731` (`app/avvio_sistema.py:245-246`, `tests/dati/test_notizie.py:181`): sono gli unici `noqa` del
  progetto.
- **Errori**: 9 eccezioni proprie (`ErroreLLM`, `QuotaEsaurita`, `ContenutoAssente`, `NonAncoraDisponibile`,
  `GiaInCorso`, `ErroreAvvio`, `ErroreAggiornamento`, `ErroreTelegram`, `ImpostazioneNonValida`); 81 `except` in
  `src`, di cui **10 larghi**: 9 `except Exception` (`esecuzione/esecutore.py:153, 224, 236, 312, 339, 374`,
  `esecuzione/programmatore.py:76`, `telegram/bot.py:177`, `app/pannello.py:147`), tutti con un commento sul perché
  e, tranne il pannello, con un `log`; 1 `except BaseException` che rilancia (`llm/claude_code.py:105`); 2
  `contextlib.suppress(Exception)` (`telegram/bot.py:125, 140`, con commento). `except` con solo `pass`: 3
  (`app/pannello.py:84, 90` su `queue.Empty`, `dashboard/rotte.py:195` su `GiaInCorso`); con `return` di un valore
  vuoto: 23, quasi tutti `ValueError` di conversione. `raise` dentro un `except` senza `from`: 0.
- **Logging**: un logger per modulo solo nei 5 moduli che scrivono nei log (`log = logging.getLogger(__name__)` in
  4, `logging.getLogger("gradiens")` in `app/servizio.py:30`); 22 chiamate: 8 `info`, 10 `warning`, 4
  `exception`, nessun `debug` né `error`; **nessuna f-string** (16 con parametri `%s`, 6 testi fissi).
  `print` solo in `app/cli.py` (20, di cui 5 su `stderr`).
- **Type hint** (funzioni con ritorno e tutti i parametri annotati, `self` escluso): `src` 343 su 431 (79,6%):
  `dati` 87/89, `app` 68/73, `telegram` 31/34, `llm` 14/16, `esecuzione` 34/41, `fonti` 78/99, `dashboard` 31/79
  (le rotte FastAPI non dichiarano il ritorno: 44 delle 55 funzioni senza ritorno sono rotte o `__init__`).
  `Any`: **0**. Annotazioni con `dict`/`list` senza parametri: 35 (per esempio `llm/base.py:9` `schema: dict`,
  `dati/esecuzioni.py:20`). `tests`: 13 su 286.
- **Docstring**: moduli 58/64 in `src` (90,6%), 4/25 in `tests`; funzioni 161/431 in `src` (37%; pubbliche 130/325,
  40%), 20/286 in `tests`; classi 20/45. Stile: frase italiana, imperativa o descrittiva, spesso con il codice del
  PRD tra parentesi; nessuna sezione `Args:`/`Returns:`.
- **Commenti**: 321 in `src` (232 in linea, sempre con due spazi prima di `#`); 98 commenti e 106 docstring
  citano un codice del PRD (`ESE-12`, `WEB-04`...); 9 commenti citano un ADR; 3 commenti `shortcut:`
  (`dati/notizie.py:65`, `fonti/siti/__init__.py:60`, `fonti/youtube/__init__.py:108`); nessun `TODO`/`FIXME`.
- **Altro**: `open()` senza `encoding`: 1, in binario (`app/avvio_sistema.py:22`, corretto). `read_text`/`write_text`
  senza `encoding`: 0 in `src`, 3 in `tests` (`tests/llm/test_claude_code.py:40, 57, 68`). `shell=True`: 0. `zip`
  senza `strict`: 1 (`esecuzione/esecutore.py:202`). `datetime.utcnow`, `utcfromtimestamp`, `asyncio.get_event_loop`:
  0.

### M-4. `sqlite3` con il futuro valore predefinito di `autocommit` (15 nov 2026)

Metodo: script nella cartella temporanea, eseguito con il Python del progetto (`uv run --frozen python -I`,
Python 3.14.10, SQLite 3.53.1) e con il Python di sistema (3.13.5, SQLite 3.46.1), su database nuovi nella
stessa cartella temporanea. Risultati identici nelle due versioni:

| Connessione | `PRAGMA foreign_keys = ON`, poi lettura | Transazione aperta |
|---|---|---|
| `autocommit=LEGACY_TRANSACTION_CONTROL` (il valore predefinito di oggi) | **1** (attivo) | no |
| `autocommit=False` (il predefinito annunciato per il futuro) | **0** (il PRAGMA non ha effetto) | sì, sempre |
| `autocommit=False` più `isolation_level = None` | **0** | sì |
| `autocommit=True` | 1 | no |

Il PRAGMA `foreign_keys` non ha effetto dentro una transazione; con `autocommit=False` `sqlite3` ne tiene sempre una
aperta, e `isolation_level` non conta più.

### M-5. Claude Code, senza eseguirlo (15 nov 2026)

Metodo: `claude` non è stato lanciato (vietato in questa fase). Versione dal collegamento simbolico
(`readlink -f $(command -v claude)` → `~/.local/share/claude/versions/2.1.316`, unica cartella presente in
`versions/`). Opzioni, campi e file usati da Gradiens letti in `llm/claude_code.py` e `app/avvio_sistema.py`;
confrontati con le pagine ufficiali headless, cli-reference, setup e changelog lette con WebFetch (sezione 8).
Opzioni `--no-*` della CLI reference contate con `grep` sul testo della pagina: `--no-browser`, `--no-chrome`,
`--no-post`, `--no-session-persistence`.

### M-6. Segreti e categorie nei log veri (15 nov 2026)

Metodo: `grep` in sola lettura su `.gradiens/log/gradiens.log` e le tre copie ruotate (3.654 + 17.396 + 17.514 +
15.649 righe), **senza stampare** le righe trovate: conteggio delle stringhe con la forma di un token di bot Telegram
(`bot[0-9]{6,}:[A-Za-z0-9_-]{20,}`): 0 in tutti i file. Righe per livello e logger: 2.056 `INFO uvicorn.access`,
461 `INFO uvicorn.error`, 379 `ERROR telegram.ext.*`, 171 `INFO alembic.runtime.migration`, 165 `INFO telegram.ext.*`,
142 `INFO gradiens`, 73 `WARNING gradiens.telegram.bot`, 64 `INFO gradiens.telegram.bot`, 52 `INFO httpx` (tutte del 6
nov tra le 23:20:16 e le 23:27:02; host contati: `projectdiscovery.io` 35, `www.redhotcyber.com` 13,
`export.arxiv.org` 2, `www.youtube.com` 2; nessun host di Telegram), poche righe dell'esecutore.

## Che cosa non ho potuto verificare

- **I numeri di ruff**: ruff non è installato e non l'ho scaricato; tutte le cifre del punto 6 sono stime dai miei
  script. Comandi per i numeri veri: `uvx ruff check --statistics`, `uvx ruff format --check`, `uvx ruff format --diff`
  (rete e permesso dell'utente).
- **yt-dlp senza runtime JavaScript**: se oggi `live_status` e `media_type` arrivano completi; se Deno da PyPI
  (`yt-dlp[deno]`) funziona su Windows e Linux, e quanto pesa. Serve una prova vera (domanda 3).
- **Claude Code**: perché su questo PC c'è ancora la 2.1.316 (impostazioni di `~/.claude` non lette); se
  `claude --version` consuma quota (ipotesi: no); se in modalità bare un token di `claude setup-token` basta; quando
  `--bare` diventerà il predefinito (la pagina non lo dice; il changelog è stato letto solo in parte); i campi della
  risposta non documentati (`is_error`, `api_error_status`, i sotto-campi di `usage`).
- **Windows**: nessuna misura su Windows in questa fase (avvisi, pulizia delle cartelle temporanee con i database
  aperti, fine riga con ruff, percorso npm di Claude Code dopo un aggiornamento).
- **Versioni senza fonte letta**: l'ultima versione di htmx; correzioni di Python 3.14 più nuove di quelle note a uv
  0.13.7; il comando di uv per spostare un ambiente esistente a una correzione nuova di Python.
- **Fonti lette in parte**: le note di rilascio di FastAPI sul sito (ho usato quelle di GitHub), il changelog di
  Claude Code (prime 100.000 battute), la tabella di Dependabot (riga di `uv` parziale); se GitHub legge da solo
  `.git-blame-ignore-revs`; i limiti dei minuti di CI del piano GitHub dell'utente.
- **Comportamenti di librerie non documentati**: se `server.should_exit` di uvicorn e `yt_dlp.utils.DownloadError`
  sono API pubbliche; se le eccezioni di python-telegram-bot scritte da `log.exception` possono contenere l'indirizzo
  con il token (nei log veri non è mai successo, M-6).
- **Quando** Python renderà `autocommit=False` il predefinito: la documentazione di Python non dà una versione;
  "3.16" viene da SQLAlchemy ("as of this writing").
- **La stima dei ResourceWarning su altre macchine**: il numero varia tra esecuzioni (115 e 118) perché dipende dal
  garbage collector.
