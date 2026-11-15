# Fase 2: test e copertura (piano)

**Data**: 13 novembre 2026. **Stato**: bozza da discutere con l'utente.

Piano dei test di caratterizzazione e dei sospetti bug, costruito leggendo il codice e la suite e con 45 prove usa e
getta (registro in fondo, "Appendice"). Non modifica nessun file del progetto. Riferimenti `pacchetto/file.py:riga`
relativi a `src/gradiens/`; quelli dei test relativi alla radice. Le stime di sforzo (S = circa 1-2 ore, M = circa mezza
giornata, L = 1-2 giorni) sono stime, non misure.

## Riepilogo

**Copertura.** 86,8% per riga (3.462 righe su 3.987), misurata oggi su Linux: dati in
[dati/copertura-2026-11-13.md](dati/copertura-2026-11-13.md). Suite rilanciata: 182 test verdi in 16 secondi, verdi
anche con `TZ` impostato a `Pacific/Auckland`, `America/Los_Angeles` e `Asia/Kolkata` (P02). Per pacchetto: `dati` 98,1%,
`dashboard` 94,3%, `esecuzione` 92,0%, `fonti` 90,4%, `llm` 90,4%, `telegram` 78,2%, `app` 64,9%.

**Dove sono i buchi che contano** (e non sono interfaccia grafica o rami Windows):
1. i percorsi di errore dell'esecutore: valutazione fallita (`esecuzione/esecutore.py:312-315`), errore imprevisto o
   rigenerazione fallita di un sito (`:224-226`, `:236-237`), quota nel pre-filtro, negli argomenti e nelle proposte
   (`:337-338`, `:372-377`, `:391-392`);
2. `fonti/siti/strategie/wordpress.py:42-67` (strategia intera mai eseguita), `fonti/youtube/__init__.py` (`raccogli`
   e i rami di `_trascrizione`), `fonti/siti/rete.py` (5xx, nuovi tentativi, cache 304, tetto di pagine, gzip, pause);
3. `telegram/bot.py:107-143` (`avvia` e `ferma`: registrazione dei gestori e filtro sulla chat, mai eseguiti);
4. rotte delle Impostazioni mai provate: `rigenera_profilo` (decisione 21) e `tetto_arxiv` (decisione 9);
5. migrazioni: nessun test di fallimento a metà e nessuna prova con dati nella tabella `siti` (ADR 0011).

**Dove la copertura inganna**: `dati/database.py` è al 100% ma nessun test copre un fallimento; il programmatore esegue
copia e pulizia giornaliere in ogni test senza verificarle; l'esecutore passa `dal` alle fonti ma il finto lo ignora
(ESE-03, ACC-11 senza asserzione); le metriche si controllano solo in parte.

**I 10 test di caratterizzazione da scrivere per primi** (sezione 3): T-01 migrazione di `siti` su un database con dati;
T-02 pre-filtro dei paper a blocchi e tetto; T-03 i contatori di una fonte tornano; T-04 valutazione fallita; T-05 quota
nel pre-filtro; T-06 la finestra passata alle fonti; T-07 stato del sito registrato alla raccolta; T-08 gli stati dei
siti diversi da "ok" sono problemi in ogni punto; T-09 video sponsorizzato; T-10 WordPress `raccogli`.
In tutto **50 test proposti**: 23 prima delle modifiche già decise, 17 prima dei refactoring, 10 quando capita.

**Sospetti bug per la fase 4**: 39 nella bozza (S-01...S-39), **32 dopo la rilettura** (vedi "Esito della rilettura" qui sotto: S-16 tolto, sei riclassificati come comportamento voluto, previsto o scelta da confermare). **Provati**: 35 (in 3 la prova riguarda solo una parte: S-01,
S-11, S-29); **solo letti**: 4 (S-14, S-19, S-37, S-38). Il più importante resta il difetto dei video YouTube (S-01):
il meccanismo è dimostrato senza LLM, la causa no.

**Strumenti che mancano alla suite**: un orologio finto comune (nel codice ci sono sette riferimenti diversi a
"adesso"), un finto `claude` che salvi argomenti e tutto l'ambiente, un provider finto con latenza e registro di schema
e modello, `Application` finta di Telegram, isolamento di `HOME`, un costruttore di database "vecchi" con dati.

**Domande per l'utente**: 8 (sezione 5), la prima su `pytest-cov`.

---

## Esito della rilettura (13 novembre 2026)

La rilettura è stata **abbreviata** su richiesta dell'utente. Il revisore ha rilanciato quasi tutte le prove
dell'autore (P01, P03-P45, escluse P02 e P35) e ne ha scritte di sue: **30 sospetti riprovati e confermati**
nei fatti osservati. Le correzioni sono già applicate nel testo sotto; qui ciò che cambia rispetto ai numeri
del riepilogo.

- **Sospetti che non sono bug**: S-16 è tolto (comportamento corretto e già coperto da test). S-10, S-22 e
  S-35 sono comportamento previsto dai requisiti (`ESE-01`, RFC 9309, `ESE-03`); S-19 è probabilmente una
  protezione voluta; S-03 è una scelta da confermare con l'utente; S-17 è un disallineamento della
  documentazione. Alla fase 4 passano quindi **32 sospetti**, più S-03 come domanda.
- **Sospetti con la stessa radice**: S-02, S-04, S-05 e S-07 (il motivo dell'esecuzione fallita è il testo
  di un `ExceptionGroup`); S-04 è un caso particolare di S-05; la seconda metà di S-37 è l'innesco di S-11;
  S-06 e S-08 passano dallo stesso percorso.
- **S-01 (video YouTube)**: confermato che il sommario è la descrizione del video e che l'esclusione è
  definitiva (l'indirizzo entra nel registro delle viste). Sfumatura: se l'LLM mette un video sia tra i
  pertinenti sia tra gli sponsorizzati, il video non viene escluso (`esecutore.py:405`). La causa del
  verdetto dell'LLM resta non provata.
- **Piano dei test, correzioni**:
  - T-01 è in parte già scritto (`tests/dati/test_database.py:36-52` e `:70-88`); senza una migrazione
    0012 finta non fissa nulla di nuovo.
  - T-09 si sovrappone a `tests/esecuzione/test_esecutore.py:306`; la parte nuova è verificare sul registro
    delle viste che il video escluso non si riconsidera.
  - T-14 non si costruisce come descritto: la fixture `sito` sta in `tests/fonti/siti/conftest.py` e non si
    vede dagli altri pacchetti di test; va spostata in `tests/conftest.py`.
  - T-02 e T-05 richiedono un provider scritto apposta (il `Finto` non cede mai il controllo, quindi
    "partite insieme" non è osservabile); le candidate di T-02 vanno create con date diverse.
  - T-03 vale solo senza dirette e senza errori di fonte (vedi la scheda).
  - T-31: la parte su S-16 esiste già; i test delle rotte `tetto_arxiv` (decisione 9) e di rigenerazione
    del profilo (decisione 21) vanno nel gruppo A. Anche la parte di T-24 sull'avanzamento del pre-filtro
    va nel gruppo A (l'ADR 0010 lo cambia).
  - T-42 aggiunge solo la verifica che il programmatore chiama copia e pulizia; T-44 ha sforzo S, non M.
  - **Test mancanti per modifiche già decise**: che cosa `analizza` propone oggi come escluso (decisione
    22, traduzioni); un test che dica "nessuna chiamata LLM in `fonti/siti` durante le esecuzioni"
    (decisione 19 e `WEB-04`).
- **Conteggi**: le prove hanno 46 identificativi, con buchi nella numerazione (P14, P24-P26, P40). Le prove
  parziali sono S-01, S-11, S-20, S-29 e S-30.
- **Non riletto**: la nota su `pytest-cov` (1.7); gran parte delle tabelle 2.5-2.8; i test T-24…T-50 nel
  dettaglio; la tabella 3.5; quasi tutta la tabella 4.2; S-14, S-29, S-37, S-38; i rami Windows; le domande
  della sezione 5 (la 7, isolare `HOME` nei test, non dipende dall'utente).

## 1. Copertura

### 1.1 Sintesi dei dati misurati

La tabella completa per modulo, con le righe non coperte, è in
[dati/copertura-2026-11-13.md](dati/copertura-2026-11-13.md) (script
[dati/copertura.py.txt](dati/copertura.py.txt), solo libreria standard). Qui solo ciò che serve a decidere.

| Pacchetto | Righe | Coperte | % | Lettura |
|---|---|---|---|---|
| `dati` | 576 | 565 | 98,1 | quasi tutto, ma per riga: nessun fallimento di migrazione, nessun conflitto di scrittura |
| `dashboard` | 619 | 584 | 94,3 | mancano 6 rotte (sotto) |
| `esecuzione` | 514 | 473 | 92,0 | il buco è nei percorsi di errore dell'esecutore |
| `fonti` | 1.133 | 1.024 | 90,4 | WordPress, YouTube, rete dei siti |
| `llm` | 146 | 132 | 90,4 | `trova_eseguibile` mai eseguito |
| `telegram` | 275 | 215 | 78,2 | `avvia`, `ferma`, `cerca_chat`, `collega` |
| `app` | 721 | 468 | 64,9 | pannello (grafica), rami Windows, `cli.main`, `servizio.esegui` |

### 1.2 Moduli meno coperti: che cosa c'è nelle righe non coperte e se conta

| Modulo (%) | Righe non coperte: cosa sono | Conta? |
|---|---|---|
| `__main__.py` (0) | punto d'ingresso `python -m gradiens`; lo esercita il processo vero di `tests/app/test_avvio_reale.py`, che la misura non conta | no |
| `app/pannello.py` (27,5) | finestra Tkinter: costruzione, lettura dello stato, bottoni Accendi, Spegni, Aggiorna. Provata a mano (ADR 0009). Si prova solo `descrivi` (`tests/app/test_pannello.py`). Dentro c'è logica vera (`_controlla`, 22 righe: attese di accensione e spegnimento di 20 s) | in parte: la logica sì, la grafica no |
| `app/cli.py` (51) | `main` (argparse e smistamento, `:154-191`); `_riepilogo` (`:100-121`, il testo che `gradiens esegui` stampa alla fine, CLI-02); la fine del ciclo di `esegui` (`:143-151`: codice d'uscita e riepilogo; le righe 136-142 sono coperte) | sì: il resoconto della CLI non è verificato (P21) |
| `fonti/siti/strategie/wordpress.py` (51) | `raccogli` (`:42-67`) per intero: parametro `after`, 100 voci, `date_gmt`, "copre" | sì |
| `llm/__init__.py` (62,5) | `crea_provider` (`:9-12`): provider per nome, errore "Provider LLM sconosciuto"; i test passano una fabbrica a mano | in parte (LLM-01) |
| `telegram/bot.py` (73,8) | `:107-123` costruzione dell'`Application` con un `CommandHandler` per comando filtrato su `filters.Chat` (TG-02), `CallbackQueryHandler`, `TypeHandler`; `:125-134` pulizia e testi d'errore se l'avvio fallisce; `:139-143` `ferma` (updater, `app.stop`, `shutdown`, tutto dentro `suppress`); `:65-71` `cerca_chat` (sceglie l'ultimo `/start`); `:78-79` `collega`; `:171` e `:177-178` `invia_esecuzione` senza bot o con errore; `:186-187` errore di `invia_prova`; `:193-196` `_registra` | sì: TG-01, TG-02, ACC-07 |
| `fonti/youtube/__init__.py` (74,7) | `_info` e `risolvi_canale` (`:70-85`, chiamano yt-dlp: rete); `raccogli` (`:109-111`: finestra `>= dal` e `raise_for_status`); `_trascrizione` `:119-128` (video non disponibile, scelta della lingua, trascrizioni automatiche, testo vuoto) | sì, tranne `_info` e `risolvi_canale` (si sostituiscono) |
| `app/servizio.py` (76,4) | `:55` `should_exit` di `/api/spegni`; `:66` risposta di `/api/esegui`; `:84-91` ciclo di vita (bot, programmatore, spegnimento); `:123-141` `configura_log` ed `esegui` (esercitate solo nel processo vero) | in parte: il ciclo di vita sì |
| `app/avvio_sistema.py` (80,6) | rami Windows: `lancia_staccato` `:27-32`, attiva e disattiva `:89`, `:99`, `_stato_windows`, `_come_amministratore`, `_pythonw`, icone `:285-301`; Linux: `_linger` senza `loginctl` (`:154`), `systemctl` che fallisce (`:164`); `_esegui` (`:105-108`) ed `eseguibile` (`:369-372`), sempre sostituiti nei test | sì: sono i rami che si provano solo su Windows (1.3) |
| `app/aggiornamento.py` (81,1) | percorsi di errore di `gradiens aggiorna`: git o uv assenti, `fetch` fallito, nessun ramo remoto, spegnimento in ritardo, `merge` o `uv sync` falliti | medio: su Windows i file in uso sono il rischio dichiarato dal piano |
| `fonti/siti/strategie/raccolta.py` (84,2) | `Raccolta.errore`: tetto di pagine, "accesso bloccato", robots.txt che vieta | sì (P13) |
| `esecuzione/programmatore.py` (85,7) | `:54-55` copia giornaliera fallita; `:73-78` `gira`, il ciclo ogni 30 s | sì |
| `dashboard/rotte_impostazioni.py` (88,5) | rotte mai chiamate dai test: `escludi_percorso`, `rigenera_profilo` (`:217-224`), `scarta_proposta`, `tetto_arxiv`, `telegram_prova`, `telegram_cambia_chat`; rami di errore di `telegram_cerca` e `telegram_conferma` | sì (`rigenera_profilo`, `tetto_arxiv`: decisioni 21 e 9) |
| `fonti/siti/rete.py` (88,8) | `:72-74` ripiego cp1252; `:115` robots.txt 5xx o 429; `:123` tetto di pagine; `:135` troppi redirect; `:148` risposta 304; `:153` corpo oltre 15 MB; `:163` nuovo tentativo su 429 o 5xx; `:165-167` espulsione dalla cache; `:181` pausa tra richieste; `:187-190` gzip | sì (WEB-18, WEB-19) |
| `llm/base.py` (88,9) | i due `...` del `Protocol` | no |
| `dati/impostazioni.py` (90,5) | `salva_tetto_arxiv` (`:56-60`) e `__annotate__` | in parte |
| `telegram/messaggi.py` (91,3) | `:49` e `:85` la riga "Motivo:" (ESE-13 su Telegram); `:80-81`, `:88` rami di `stato` | sì (ESE-13) |
| `esecuzione/esecutore.py` (91,5) | `:98-102` `rete_disponibile` reale (la sostituisce `tests/conftest.py:20-25`); `:208` `BaseException` in `_raccogli`; `:214` "Nessuna fonte raggiungibile"; `:224-226` errore imprevisto di un sito; `:236-237` rigenerazione fallita; `:250` nessun interesse; `:312-315` valutazione fallita; `:337-338`, `:348`, `:350` argomenti (quota, voce non valida, assegnazione a un argomento esistente); `:372-377` proposta fallita; `:392` quota nel pre-filtro | sì: è il modulo più toccato dalle modifiche decise |
| `llm/claude_code.py` (91,5) | `:31-37` `trova_eseguibile` (`GRADIENS_CLAUDE`, `which`, `.cmd`); `:55` `is_error` che non è quota; `:109` uscita vuota | sì |
| `fonti/arxiv/__init__.py` (92,5) | `:30` voce senza data o senza id, `:33` indirizzo che non è di arXiv, `:52` nessuna categoria, `:57` pausa tra una pagina e l'altra | in parte (P22, P23) |

Gli altri moduli sono sopra il 93% e mancano righe di poco conto (vedi il file dei dati).

### 1.3 Le 52 funzioni mai eseguite, per significato

| Gruppo | N. | Funzioni | Conta? |
|---|---|---|---|
| Interfaccia grafica | 10 | `Pannello.__init__`, `_controlla`, `_imposta_passo`, `_leggi_sempre`, `_mostra`, `_premi_accendi`, `_premi_aggiorna` (+ `lavora`), `_premi_spegni`, `apri` | no per la grafica; `_controlla` ha logica |
| Rami Windows e wrapper di sistema in `avvio_sistema.py` | 8 | `_come_amministratore`, `_powershell`, `_pythonw`, `_sessione_senza_desktop`, `_stato_windows`, `_utente_windows`, più `_esegui` ed `eseguibile` (usate anche su Linux ma sempre sostituite) | sì: si provano senza Windows sostituendo `os` e `subprocess` (P19) |
| Avvio del processo | 6 | `cli.main`, `cli._riepilogo`, `configurazione.configurazione`, `servizio.ciclo_di_vita`, `configura_log`, `servizio.esegui` | in parte: le esercita il processo vero di `test_avvio_reale`, fuori misura; `_riepilogo` no (P21) |
| Rotte e salvataggi senza test | 7 | `escludi_percorso`, `rigenera_profilo`, `scarta_proposta`, `telegram_cambia_chat`, `telegram_prova`, `tetto_arxiv`, `dati.impostazioni.salva_tetto_arxiv` | sì |
| Percorsi di sistema sostituiti nei test | 4 | `esecutore.rete_disponibile`, `Programmatore.gira`, `claude_code.trova_eseguibile`, `llm.crea_provider` | sì, tutte e quattro |
| Fonti | 6 | `wordpress.raccogli`, `wordpress._reso`, `youtube._info`, `youtube.raccogli`, `youtube.risolvi_canale`, `Profilo.aggiungi_sezione` | sì, salvo `_info` e `risolvi_canale` (rete) |
| Bot | 2 | `BotGradiens.avvia` (26 righe), `BotGradiens._registra` | sì |
| Non codice | 9 | 7 funzioni `__annotate__` (artefatto delle annotazioni differite di Python 3.14) e i 2 `...` di `Provider.chiedi` e `Provider.pronto` | no |

Somma: 10 + 8 + 6 + 7 + 4 + 6 + 2 + 9 = 52. Le funzioni che contano sono quindi la maggior parte: tra 32 e 41 su 52, secondo come si contano i gruppi segnati "in parte" nella tabella sopra.

### 1.4 Quali test esercitano i moduli rischiosi e che cosa verificano davvero

Una riga coperta non è un comportamento verificato. Per ogni modulo rischioso: i file di test, ciò che le asserzioni
fissano e ciò che gira senza essere controllato.

| Modulo | File di test | Verificato da asserzioni | Eseguito ma non verificato, o non eseguito |
|---|---|---|---|
| `esecuzione/esecutore.py` | `tests/esecuzione/test_esecutore.py` (19 test) | flusso completo e contatori arXiv (`:80`); tetto (`:101`); quota esaurita dalla valutazione: `interrotta` e notizia non vista (`:108`); risposta LLM con id e punteggi sbagliati (`:122`); una sola esecuzione (`:134`); blocco di pre-filtro fallito (`:156`); spegnimento (`:176`); video, short, trascrizione assente, diretta, canale irraggiungibile, contenuto troncato (`:200`); siti: stato, guasti, rigenerazione dopo 3 (`:254`); interruttori paywall e sponsorizzati (`:306`); `al_termine` non allo spegnimento (`:325`); argomenti (`:349`, `:364`, `:374`); proposta (`:387`); provider non pronto (`:413`); attesa della rete (`:425`) | `dal` passato alle fonti (il finto `raccolta()` lo ignora, `:40`); i `token` (solo `> 0` e il nome del provider); `raccolta_s` (solo presente); l'avanzamento (solo `None` alla fine); le valutazioni intrecciate (il `Finto` non cede mai il controllo: P44 mostra che oggi regge con 60); `errori` per una valutazione fallita (non eseguito) |
| `esecuzione/programmatore.py` | `tests/esecuzione/test_programmatore.py` (10) | una volta al giorno, sospensione durante l'orario, recupero all'avvio, nessun recupero se è partita un'esecuzione, pausa, orario spostato, `GiaInCorso`, `prossima`, niente prima della configurazione | copia e pulizia del primo controllo del giorno (`:51-56`): girano in ogni test, nessuna asserzione; `gira` (`:72-78`); ora solare e legale; mezzanotte |
| `fonti/siti/rete.py` e raccolta | `tests/fonti/siti/test_siti.py` (16), `test_sicurezza.py` (3), `test_indirizzi_e_date.py` (7), `conftest.py` (finto `Sito`) | SSRF su indirizzi e redirect, robots.txt con rete assente, robots.txt che vieta l'API WordPress, ISO-8859-1, feed che risponde HTML, feed fermo, tetto di articoli, rigenerazione che conserva le modifiche, `completa` con paywall e senza testo | le pause: `rete_pulita` imposta `PAUSA = 0.0` in ogni test (`tests/fonti/siti/conftest.py:12-17`), quindi la pausa tra richieste e il Crawl-delay non sono mai verificati; nuovi tentativi, cache, gzip, tetto di pagine |
| `dati/database.py` e migrazioni | `tests/dati/test_database.py` (7 funzioni, 8 casi) | pertinenze salve dopo la 0009 (`:36`), chiavi esterne riaccese, configurazione già in uso, copia prima della migrazione e non su un database nuovo, copie giornaliere | fallimento a metà; migrazioni con dati nelle altre tabelle ricreate (0005, 0007, 0011); connessioni del pool con le chiavi esterne accese; conflitti di scrittura |
| `telegram/bot.py` | `tests/telegram/test_bot.py` (11) | messaggio di fine esecuzione (testo escapato, 3 per fonte, 2 frasi, metriche, bottoni), comandi chiamando i gestori a mano, cuore da Telegram (caso base e chat diversa), segreto nel `.env`, tutorial con funzioni sostituite, errori senza token (con un `Bot` finto), riprova a 5, 10, 20, 40 s, messaggio di prova, avviso del login, fonti con problemi | che i comandi siano registrati solo per la chat autorizzata (si chiamano i gestori, non l'`Application`); `avvia`, `ferma`; di `cerca_chat` e `collega` gira solo il ramo d'errore (`tests/telegram/test_bot.py:194`): restano scoperte le righe 65, 68-71 e 78-79 |
| `app/avvio_sistema.py` | `tests/app/test_avvio_sistema.py` (13) | testo del servizio systemd, registrazione e stato con `systemctl` finto, icone Linux, stringhe PowerShell con apostrofi, stato dall'XML di `schtasks` | tutte le funzioni Windows che toccano `ctypes`, `subprocess` o `schtasks`; confronto dei percorsi con le regole di Windows (su Linux `normcase` non fa niente, P19) |
| `app/servizio.py`, `app/cli.py`, `app/aggiornamento.py` | `test_servizio.py` (9), `test_cli.py` (4), `test_avvio_reale.py` (1), `test_aggiornamento.py` (4) | sicurezza (host, intestazioni, spegnimento da locale, 409), configurazione iniziale, avvia e spegni con un processo vero, aggiornamento con repository git veri e `uv` finto | effetto di `/api/spegni` (`server.should_exit`, `:55`), ciclo di vita, `esegui` della CLI, `_riepilogo` |
| `llm/claude_code.py` | `tests/llm/test_claude_code.py` (10) con un finto `claude` (script Python) | opzioni di isolamento, messaggio da stdin, chiave API tolta dall'ambiente, quota senza nuovo tentativo, un nuovo tentativo, timeout, cancellazione che uccide il processo, `pronto`, avviso del login | `trova_eseguibile`; `is_error` che non è quota; uscita vuota; l'ambiente completo (il finto salva solo `ANTHROPIC_API_KEY`); `cache_creation_input_tokens`; il numero di processi avviati al timeout |
| `fonti/youtube`, `fonti/arxiv` | `test_youtube.py` (8), `test_arxiv.py` (3) | `interpreta`, indirizzi accettati e rifiutati, short e dirette (con `_info` e `_trascrizione` sostituiti), trascrizione assente, al massimo 2 video alla volta; arXiv: normalizzazione, fonte, finestra | `youtube.raccogli`, rami di `_trascrizione`, risposte 200 non valide |

### 1.5 Requisiti del PRD senza copertura (o con copertura dichiarata ma non vera)

| Requisito | Situazione |
|---|---|
| `YT-02`, `ACC-11` (YouTube) | `verifica-accettazione.md` dice "test per arXiv, YouTube e siti", ma `youtube.raccogli` non è mai eseguita: nessun test sul filtro `>= dal` (`fonti/youtube/__init__.py:111`) |
| `ESE-03`, `ACC-11` (esecutore) | nessuna asserzione sul `dal` che l'esecutore passa alle fonti (T-06) |
| `YT-03` | lingua preferita (it, en) e trascrizioni automatiche: `_trascrizione` `:119-128` mai eseguita, si prova solo `TranscriptsDisabled` |
| `ESE-13` (su Telegram) | la riga "Motivo:" del messaggio e di `/stato` (`telegram/messaggi.py:49`, `:85`) mai eseguita |
| `ESE-11`, metriche coerenti | nessun test controlla che le chiavi siano tutte presenti e che i contatori tornino (T-03, T-30) |
| `ESE-12` | "le notizie rimaste si riprendono": provato solo con la quota (arXiv), non con lo spegnimento a metà valutazione (T-25) |
| `TG-02`, `ACC-07` | il filtro sulla chat dei comandi (`bot.py:112-116`) non è mai provato; solo il cuore (`:247`); `verifica-accettazione.md` dice "in parte" (T-32) |
| `WEB-18` | pause, Crawl-delay, nuovi tentativi su 5xx, cache 304: non verificati (T-46) |
| `WEB-19` | tetto di pagine: `rete.py:123` mai eseguita (T-16) |
| `WEB-04`, `WEB-05` | nessun test dice che le esecuzioni non chiamano un LLM per i siti (un controllo sugli import di `fonti/siti` basterebbe) |
| `WEB-02` (anteprima), `WEB-03` (sezioni modificabili), `WEB-25` (differenze), `LLM-02`, `LLM-03` | non implementati: `Profilo.aggiungi_sezione` mai eseguita, `profilo_precedente` mai letto, modelli senza interfaccia; non c'è nulla da coprire |
| `LLM-06` (orario in cui torna la quota) | nessun codice dedicato: il testo di Claude finisce nel motivo così com'è; nessun test sul contenuto del motivo |
| `INT-07`, `DUP-02`, `DUP-03` | comportamenti per assenza (niente rivalutazione, niente unione): nessun test |
| `CLI-02`, `CLI-04` | `gradiens esegui` completo non provato; `spegni` solo con il processo vero |
| `AMB-04`, `AMB-05`, `ACC-09`, `ACC-10` su Windows | ramo Windows mai eseguito in questa misura; prove manuali già indicate in `verifica-accettazione.md` |
| `ACC-14` | verifica manuale per definizione |

Nota: non esiste `tests/accettazione/` né `docs/test/`, previsti da `struttura.md` per il tester. La verifica dei 13
siti è `tests/fonti/siti/verifica_reale.py` (stampa su stdout, nessun report datato). Vedi domanda 6.

### 1.6 Limiti della misura

- Per riga, non per ramo: una riga con più condizioni vale come coperta se gira una volta (per esempio
  `esecutore.py:439`, `if not punteggi or max(...) < soglia`).
- Solo Linux (Debian 13, Python 3.14). Nessuna misura su Windows: i rami `os.name == "nt"` risultano coperti solo dove
  i test li simulano sostituendo `os`.
- I sottoprocessi non si contano: `servizio.esegui`, `configura_log`, `ciclo_di_vita`, `cli.main` e `__main__` sono
  esercitati da `test_avvio_reale.py` e risultano non coperti.
- Le migrazioni Alembic sono escluse dalla misura.
- La misura non dice se un'asserzione controlla l'esito (1.4).

### 1.7 Nota su `pytest-cov` (è una domanda per l'utente, non una decisione)

- **Cosa darebbe in più**: copertura per ramo (`--cov-branch`: vedrebbe i `if` con un solo lato provato, come
  `esecutore.py:439`); copertura dei sottoprocessi (con la configurazione di `coverage` per i processi figli: vedrebbe
  `servizio.esegui` e `__main__`); un rapporto in CI su Windows e su Linux con i dati uniti (`coverage combine`), che
  mostrerebbe i rami Windows davvero eseguiti dalla CI Windows; un controllo di non regressione facoltativo.
- **Cosa costa**: una dipendenza di sviluppo in `pyproject.toml` (`[dependency-groups] dev`) e il relativo
  aggiornamento di `uv.lock` (porta `coverage`); una riga in `.github/workflows/test.yml` (per esempio
  `uv run pytest --cov=gradiens --cov-branch --cov-report=term-missing`, più eventualmente il caricamento del file XML
  come allegato); nuovi file generati in radice (`.coverage`, `htmlcov/`) da mettere in `.gitignore` (PER-02).
  Tempo di esecuzione: oltre i 16 s attuali, non misurato (ipotesi: qualche secondo). **Non verificato**: la
  compatibilità di `coverage` con Python 3.14 (non l'ho installato).
- **Come si userebbe**: stessa riga su Linux e su Windows (PowerShell o terminale), `uv run pytest --cov=gradiens
  --cov-branch --cov-report=term-missing` per il rapporto a video e `--cov-report=html` per `htmlcov/index.html`.
- **Alternativa senza dipendenze**: tenere lo script in `dati/copertura.py.txt` (per riga, solo Linux).

---

## 2. Casi limite non coperti, per modulo rischioso

Colonna **Fam.**: F1 fusi e cambio dell'ora; F2 rete; F3 quota ed errori del provider; F4 dati vecchi e database;
F5 interruzioni; F6 input malformati; F7 percorsi e ambiente (Windows, systemd); F8 concorrenza. "Provato (Pnn)" rimanda
al registro in fondo; "letto" vuol dire solo lettura del codice. **Test** è il test esistente che fissa il caso.

### 2.1 Esecutore (`esecuzione/esecutore.py`)

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| Quota esaurita insieme a un altro errore nello stesso gruppo | F3 | `_tutti` (`:458-466`) usa `except*` solo per la quota; con un errore di altro tipo `_esegui` riceve un gruppo (`:148-155`) e registra `fallita`, motivo `" (2 sub-exceptions)"`. Provato (P03) | nessuno (solo la quota da sola, `tests/esecuzione/test_esecutore.py:108`) | medio | l'esecuzione risulta fallita invece che interrotta e il motivo non dice niente |
| Quota nel pre-filtro, negli argomenti, nelle proposte | F3 | `except QuotaEsaurita: raise` in `:391-392`, `:337-338`, `:372-373`; letto | nessuno (solo nella valutazione) | medio | l'ADR 0010 riscrive proprio il pre-filtro |
| Risposta LLM di forma inattesa (contenitore sbagliato) | F3 | provato (P28): pre-filtro `{}` o `"tutti"`: tutte scartate e segnate viste, esecuzione "completata"; `pertinenti: null` o `punteggi` non lista di oggetti: esecuzione fallita con "unhandled errors in a TaskGroup"; `riassunto: null` salvato come `"None"`; pertinenza 85,5 ignorata e notizia scartata e vista | solo elementi sbagliati dentro liste valide (`:122`) | medio | un lotto intero può sparire in silenzio; il cambio di forma delle risposte (6b-4, lotti) passa di qui |
| Id di interessi inesistenti, punteggi fuori scala, titolo `""` | F3 | ripuliti (`:434-437`, `:443-445`); letto | `:122` | basso | coperto |
| Valutazione fallita (rete o LLM) | F3 | `:312-315`: `errori` +1, non vista; alla prossima esecuzione la notizia passa di nuovo dal pre-filtro e dalla valutazione. Provato (P37) | nessuno (riga mai eseguita) | alto | costa quota ogni giorno (A6); 6b-12 e ADR 0010 toccano questo punto |
| Timeout e nuovo tentativo | F3 | vedi 2.7 (P38) | parziale | medio | |
| Valutazioni intrecciate sulla stessa sessione | F8 | oggi regge (P44: 60 paper con latenza finta, tutti salvati); la sicurezza dipende dal non avere `await` tra modifica e commit (A2) | nessuno: il `Finto` non cede mai il controllo | medio | un refactoring che inserisce un `await` romperebbe tutto in silenzio |
| `ferma` durante l'esecuzione | F5 | `CancelledError`, stato `interrotta`, motivo `SPENTO`, metriche nel `finally` (`:150-167`); letto | solo con un provider bloccato dalla prima chiamata (`:176`) | medio | non è provato che il lavoro già salvato resti (ESE-12) |
| `termina` fallisce (database occupato) | F5 | `avanzamento = None` non viene eseguito (`:162-164`): ogni `avvia` successiva dà `GiaInCorso` fino al riavvio. Provato con un blocco di scrittura vero (P17, P39) | nessuno | medio | |
| Eccezione in `_salva` o `conta_token` | F5 | fuori dal `try` di `elabora` (`:318-319`): tutta l'esecuzione fallita, motivo opaco. Provato (P18, P39) | nessuno | medio | |
| `al_termine` che solleva | F5 | l'eccezione sfugge dal `finally` (`:166-167`); `BotGradiens.invia_esecuzione` le assorbe tutte; letto | `:325` (caso normale) | basso | |
| `avvia` chiamata fuori dal ciclo (thread) | F8 | `asyncio.create_task` fallirebbe (`:127`); letto | nessuno | basso | contratto "una esecuzione alla volta" (ESE-02) |
| Esecuzione manuale e programmata insieme | F8 | `GiaInCorso` in `avvia` (`:122-123`); letto | `:134` e `tests/esecuzione/test_programmatore.py:111` | basso | coperto nello stesso processo; tra processi vedi 2.6 |
| Rete assente all'avvio | F2 | `_attendi_rete` (`:169-177`): fino a 300 s, poi fallita con motivo | `:425` (con `rete_disponibile` sostituita) | basso | `rete_disponibile` reale (`:96-102`) mai eseguita |
| Rete che cade dopo l'attesa, o portale captive (DNS sì, HTTP no) | F2 | `rete_disponibile` guarda solo il DNS (`:96-102`): con soli siti tutti irraggiungibili l'esecuzione finisce "completata" a 0 notizie e i siti accumulano guasti (`:213-214`, `:224-226`); letto | nessuno | medio | catena con la rigenerazione del profilo (S-34) |
| Errore imprevisto di un sito, profilo JSON illeggibile | F5 | errore imprevisto: "errore di lettura" e guasto (`:224-226`); JSON illeggibile: la fonte risulta "non raggiungibile" (`:221` fuori dal `try`); letto | nessuno | medio | ADR 0011 cambia `_raccogli_sito` |
| Rigenerazione che fallisce | F5 | guasti non azzerati, nuova analisi a ogni esecuzione con guasto (`:236-237`); letto | nessuno | medio | decisione 21 |
| `dal = adesso() - finestra` | F1 | UTC senza fuso (`:256`); il valore non è verificato da nessun test | nessuno | medio | ADR 0011 aggiunge per i siti un punto di ripartenza ("coperto fino a"), sempre dentro la finestra; `dal` resta per arXiv e YouTube |
| Date solo-giorno e finestra | F1 | `nella_finestra` (`fonti/siti/date.py:90-94`) | `tests/fonti/siti/test_indirizzi_e_date.py:44` | basso | coperto |
| Esecuzioni vecchie senza metriche complete | F4 | `riepilogo` usa `.get` (`dati/esecuzioni.py:53-69`); la CLI no (P21) | dashboard e `dati` sì; CLI no | basso | |
| Notizie senza `esecuzione_id` (4 nel database vero il 13 novembre) | F4 | restano fuori da `in_evidenza(esecuzione_id=...)` e dagli argomenti (`:328`); letto | nessuno | basso | dati storici |
| `soglia` 0 con punteggio 0 | F6 | salvata senza pertinenze, contata come mostrata, mai visibile (P06) | nessuno | basso | |
| Doppioni tra fonti con indirizzi diversi | F6 | si tiene la prima per indirizzo (`:264`); letto | nessuno | basso | DUP-01 |
| Video senza trascrizione, dirette, trascrizione lunga | F6 | `ContenutoAssente`, `NonAncoraDisponibile`, troncamento (`:304-311`, `:422-423`) | `:200` | basso | coperto |

### 2.2 Programmatore (`esecuzione/programmatore.py`)

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| Passaggio all'ora solare, orario tra 02:00 e 02:59 | F1 | l'orologio locale senza fuso torna indietro e `ultimo < scadenza <= adesso` (`:63`) è vera due volte: **2 esecuzioni** nello stesso giorno. Provato (P01) | nessuno | basso | una volta l'anno e solo con orario in quell'ora (il predefinito è 07:00); il docstring (`:4-6`) dice che i cambi d'ora sono gestiti |
| Passaggio all'ora legale, orario inesistente | F1 | 1 esecuzione al primo controllo dopo le 03:00. Provato (P01) | nessuno | basso | |
| Date UTC senza fuso e recupero all'avvio | F1 | `scadenza.astimezone(UTC)` (`:61`) interpreta il datetime senza fuso come ora locale | `:72`; la suite passa con tre fusi diversi (P02) | basso | coperto |
| PC sospeso o servizio spento mentre passa l'orario | F1, F5 | la scadenza si calcola solo sulla data di `adesso` (`:58`, `:63`): se si sveglia il giorno dopo prima dell'orario, l'esecuzione del giorno prima è persa; con orario 23:30 e sospensione 23:10-00:40: 0 esecuzioni; avvio alle 00:40: nessun recupero. Provato (P01) | `:58` (sospeso nello stesso giorno: sì) | medio | con finestra a 3 giorni, una pausa di 4 giorni perde notizie |
| Primo controllo del giorno: copia e pulizia | F5 | `copia_giornaliera` e `cancella_scadute` (`:51-56`) girano in ogni test del programmatore senza asserzioni; letto | le due funzioni hanno test diretti (`tests/dati/test_database.py:91`, `tests/dati/test_notizie.py:90`); manca solo la prova che il programmatore le chiama | medio | ESE-09 "almeno una volta al giorno" |
| Copia giornaliera fallita | F5 | l'errore va nel log, la pulizia continua (`:54-55`); letto | nessuno | basso | |
| `controlla` che solleva | F5 | `_ultimo_controllo` non cambia (`:64`), `gira` registra e riprova dopo 30 s (`:72-78`); letto | nessuno (`gira` mai eseguita) | basso | |
| Orario nel database non valido | F4 | `time.fromisoformat` solleverebbe a ogni controllo (`:27`); la validazione sta in `dati/impostazioni.py:39-42`; letto | la validazione sì | basso | |
| Pausa cambiata da Telegram mentre `controlla` legge | F8 | ognuno apre la sua sessione; letto | `tests/telegram/test_bot.py:94` (senza concorrenza) | basso | |

### 2.3 Rete dei siti e raccolta (`fonti/siti`)

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| robots.txt irraggiungibile (rete) | F2 | `ERRORE_RETE`, non ricordato (`rete.py:106-110`) | `tests/fonti/siti/test_sicurezza.py:34` | basso | coperto (ConnectError) |
| robots.txt in timeout | F2 | `ERRORE_RETE`. Provato (P13) | nessuno | basso | |
| robots.txt con 503 o 429 | F2 | tutto vietato per un'ora (`:114-116`): `VIETATA`, guasto "robots.txt ora vieta". Provato (P13) | nessuno (`:115` mai eseguita) | medio | un guasto passeggero del sito blocca la raccolta del giorno |
| Timeout, DNS, risposta a metà | F2 | `ReadTimeout` o `RemoteProtocolError`: 2 tentativi e `ERRORE_RETE`, il testo parziale non si usa (P13); il timeout è per operazione: un server che manda un byte ogni 0,3 s con `TIMEOUT` 0,5 s tiene la lettura per 3,9 s (P13b) | nessuno | basso | lettura non limitata nel tempo totale |
| Rete che torna dopo l'avvio | F2 | l'esecutore aspetta; i siti si rileggono appena torna (`rete.py:106-110`) | `test_sicurezza.py:34` | basso | coperto |
| Nuovi tentativi su 429 o 5xx, risposta 304, gzip, corpo oltre 15 MB, espulsione dalla cache, troppi redirect | F2, F6 | letto: `:163`, `:148`, `:187-190`, `:153`, `:165-167`, `:135`; provato solo il corpo da 18 MB (P11: `ERRORE_RETE`) | nessuno | medio | WEB-18; la proposta 6a-10 (cache su disco) tocca questo codice |
| Pause per host e Crawl-delay | F8 | `_attendi_turno` (`:171-181`): 1 s e massimo 10 s; nessun test (`PAUSA = 0`) | nessuno | medio | |
| robots.txt che reindirizza alla rete di casa | F2 | seguito: la richiesta a `http://192.168.1.1/robots.txt` parte. Provato (P43) | `test_sicurezza.py:17` (solo i redirect delle pagine) | medio | SSRF residua (C4) |
| Tetto di pagine | F2 | `leggi` restituisce `TETTO` (`:122-123`); con 5 pagine e 12 voci senza data: 5 richieste, 8 candidate restano incerte, nessun guasto, nota "Raggiunto il tetto di 5 pagine". Provato (P33) | nessuno (`:123` mai eseguita) | alto | ADR 0011: "copertura parziale" nasce da qui |
| Date incerte: una pagina per candidata, anche già vista | F6 | `_date_incerte` (`siti/__init__.py:142-156`) legge 12 pagine per 12 voci senza data (P33); la fonte non conosce il registro delle viste | nessuno | alto | 6a-3 |
| Feed che copre ma è in ritardo | F6 | `r.copre and trovate` ferma la cascata (`:107-108`): la sitemap non si chiede, l'articolo di 2 ore fa si perde, stato "ok". Provato (P29) | nessuno | alto | 6a-5 |
| Voci di un feed su altri domini | F6 | tutte accettate, fonte = dominio del profilo (`feed.py:99-103`). Provato (P29b) | nessuno | medio | decisione 18 |
| Feed di una sezione | F6 | scartato se meno della metà delle voci è nel perimetro o linkata dalla pagina (`feed.py:70-71`); letto | `tests/fonti/siti/test_siti.py:88` (parziale) | medio | 6a-4 |
| Feed non XML o che risponde HTML | F6 | `None` e guasto (`feed.py:22-27`, `:93-95`) | `test_siti.py:159` | basso | coperto |
| Date assenti, future | F6 | assenti: `adesso()` e `data_incerta` (`feed.py:36-41`), coperto (`test_siti.py:190`); **future accettate** con data certa. Provato (P12) | assenti sì; future no | medio | decisione 16 (rifiuto delle date future) |
| Codifiche | F6 | ISO-8859-1 coperto; ripiego cp1252 (`rete.py:72-74`) no | `test_siti.py:64`, `:81` | basso | |
| URL senza protocollo, spazi, virgolette, rete privata | F6 | `normalizza` (`indirizzi.py:33-56`) | `test_indirizzi_e_date.py:10`, `test_sicurezza.py:10` | basso | coperto; `http://` diventa `https://` (un sito solo http non si legge) |
| Sitemap enorme | F6 | `interpreta` è sincrona nel ciclo di eventi: 50.000 voci (5,3 MB) 2,0 s, 200.000 (21 MB) 8,6 s; oltre 15 MB `ERRORE_RETE`. Provato (P11) | nessuno | basso | blocca bot e dashboard per qualche secondo |
| WordPress API | F6 | `raccogli` (`wordpress.py:42-67`): `after = dal - 1 giorno`, 100 voci, `date_gmt`; mai eseguita | nessuno | alto | 6a-5, 6a-7, ADR 0011 cambiano il significato di `dal` |
| `completa`: errore di rete | F2 | diventa "errore di estrazione" (`estrazione.py:56-57`) e l'esecutore segna la notizia vista per sempre. Provato (P42) | nessuno | medio | un guasto passeggero perde l'articolo (S-30) |
| `completa`: data fuori finestra | F1 | la data della pagina si prende senza controllare la finestra (`estrazione.py:61-62`). Provato (P41) | nessuno | basso | |
| Profilo con campi mancanti, `null` o sconosciuti | F4 | `Profilo.da_dict` completa con i valori di base, ignora i campi sconosciuti; `feed: null` passa (P27) | `test_siti.py:218` (solo andata e ritorno) | medio | ADR 0011 e 6a aggiungono campi |
| Un sito solleva un'eccezione imprevista | F5 | vedi 2.1 | nessuno | medio | |

### 2.4 Migrazioni e database (`dati/database.py`, `dati/migrazioni`)

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| Migrazione su un database con dati | F4 | con la 0012 finta di prova su una copia del database vero (13 siti, 145 notizie, 227 pertinenze, 1.447 viste): conteggi invariati, `foreign_key_check` vuoto, 0,01 s, copia `migrazione.db` creata. Provato (P15) | `tests/dati/test_database.py:36` (0009), `:56` (0011) | alto | ADR 0011: una `add_column` su `siti` è un `ALTER TABLE ADD COLUMN`, senza ricreazione |
| Migrazione fallita a metà | F4, F5 | senza ricreazioni (solo DDL) non c'è nessun rollback: restano le tabelle create e il secondo avvio rifallisce con "already exists" (P15b); con una ricreazione resta la parte DDL prima del primo DML (`_alembic_tmp_<tabella>`, P15c); `alembic_version` resta alla vecchia | nessuno | alto | nessun ripristino automatico dalla copia; con systemd il servizio riparte ogni 30 s e rifallisce |
| Copia di sicurezza che fallisce | F4 | l'eccezione non è intercettata: il servizio non parte (`database.py:41-42`); succede solo quando il database non è all'ultima versione, cioè al primo avvio dopo un aggiornamento con una migrazione; letto | nessuno | basso | disco pieno, OneDrive; probabilmente una protezione voluta: meglio non partire che migrare senza copia |
| Chiavi esterne | F4 | accese da un listener su ogni connessione (`:21-25`), spente durante `migra` e riaccese (`:37`, `:48`) | `:36` (dopo `migra`) | medio | nessun `foreign_key_check` dopo la migrazione |
| Conflitto di scrittura | F8 | un'altra connessione tiene il blocco: dopo 5 s `database is locked`; nell'esecutore due attese di 5 s (10 s con `termina`), il ciclo di eventi fermo per tutto il tempo, esecuzione `fallita`/`in_corso`. Provato con un blocco vero (P39) | nessuno | medio | blocca bot, programmatore, altre richieste |
| Cancellazione dopo 7 giorni: confine, date future | F1, F4 | `pubblicata_il < adesso - 7 giorni` (`dati/notizie.py:104-111`): esattamente 7 giorni resta; una data futura non scade finché non passano 7 giorni dopo; letto | `tests/dati/test_notizie.py:90` (caso base) | medio | il confine si prova sostituendo `adesso` nel modulo (`monkeypatch.setattr(notizie, "adesso", ...)`): non serve un orologio finto comune |
| Notizie senza `esecuzione_id` | F4 | `SET NULL`; letto | nessuno | basso | |
| Argomenti e pertinenze orfani | F4 | cascate del database; letto | `test_notizie.py:147`, `tests/dati/test_argomenti.py:61` | basso | |
| `notizie_viste` cresce senza limite | F4 | 1.447 righe in 5 giorni; nessuna pulizia | nessuno | basso | |
| Database in una cartella sincronizzata (OneDrive) | F7 | nessuna gestione dei blocchi del client di sincronizzazione; `copia_di_sicurezza` fa `unlink` delle copie vecchie senza intercettare `PermissionError` dentro `migra`; letto | nessuno | medio | Windows; non verificato |

### 2.5 Bot Telegram (`telegram/bot.py`)

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| Due `avvia()` insieme (ciclo `gira` e "Messaggio di prova") | F8 | due `Application` in polling, `ferma()` ne ferma una. Provato con `Application` finta (P09) | nessuno | basso | due poller con lo stesso token danno conflitto a Telegram (ipotesi su Telegram, non provato) |
| Comandi solo dalla chat autorizzata | F6 | i 7 comandi rispondono dalla chat configurata e nessuno da un'altra, verificato con i gestori veri di python-telegram-bot senza rete (P10) | nessuno per i comandi (solo `_cuore`, `:134`) | medio | ACC-07 "in parte" |
| Cuore: stato del bottone diverso dal database | F8 | il bottone inverte il valore del database, non quello mostrato: dopo un cuore messo dalla dashboard, premere il bottone "senza cuore" risponde "Cuore tolto". Provato (P09b) | nessuno | basso | |
| Cuore da un messaggio senza tastiera | F6 | `AttributeError` dopo aver già cambiato il database, nessuna risposta a Telegram. Provato (P09b) | nessuno | basso | |
| Telegram irraggiungibile all'avvio | F2 | `errore` e nessuna `Application`, pulizia dei client (`:123-134`); riprova 5, 10, 20, 40, 60 s | `:215` (`avvia` sostituita) | medio | il ramo di errore non è mai eseguito |
| Token nel testo degli errori | F6 | `InvalidToken` gestito; per gli altri `TelegramError` il testo originale va in `errore` e nel log (`:130-131`); non provato che la libreria non lo includa | `:194` (solo `InvalidToken`) | medio | PER-04: resta da provare con la libreria |
| `ferma()` | F5 | `suppress(Exception)` attorno a updater, stop e shutdown (`:139-143`) | nessuno | basso | |
| Messaggio di fine esecuzione lungo | F6 | il motivo non si accorcia: con un motivo da 5.151 caratteri il messaggio è di 5.421 (P45); Telegram accetta fino a 4.096 caratteri (limite citato in `messaggi.py:13`); l'errore va solo nel log (`:177-178`) | nessuno | basso | ESE-13: proprio la segnalazione di un guasto può non arrivare |
| Chiamate a Telegram senza bot attivo | F2 | `invia_esecuzione` ritorna in silenzio (`:170-171`) | nessuno | basso | |
| Pausa e riprendi insieme a un'altra pausa dalla dashboard | F8 | ultimo che scrive vince; letto | nessuno | basso | |
| `cerca_chat` e `collega` | F6 | scelgono l'ultimo `/start` e impostano i comandi (`:61-81`); eseguito solo il ramo d'errore (`tests/telegram/test_bot.py:194`), scoperte le righe 65, 68-71, 78-79 | nessuno per il caso buono | basso | |

### 2.6 `avvio_sistema`, servizio e CLI

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| Percorsi con spazi e caratteri non ASCII | F7 | `unita_systemd`, `voce_desktop`, `script_windows` gestiscono `%`, virgolette, apostrofi; il file del servizio si scrive in UTF-8, lo script Windows va in base64 UTF-16; letto | `tests/app/test_avvio_sistema.py:52`, `:87`, `:139` (non ASCII no) | basso | |
| `claude.cmd` e il percorso dell'eseguibile nativo | F7 | su Windows `.cmd` e `.bat` diventano `<cartella>/node_modules/@anthropic-ai/claude-code/bin/claude.exe` (`avvio_sistema.py:35-40`); se il pacchetto npm cambia la struttura, `ErroreLLM` "Eseguibile non trovato"; letto | `:12` (solo il testo del percorso) | medio | provato a mano il 12 nov su Windows 11, non in automatico |
| Limite della riga di comando (32.767 caratteri) | F7 | prompt di sistema e schema passano come argomenti (`claude_code.py:85-92`): argomenti con 100 nomi da 200 caratteri 21.903; 100 nomi di sole virgolette 41.903; pre-filtro con 30 interessi da 500+500 caratteri 32.140. Provato (P08) | nessuno | basso | database vero: 3 interessi, 181 caratteri |
| `pythonw.exe` e flussi `None` | F7 | `configura_log` e `cli.main` gestiscono `sys.stdout is None`; `_pythonw` mai eseguita; letto | nessuno | basso | |
| `schtasks` e la sua codifica | F7 | `_esegui` legge in UTF-8 con `errors="replace"` (`:106`): con un'uscita in cp850 o cp1252 un percorso con accenti diventa "un'altra cartella" (provato nella decodifica, P35; **che `schtasks` scriva in quella codifica non è verificato**) | nessuno | medio | segnale globale su ogni pagina |
| UAC e sessione 0 | F7 | `_come_amministratore` si prova senza Windows (P19): codice 1 e sessione 0 danno `ErroreAvvio` con lo script | nessuno | medio | |
| Confronto dei percorsi come Windows | F7 | su Linux `normcase` non fa niente: maiuscole diverse danno "un'altra cartella"; con `ntpath` nessun problema (P19) | `:104` (percorsi identici) | basso | la CI Windows lo prova solo con stringhe uguali |
| systemd: PATH del servizio e `GRADIENS_CLAUDE` | F7 | il servizio scrive solo `Environment=GRADIENS_CLAUDE`; `GRADIENS_CLAUDE` nel `.env` è ignorato (P20); su questa macchina `claude` è un ELF nativo, nessuna dipendenza da `node` | `:52` | medio | |
| `loginctl enable-linger` | F7 | l'esito non si controlla (`:166-167`); lo stato lo segnala | `:60`, `:72` | basso | |
| Secondo servizio avviato mentre il primo è acceso | F8 | `crea_app` esegue `migra` e `segna_interrotte` prima di scoprire la porta occupata: l'esecuzione `in_corso` del primo diventa `interrotta`. Provato per questa parte (P16); bot doppio e recupero: letto | nessuno | medio | |
| Servizio occupato (blocco del database, sitemap grande) | F8 | `leggi_stato` ha timeout 2 s (`cli.py:20`): un ciclo bloccato per più di 2 s fa credere a `gradiens avvia` che il servizio sia spento e ne lancia un secondo; il pannello mostra "spento"; letto, collegato a P11 e P39 | nessuno | medio | |
| `/api/spegni` | F5 | `server.should_exit = True` (`servizio.py:55`); con un server finto il valore diventa vero, senza server risponde 200 senza effetto (P34) | `test_servizio.py:48` (solo il codice 200 e 403) | basso | |
| Spegnimento con SIGTERM (systemd) | F5 | stessa strada di `should_exit`; letto | nessuno | basso | |
| `gradiens esegui` | F2 | `httpx.post` iniziale senza `try` (`cli.py:128`): un timeout dà una traccia; il ciclo gira (righe 136-142 coperte), restano scoperte le righe 143-151 e `_riepilogo` | `tests/app/test_cli.py:26` | basso | |
| Configurazione iniziale richiesta quando mancano i dati | F4 | blocco di tutte le pagine che usano `pagina`; `POST /esecuzione` e `/api/esegui` partono comunque (letto), il programmatore no | `tests/dashboard/test_configurazione.py` (5), `test_segnali.py:28` | basso | coperto per le pagine |
| `test_avvio_reale` legge il `.env` vero | F7 | il processo figlio legge `RADICE/.env`; solo `GRADIENS_PORTA` e `GRADIENS_CARTELLA_DATI` sono forzati; letto (non ho aperto il `.env`) | `test_avvio_reale.py:1` | basso | un `GRADIENS_HOST` nel `.env` cambierebbe l'indirizzo del processo di prova |

### 2.7 `llm/claude_code.py`

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| "rate limit" e "quota" trattati come quota esaurita | F3 | `PAROLE_QUOTA` (`:26`, `:53`): "API Error: rate limit exceeded" e "would exceed your quota of tokens per minute" danno `QuotaEsaurita` e interrompono l'esecuzione; "Overloaded" e un 500 no. Provato (P36) | `tests/llm/test_claude_code.py` (solo 429 con "usage limit reached") | medio | S-03 |
| Timeout e nuovo tentativo | F3 | ogni `ErroreLLM` si riprova una volta (`:81-83`): con il timeout si avviano 2 processi (provato con timeout 1 s: 2 processi in 2,0 s; con 300 s: fino a 600 s e quota doppia). P38 | `test_timeout` senza controllare il numero di processi | medio | |
| JSON valido ma non un oggetto (`null`, `[]`, `42`) | F3 | `AttributeError` (non `ErroreLLM`) in `interpreta` (`:51`); nel pre-filtro l'esecuzione fallisce con motivo opaco. Provato (P04) | nessuno | basso | |
| `is_error` che non è quota; uscita vuota | F3 | `ErroreLLM` (`:55`, `:109`); letto | nessuno | basso | |
| Contabilità dei token | F3 | `ingresso = input + cache_creation + cache_read` (`:60`) | solo `input` + `cache_read` | basso | 6b-1 cambia la contabilità |
| `trova_eseguibile` | F7 | `GRADIENS_CLAUDE`, poi `which`, poi conversione `.cmd`, poi controllo di esistenza (`:29-37`); mai eseguita | nessuno | medio | 6b-3 e Windows |
| Ambiente passato al processo | F7 | tutto l'ambiente meno `ANTHROPIC_API_KEY` e `ANTHROPIC_AUTH_TOKEN` (`:40-42`) | solo la chiave API | basso | |
| Cancellazione | F5 | il processo viene ucciso (`:105-107`) | `test_chiamata_cancellata_chiude_claude` | basso | coperto |

### 2.8 YouTube e arXiv

| Caso | Fam. | Cosa fa oggi | Test | Rischio | Perché |
|---|---|---|---|---|---|
| Video: sommario e pre-filtro | F6 | il sommario è la descrizione del feed (`youtube/__init__.py:99`); il pre-filtro riceve titolo e descrizione fino a 1.500 caratteri; con `escludi_sponsorizzati` attivo (predefinito) un video segnalato non torna più (P07) | nessuno | alto | S-01 |
| `raccogli` di YouTube | F6, F2 | finestra `>= dal`, `raise_for_status`; una pagina HTML con 200 dà lista vuota e stato "ok" (P22); mai eseguita | nessuno | medio | |
| Trascrizione: lingue e automatiche | F6 | `find_transcript(("it", "en"))`, poi la prima disponibile; "video non disponibile"; testo vuoto (`:119-128`) | solo `TranscriptsDisabled` (`tests/fonti/test_youtube.py:67`) | medio | YT-03 |
| Dirette e anteprime | F6 | `NonAncoraDisponibile`, ripassano dal pre-filtro a ogni esecuzione | `tests/esecuzione/test_esecutore.py:200` | basso | coperto |
| IP bloccato da YouTube | F2 | errori non intercettati: `errori` +1 e si riprova; letto | nessuno | basso | |
| arXiv: risposta 200 vuota o non Atom | F6 | lista vuota, nessuna eccezione, stato "ok" (P22) | nessuno | medio | portale captive o pagina d'errore: 0 paper senza avviso |
| arXiv: paginazione | F6 | una voce scartata nella pagina da 200 fa credere che sia l'ultima (`arxiv/__init__.py:65`): 199 paper, nessuna seconda richiesta (P23) | nessuno | basso | |
| arXiv: errori HTTP | F2 | `raise_for_status` e la fonte diventa "non raggiungibile" (`esecutore.py:203-206`) | stesso codice del canale rotto (`:200`) | basso | |

### 2.9 Dove stanno le otto famiglie

| Famiglia | Righe di sezione 2 |
|---|---|
| F1 fusi e ora | 2.1 (`dal`, date solo-giorno), 2.2 (intera), 2.3 (date future, `completa`), 2.4 (cancellazione) |
| F2 rete | 2.1 (attesa, captive), 2.3 (robots, timeout, tetto), 2.5 (Telegram), 2.6 (CLI), 2.8 |
| F3 quota ed errori LLM | 2.1 (quota mista, forme inattese, valutazione fallita), 2.7 |
| F4 dati vecchi e database | 2.1 (metriche, `esecuzione_id`), 2.3 (profili), 2.4 (intera), 2.6 (configurazione) |
| F5 interruzioni | 2.1 (`ferma`, `termina`, `_salva`), 2.2, 2.4, 2.6 (spegnimento) |
| F6 input malformati | 2.3, 2.8, 2.1 (risposte LLM) |
| F7 Windows e ambiente | 2.6, 2.7 (`trova_eseguibile`), 2.4 (OneDrive) |
| F8 concorrenza | 2.1 (intrecciate), 2.4 (blocco), 2.5, 2.6 (due servizi) |

---

## 3. Piano dei test di caratterizzazione

Un test di caratterizzazione fissa il comportamento di oggi, anche se discutibile, prima di toccare il codice. Dove il
comportamento sembra sbagliato il test lo fissa lo stesso e rimanda al sospetto (S-nn, sezione 4): quando il bug si
corregge, il test si ribalta insieme alla correzione. Nome nello stile dei test esistenti (italiano, frase). I test di
unità vanno nei file di chi possiede il modulo (`struttura.md`): qui sono indicati i file, la scrittura va concordata.

**Come sono ordinati**: per rischio, cioè probabilità che il codice venga toccato presto × danno se il comportamento
cambia senza accorgersene. **Fixture e finti esistenti** che i test riusano: `sessioni`, `candidata`, `raccolta`,
`risponditore`, `esegui` in `tests/esecuzione/test_esecutore.py:21-77`; `Finto` in `llm/finto.py`; fixture `sito`
(classe `Sito` con `MockTransport`) e `rete_pulita` in `tests/fonti/siti/conftest.py`; `conf`, `client`, `client_nuovo`
in `tests/conftest.py`; `finto` (script `claude`) in `tests/llm/test_claude_code.py:36-44`; `systemd` in
`tests/app/test_avvio_sistema.py:26-49`; `ambiente`, `bot_di`, `aggiornamento`, `Risposte` in
`tests/telegram/test_bot.py:22-76`; `programmatore`, `ora`, `EsecutoreFinto` in `tests/esecuzione/test_programmatore.py`.
Con `--import-mode=importlib` i file di test non si importano a vicenda: gli strumenti comuni nuovi vanno come fixture
in un `conftest.py` (come già fa `sito`).

**Windows e Linux** (la CI gira su entrambi, `.github/workflows/test.yml`): i finti sono script Python lanciati con
`sys.executable`; niente percorsi scritti a mano (`tmp_path`, `pathlib`), niente asserzioni sui permessi (`chmod`) su
Windows (come fa già `tests/telegram/test_bot.py:154`); il sistema operativo si simula sostituendo `os` del modulo con
un `SimpleNamespace(name="nt", path=ntpath)` o `name="posix"` (come `tests/app/test_avvio_sistema.py:14`, aggiungendo
`path`) e, per `Popen`, le costanti `DETACHED_PROCESS` e simili con `monkeypatch.setattr(subprocess, ..., raising=False)`;
l'orologio, la rete e il provider sono sempre finti; nessun test aspetta un tempo fisso se può aspettare un evento.

### 3.1 Gruppo A: prima delle modifiche già decise (ADR 0010, ADR 0011, decisioni 13, 18, 21, 22) e delle proposte 6a-3, 6a-4, 6a-5, che sono ancora bozze

Attenzione: 6a-3, 6a-4, 6a-5 e il rifiuto delle date future (ciò che resta di 6a-2 dopo la decisione 16) **non sono decise**: i test che dipendono solo da loro (T-17, T-18, T-20, T-21) si scrivono quando la proposta viene accettata.

| Codice e nome | Cosa fissa | Come si costruisce | Perché prima | File | Sforzo |
|---|---|---|---|---|---|
| **T-01** `test_la_migrazione_dei_siti_non_perde_dati_e_si_ripete_senza_errori` | su un database alla versione 0011 con 13 siti (profili JSON), notizie, pertinenze, viste: dopo `migra` i conteggi sono uguali, `PRAGMA foreign_key_check` è vuoto, esiste una sola copia `-migrazione.db`, e una seconda `migra` non ne fa un'altra (`dati/database.py:30-49`) | un costruttore di database "vecchio" (strumento 8) con `command.upgrade(config, "0011")` come in `tests/dati/test_database.py:36`, poi una 0012 finta in una cartella temporanea con `monkeypatch.setattr(database, "CARTELLA_MIGRAZIONI", ...)` (la tecnica di P15). Quando la 0012 vera esiste, si passa alla vera | ADR 0011: migrazione della tabella `siti`; "da provare su una copia del database vero" (qui diventa un test ripetibile, senza usare il database vero) | `tests/dati/test_database.py` | M |
| **T-02** `test_il_prefiltro_dei_paper_manda_tutto_a_blocchi_e_poi_si_applica_il_tetto` | con 65 paper e tetto 5: chiamate di pre-filtro = `ceil(65 / BLOCCO_PREFILTRO)` (3 con blocchi da 30) partite insieme, ogni paper inviato una volta, valutati i 5 più recenti tra i promossi, `oltre_tetto` = promossi - 5, tutti i non valutati nel registro delle viste (`esecutore.py:274-284`, `:381-416`) | `esegui` con `raccolta(...)` e un `risponditore` che promuove tutto; si leggono i messaggi in `finto.chiamate`; 65 candidate si creano in un attimo, senza ridurre il blocco | ADR 0010 cambia numero, ordine e momento delle chiamate: questo test dice cosa deve restare uguale (il tetto sceglie i più recenti, gli scartati entrano nelle viste) e cosa cambia apposta (T-11 e T-03 lo completano) | `tests/esecuzione/test_esecutore.py` | S |
| **T-03** `test_i_contatori_di_una_fonte_tornano` | `esaminate` = `scartate_prefiltro` + `escluse` + `oltre_tetto` + `senza_contenuto` + `scartate_valutazione` + `mostrate` + notizie con `errori` per notizia. **Vale solo senza dirette e senza errori di fonte o di sito**: le dirette (`NonAncoraDisponibile`, `esecutore.py:310-311`) non entrano in nessun contatore (riprovato nella rilettura: 2 esaminate, somma degli esiti 1, errori 0) e `errori` mescola gli errori di notizia con quelli di fonte e di sito (`:205`, `:230`). Il test fissa l'invariante con queste eccezioni dichiarate; provato (P05): caso normale e blocco fallito | `esegui` con quattro scenari (tetto, sponsorizzate e paywall, blocco fallito, valutazione fallita); l'invariante si scrive una volta in una funzione | l'ADR 0010 promette che `oltre_tetto` e `scartate_prefiltro` "continuano a tornare" (ESE-11): presuppone un'identità che oggi vale solo con le eccezioni dette; nessun test lo dice | `tests/esecuzione/test_esecutore.py` | S |
| **T-04** `test_una_valutazione_fallita_non_segna_vista_la_notizia_e_la_rimanda_al_prefiltro` | `elabora` (`:312-315`): `errori` +1, la notizia non è vista, le altre si salvano; alla seconda esecuzione la notizia ripassa dal pre-filtro e dalla valutazione (P37: 2 chiamate di ciascuno) | `Finto` che solleva `ErroreLLM` e poi `RuntimeError` per `SCHEMA_VALUTAZIONE`; due esecuzioni di fila con `asyncio.run` come `tests/esecuzione/test_esecutore.py:374` | riga mai eseguita; ADR 0010 e 6b-12 (rivalutazioni, nuovi tentativi) la toccano | `tests/esecuzione/test_esecutore.py` | S |
| **T-05** `test_quota_esaurita_nel_prefiltro_interrompe_e_non_segna_viste_le_notizie` | `except QuotaEsaurita: raise` (`:391-392`): esecuzione `interrotta`, motivo con "Quota", nessuna notizia nel registro, blocchi fratelli cancellati | `BLOCCO_PREFILTRO` a 1, un provider che solleva la quota alla prima chiamata e attende (`asyncio.sleep(0)`) nelle altre, così l'ordine dei compiti è deterministico | l'ADR 0010 sostituisce i blocchi paralleli con giri in sequenza: la semantica della quota non deve cambiare | `tests/esecuzione/test_esecutore.py` | M |
| **T-06** `test_l_esecutore_passa_a_ogni_fonte_la_finestra_di_raccolta` | `dal = adesso - finestra_giorni` (`:256`) arriva a `raccogli` di arXiv, YouTube e siti, con una tolleranza di pochi secondi; cambiando `finestra_giorni` cambia `dal` | fonti finte che registrano `dal` (come `raccolta()` ma senza ignorarlo); `esegui(..., finestra_giorni=3)` | ESE-03 e ACC-11 non hanno asserzioni; ADR 0011 aggiunge per i siti "coperto fino a" (sempre dentro la finestra; `dal` resta per arXiv e YouTube) e prevede casi in cui si riparte dalla finestra intera | `tests/esecuzione/test_esecutore.py` | S |
| **T-07** `test_lo_stato_del_sito_si_registra_alla_raccolta_anche_se_l_esecuzione_e_interrotta` | `_raccogli_sito` (`:217-242`) fa commit di stato, dettaglio e guasti subito; se poi la valutazione dà quota esaurita, il sito ha già lo stato nuovo e le notizie non sono viste | come `tests/esecuzione/test_esecutore.py:254` con una quota nella valutazione; lettura di `Sito` | l'ADR 0011 salva "coperto fino a" a fine esecuzione e non alla raccolta: questo test fissa il contrasto e impedisce di spostare per errore anche lo stato e i guasti | `tests/esecuzione/test_esecutore.py` | S |
| **T-08** `test_gli_stati_dei_siti_diversi_da_ok_e_nessun_articolo_nuovo_sono_problemi_ovunque` | per ogni stato (ok, nessun articolo nuovo, accesso bloccato, richiede JavaScript, nessuna strategia funzionante, errore di lettura, profilo rigenerato, non raggiungibile) dice dove compare come problema: `dashboard/segnali.py:63`, `telegram/messaggi.py:63`, `app/cli.py:114`, `dati/esecuzioni.py:67` (ordine), `templates/impostazioni/siti.html:12` e `resoconto.html:75` | `client` con un `Sito` per stato e `registra_esito`; chiamate dirette a `messaggi.fine_esecuzione` e `cli._riepilogo` con metriche costruite a mano | ADR 0011 aggiunge lo stato "copertura parziale": l'elenco `STATI_BUONI` è definito una volta (`dati/esecuzioni.py:44`) e importato negli altri punti; l'unica copia scritta a mano è nel modello Jinja `siti.html:12`; chi lo aggiunge deve scegliere in modo consapevole se è un problema | nuovo `tests/dashboard/test_stati_dei_siti.py` | M |
| **T-09** `test_un_video_segnalato_come_sponsorizzato_esce_per_sempre_e_il_prefiltro_vede_solo_titolo_e_descrizione` | il messaggio al pre-filtro per un video è `{id, titolo, sommario[:1500]}` con la descrizione del feed; il prompt di sistema è identico per ogni tipo (`prompt.py:24-34`); con l'interruttore attivo il video segnalato non si salva, ha `escluse` 1 e non si riconsidera (2ª esecuzione: `esaminate` 0); con l'interruttore spento lo stesso video è mostrato. Provato (P07) | fonti finte con `youtube.interpreta` su un feed con una descrizione che nomina uno sponsor; `Finto` che segnala chi contiene "sponsorizzat"; due esecuzioni | decisione 13 (S-01): chi corregge il difetto deve sapere che oggi la regola vale per tutti i tipi e che l'esclusione è definitiva | `tests/esecuzione/test_esecutore.py` | S |
| **T-10** `test_wordpress_raccogli_usa_la_data_gmt_la_finestra_e_il_limite_di_100_voci` | `wordpress.py:42-67`: indirizzo con `after = dal - 1 giorno`, `per_page=100`, `date_gmt` UTC, voci senza data scartate, `copre` solo con meno di 100 voci, JSON non valido e HTML come guasto, robots.txt che vieta | `sito` con risposte JSON; due fixture nuove in `tests/fonti/siti/fixture/` | strategia intera mai eseguita; 6a-5, 6a-7 e ADR 0011 cambiano il significato di `dal` e della cascata | `tests/fonti/siti/test_siti.py` | M |
| **T-11** `test_un_blocco_di_prefiltro_mescola_paper_siti_e_video` | un solo giro contiene tipi diversi (`:274-275`, `:384`) e `escluse` e `scartate_prefiltro` si attribuiscono al tipo giusto (`:409-413`) | `esegui` con fonti finte arxiv, youtube e siti e `Finto` che registra i messaggi | ADR 0010: "siti e video continuano a passare tutti dal pre-filtro" mentre i paper si separano | `tests/esecuzione/test_esecutore.py` | S |
| **T-12** `test_un_errore_imprevisto_nella_raccolta_di_un_sito_non_ferma_le_altre_fonti` | `:224-226`: stato "errore di lettura", guasto, `errori` +1; profilo JSON illeggibile: la fonte è "non raggiungibile" (`:221`) | `siti` finto che solleva `RuntimeError`; un sito con `profilo = "{"` scritto a mano nel database | ADR 0011 cambia questa funzione | `tests/esecuzione/test_esecutore.py` | S |
| **T-13** `test_la_rigenerazione_fallita_non_azzera_i_guasti` | `:236-237`: il log, i guasti restano 3 e alla prossima esecuzione si ritenta | `rigenera` finto che solleva, come in `:254` | decisione 21 e ADR 0011 | `tests/esecuzione/test_esecutore.py` | S |
| **T-14** `test_la_rigenerazione_sostituisce_il_profilo_anche_se_non_trova_nessuna_strategia` | via `POST /impostazioni/siti/{id}/rigenera` (`rotte_impostazioni.py:217-224`, mai chiamata) e via rigenerazione automatica: `profilo.strategie == []`, diagnosi "nessuna strategia funzionante", il vecchio in `profilo_precedente`, stato "profilo rigenerato". Provato per `rigenera` con 404 e con rete assente (P32) | `client` con `Sito` e `httpx.MockTransport` sostituito a `httpx.AsyncClient` nella rotta con `monkeypatch`; per l'automatica, `rigenera` reale con `Sito` che risponde 404 | decisione 21: "si tiene il profilo vecchio e la rigenerazione sostituisce solo se trova almeno una strategia" | `tests/dashboard/test_rotte.py` e `tests/esecuzione/test_esecutore.py` | M |
| **T-15** `test_il_profilo_salvato_con_campi_mancanti_o_sconosciuti_si_legge` | `Profilo.da_dict`: campi mancanti ai valori di base, sconosciuti ignorati, `feed: null` accettato; ritorno di `come_dict()` (P27) | dizionari scritti a mano | ADR 0011 e 6a aggiungono campi: serve poter tornare indietro e andare avanti | `tests/fonti/siti/test_siti.py` | S |
| **T-16** `test_il_tetto_di_pagine_ferma_le_letture_senza_essere_un_guasto` | `rete.leggi` dà `TETTO` (`:122-123`); con `pagine_massime=5` e 12 voci senza data: 5 richieste, 8 candidate incerte, `guasto` falso, nota "Raggiunto il tetto di 5 pagine" (P33) | `sito` con feed e 12 pagine | ADR 0011: "copertura parziale" nasce dal tetto | `tests/fonti/siti/test_siti.py` | S |
| **T-17** `test_le_pagine_degli_articoli_con_data_incerta_si_leggono_una_per_una` | 12 voci senza data = 12 pagine lette, senza sapere se l'indirizzo è già visto (`siti/__init__.py:142-156`; P33) | come T-16 senza tetto, contando `s.richieste` | 6a-3 introduce il parametro `viste`: il test dice quante letture oggi e quante dopo | `tests/fonti/siti/test_siti.py` | S |
| **T-18** `test_un_feed_in_ritardo_ferma_la_cascata` | feed con una voce nella finestra e una più vecchia (copre) + sitemap con un articolo di 2 ore fa: candidate solo del feed, sitemap non richiesta, stato "ok", nessun guasto (`siti/__init__.py:107-108`; P29) | `sito` con feed e sitemap con date relative a `datetime.now` | 6a-5 | `tests/fonti/siti/test_siti.py` | S |
| **T-19** `test_le_voci_di_un_feed_su_altri_domini_sono_accettate` | tutte le voci passano, `fonte` = dominio del profilo (`feed.py:99-103`, `:30-43`; P29b) | feed con tre domini (altro dominio, sottodominio substack, proprio) | decisione 18 le toglie salvo siti collegati attivi | `tests/fonti/siti/test_siti.py` | S |
| **T-20** `test_un_feed_di_sezione_si_scarta_se_meno_della_meta_delle_voci_e_linkata` | `feed.py:69-71`: 15 voci su 50 nel perimetro o linkate scartano il feed (caso ACN) | `analizza` con una pagina di sezione e un feed da 50 voci; il file `acn_feed.xml` esistente si può estendere | 6a-4 | `tests/fonti/siti/test_siti.py` | S |
| **T-21** `test_una_data_futura_in_un_feed_o_in_una_sitemap_e_accettata` | una voce datata tra 400 giorni diventa candidata con data certa, stato "ok" (P12); idem sitemap | feed e sitemap con date relative a `datetime.now` | decisione 16: "resta il rifiuto delle date future" | `tests/fonti/siti/test_siti.py` | S |
| **T-22** `test_youtube_raccogli_tiene_la_finestra_e_non_nasconde_una_risposta_non_valida` | `youtube.py:106-111`: voci prima di `dal` escluse; 404 e 500 sollevano; una pagina HTML con 200 dà lista vuota (P22) | `httpx.MockTransport` come `tests/fonti/test_arxiv.py:46` | decisione 13: chi tocca YouTube trova la fonte senza rete di sicurezza | `tests/fonti/test_youtube.py` | S |
| **T-23** `test_la_trascrizione_sceglie_la_lingua_accetta_le_automatiche_e_distingue_gli_errori` | `_trascrizione` (`youtube.py:114-128`): l'ordine delle lingue (italiano a mano, italiano automatico, inglese a mano, inglese automatico) lo decide `find_transcript` della libreria, non Gradiens; di Gradiens si possono fissare il ripiego sulla prima disponibile, "video non disponibile" e il testo vuoto | `YouTubeTranscriptApi` finta (si sostituisce il nome, come `tests/fonti/test_youtube.py:72`): prova solo il ripiego e gli errori | YT-03 senza test; la correzione del difetto dei video li coinvolge | `tests/fonti/test_youtube.py` | S |

### 3.2 Gruppo B: prima dei refactoring (esecutore, `rotte_impostazioni`, bot, `avvio_sistema`, `claude_code`)

| Codice e nome | Cosa fissa | Come si costruisce | Perché prima | File | Sforzo |
|---|---|---|---|---|---|
| **T-24** `test_ordine_delle_fasi_e_avanzamento_con_valutazioni_intrecciate` | la sequenza `raccolta`, `pre-filtro`, `valutazione`, `argomenti`, `proposte` letta da `esecutore.avanzamento` a ogni chiamata del provider; `fatti` e `totale`; `avanzamento` `None` alla fine; con 60 paper e latenza finta tutte le notizie si salvano (P44) | `Finto` con latenza (`asyncio.sleep(0.001)`), strumento 3 | `_pipeline` (80 righe) è il candidato a essere spezzata; la sessione condivisa regge solo senza `await` tra modifica e commit | `tests/esecuzione/test_esecutore.py` | M |
| **T-25** `test_lo_spegnimento_a_meta_valutazione_conserva_le_notizie_gia_salvate` | `ferma()` dopo N notizie salvate: restano salvate, le altre non sono viste, stato `interrotta`, motivo `SPENTO`, metriche scritte, nessun messaggio (ESE-12) | provider che dopo la terza chiamata attende un `asyncio.Event`; `ferma()` | non è provato che il lavoro fatto resti; ADR 0010 e refactoring toccano il `finally` | `tests/esecuzione/test_esecutore.py` | M |
| **T-26** `test_un_errore_di_database_nel_salvataggio_o_alla_chiusura_lascia_l_esecuzione_cosi` | `_salva` che solleva: `fallita`, motivo "unhandled errors in a TaskGroup" (P18); `termina` che solleva: `avanzamento` resta, `avvia` dà `GiaInCorso`, stato `in_corso` (P17, P39) | `monkeypatch` su `Esecutore._salva` e su `modulo.esecuzioni.termina`; per il caso reale, una seconda connessione `sqlite3` con `BEGIN IMMEDIATE` (come P39, 10 s: va marcato lento o si accorcia il timeout del database) | S-06, S-07, S-08: oggi nessun test dice cosa succede | `tests/esecuzione/test_esecutore.py` | M |
| **T-27** `test_quota_insieme_ad_un_altro_errore_nello_stesso_gruppo` | due blocchi, uno quota e uno `RuntimeError`: `fallita` con motivo " (2 sub-exceptions)" (P03); la sola quota resta `interrotta` | `BLOCCO_PREFILTRO` a 1 | `_tutti` è il punto che un refactoring "ripulirebbe" | `tests/esecuzione/test_esecutore.py` | S |
| **T-28** `test_risposte_llm_di_forma_inattesa` | tabella di P28: `{}`, `pertinenti` `None` o stringa, `punteggi` non lista di oggetti, `riassunto` `None`, pertinenza 85,5, pertinenza `true` | `pytest.mark.parametrize` su un `risponditore` che altera una sola risposta | 6b-4 (lotti) e 6b-5 cambiano forma e schema delle risposte | `tests/esecuzione/test_esecutore.py` | M |
| **T-29** `test_riga_di_comando_e_ambiente_di_claude_code_e_forme_della_risposta` | argomenti completi e in ordine (`claude_code.py:85-92`, `OPZIONI_ISOLAMENTO`), ambiente completo senza le due chiavi, `GRADIENS_CLAUDE`; `interpreta` con tutti i campi di `usage`, `is_error` non quota (`:55`), uscita vuota (`:109`), `null`, `[]` (P04), "rate limit" (P36), timeout con 2 processi (P38) | estendere il `FINTO` di `tests/llm/test_claude_code.py:11-33` (strumento 2): salva `sys.argv` e `dict(os.environ)` e risponde con una coda di modalità | 6b-1, 6b-3, 6b-5, 6b-6 cambiano opzioni, ambiente e contabilità dei token | `tests/llm/test_claude_code.py` | M |
| **T-30** `test_le_chiavi_delle_metriche_e_chi_le_legge` | l'elenco delle chiavi di `Contatori` e di `token` salvate (`esecutore.py:53-89`, `:157-161`); `dati.esecuzioni.riepilogo`, `cli._riepilogo` (oggi `KeyError` con metriche vecchie, P21), `telegram.messaggi.riga_metriche` e il resoconto leggono sia il formato di oggi sia quello vecchio | una metrica di oggi (ricavata da una vera esecuzione del finto) e una vecchia scritta a mano | 6b-1 è "solo aggiunte": il test lo verifica; chi toglie o rinomina una chiave rompe il test | nuovo `tests/dati/test_esecuzioni.py` | M |
| **T-31** `test_le_rotte_delle_impostazioni_non_provate` | `tetto_arxiv` (1-500), `escludi_percorso`, `scarta_proposta`, `telegram_prova` (esito e errore), `telegram_cambia_chat`; `GET /impostazioni/esecuzione` con `HX-Current-URL` = `/configurazione`: 500 (P30); `POST /impostazioni/esecuzione` con soli `soglia` e `finestra_giorni` mette in pausa e spegne le esclusioni (P31) | `client` e `HTMX` come `tests/dashboard/test_rotte.py`; `TestClient(..., raise_server_exceptions=False)` per il 500 | refactoring di `rotte_impostazioni` (344 righe, sezioni e passi mescolati); decisione 9 passa dal tetto | `tests/dashboard/test_rotte.py` | M |
| **T-32** `test_il_bot_registra_i_gestori_solo_per_la_chat_autorizzata` | `avvia` (`bot.py:106-134`): sette `CommandHandler` filtrati, un `CallbackQueryHandler`, un `TypeHandler` in gruppo -1; con `check_update` i 7 comandi rispondono dalla chat autorizzata e nessuno da un'altra (P10) | `Application` finta (strumento 4) con `monkeypatch.setattr(telegram, "Application", ...)`; `Bot` con `_bot_user` impostato; `Message` e `Update` veri | TG-02 e ACC-07; refactoring del bot | `tests/telegram/test_bot.py` | M |
| **T-33** `test_avvio_del_bot_errori_ferma_e_avvii_concorrenti` | `TelegramError` in `initialize`: `errore` impostato, client chiusi, `_app None`; `InvalidToken`: testo senza token; `ferma` ferma updater, app, shutdown; due `avvia` insieme: 2 `Application` create e 1 sola fermata (P09); `_riprova` non riprova se `errore` contiene "token" | `Application` finta con `initialize` che attende | S-12; la riconnessione dopo l'accensione è la parte più provata a mano | `tests/telegram/test_bot.py` | M |
| **T-34** `test_cuore_da_telegram_casi_limite` | cuore invertito rispetto al database (P09b), `reply_markup` `None`, notizia cancellata che tiene il bottone (`_tastiera`, `:267`, `:271`) | `bot_di`, `domanda` come `tests/telegram/test_bot.py:121-130` | S-13 | `tests/telegram/test_bot.py` | S |
| **T-35** `test_i_messaggi_di_telegram_con_motivo_lungo_stato_e_senza_esecuzioni` | `fine_esecuzione` con `motivo` (`messaggi.py:49`), `stato` con `motivo` (`:85`), nessuna esecuzione (`:88`); lunghezza del messaggio con un motivo da 5.000 caratteri (P45: 5.421) | `ambiente` e `esecuzioni.termina(..., motivo=...)` | ESE-13; S-39 | `tests/telegram/test_bot.py` | S |
| **T-36** `test_cerca_chat_e_collega_con_un_bot_finto` | `cerca_chat` sceglie l'ultimo `/start`; `collega` imposta i comandi e manda il benvenuto (`bot.py:61-81`) | `Bot` finto come `BotRifiutato` in `:197-205`, con `get_updates` e `set_my_commands` | TG-01 | `tests/telegram/test_bot.py` | S |
| **T-37** `test_il_ramo_windows_di_avvio_sistema_senza_windows` | `lancia_staccato` con le costanti Windows e il ripiego senza `CREATE_BREAKAWAY_FROM_JOB` (`:27-32`); `_come_amministratore` (base64 UTF-16 ricostruibile, codice 1, sessione 0: P19b); `_stato_windows` (comando `schtasks /Query /TN Gradiens /XML`); `_utente_windows`; `_pythonw`; `crea_icone` e `togli_icone` su Windows; `eseguibile()` (`~/.local/bin`) | sostituire `avvio_sistema.os` con `SimpleNamespace(name="nt", environ=..., path=ntpath)`; `_sessione_senza_desktop` e `_esegui` finti; `subprocess.Popen` finto che registra i flag | refactoring di `avvio_sistema` (372 righe, due sistemi nello stesso file); oggi 8 funzioni mai eseguite | `tests/app/test_avvio_sistema.py` | M |
| **T-38** `test_lo_stato_dell_attivita_confronta_i_percorsi_come_windows_e_legge_l_output_di_schtasks` | maiuscole diverse nei percorsi equivalgono (P19: oggi su Linux no); un'uscita in cp850 o cp1252 con un nome con accenti dà "un'altra cartella" (P35: da capire se è voluto) | sostituire `os` con uno che ha `path=ntpath`; stringhe codificate a mano | S-29; sulla CI Windows lo stesso test prova la lettura vera | `tests/app/test_avvio_sistema.py` | S |
| **T-39** `test_linux_percorsi_con_spazi_non_ascii_e_comandi_che_falliscono` | `unita_systemd` e `voce_desktop` con percorsi non ASCII e `$`; `_attiva_linux` con `systemctl` che fallisce (`ErroreAvvio`, `:164`); `_linger` senza `loginctl` (`:154`) | fixture `systemd` esistente, con codici d'uscita diversi da 0 | refactoring di `avvio_sistema` | `tests/app/test_avvio_sistema.py` | S |
| **T-40** `test_il_servizio_ha_un_ciclo_di_vita_un_secondo_servizio_e_lo_spegnimento` | `with TestClient(app)` esegue il ciclo di vita: prima `bot.avvia`, poi i due compiti; all'uscita `esecutore.ferma` e `bot.ferma` (`servizio.py:84-91`); un secondo `crea_app` sullo stesso database segna interrotta l'esecuzione `in_corso` (P16); `/api/spegni` imposta `should_exit` (P34) | bot e programmatore finti in `app.state`; `Esecutore` con `avanzamento` finto; server finto | S-11; il ciclo di vita è nel processo vero e non conta nella misura | `tests/app/test_servizio.py` | M |

### 3.3 Gruppo C: quando capita

| Codice e nome | Cosa fissa | Come si costruisce | Perché | File | Sforzo |
|---|---|---|---|---|---|
| **T-41** `test_il_programmatore_con_ora_solare_ora_legale_e_mezzanotte` | ora solare con orario 02:30: 2 esecuzioni; ora legale: 1; sospeso 23:10-00:40 con orario 23:30: 0; avvio alle 00:40: 0 (P01); `gira` registra l'eccezione e continua | orologio finto già iniettabile (`Programmatore(adesso=...)`), sequenze come `p01_programmatore.py` | S-09, S-10; nessuna modifica prevista | `tests/esecuzione/test_programmatore.py` | S |
| **T-42** `test_la_prima_verifica_del_giorno_copia_e_cancella` | al primo controllo e al cambio di giorno: una copia `-giornaliera.db` e le notizie scadute sparite; un `OSError` nella copia non ferma la pulizia | `sessioni` con una notizia vecchia e `crea_motore` su `tmp_path` | ESE-09 "almeno una volta al giorno" non è verificato | `tests/esecuzione/test_programmatore.py` | S |
| **T-43** `test_una_migrazione_fallita_a_meta_lascia_il_database_cosi` | 0012 finta che crea una tabella e solleva: restano le tabelle, `alembic_version` vecchia, il secondo `migra` fallisce con "already exists" (P15b); con una ricreazione resta `_alembic_tmp_*` (P15c) | stessa tecnica di T-01 | S-18; si ribalta quando si decide una strategia di ripristino | `tests/dati/test_database.py` | S |
| **T-44** `test_la_cancellazione_ai_confini_dei_7_giorni` | esattamente 7 giorni resta, 7 giorni e un secondo no; cuore tolto dopo i 7 giorni sparisce alla pulizia; data futura; argomento vuoto | orologio finto comune (strumento 1) che sostituisce `adesso` nei sette punti | ESE-09 e ACC-05 solo nel caso base | `tests/dati/test_notizie.py` | M |
| **T-45** `test_le_chiavi_esterne_sono_accese_su_ogni_connessione` | ogni connessione del pool ha `foreign_keys = 1`; eliminare un interesse cancella le pertinenze; dopo `migra` `foreign_key_check` è vuoto | più connessioni da `motore.connect()` | requisito di correttezza (B4i) | `tests/dati/test_database.py` | S |
| **T-46** `test_la_rete_dei_siti_errori_nuovi_tentativi_pause_e_cache` | 5xx e 429 con un secondo tentativo, 304 dalla cache, gzip, corpo oltre 15 MB, espulsione dalla cache, troppi redirect; robots.txt 503 e 429 vietano (P13), 403 permette; pause per host e Crawl-delay con `time.monotonic` e `asyncio.sleep` finti | `Sito` con `httpx.Response`; fixture `rete_pulita` senza `PAUSA = 0` per i test delle pause | 6a-10 (cache su disco); WEB-18 | nuovo `tests/fonti/siti/test_rete.py` | M |
| **T-47** `test_una_sitemap_grande_e_una_risposta_oltre_il_limite` | 20.000 voci si interpretano entro un tempo ragionevole (P11: 2,0 s per 50.000); una risposta oltre 15 MB dà `ERRORE_RETE` | sitemap generata nel test | S-24 | `tests/fonti/siti/test_siti.py` | S |
| **T-48** `test_arxiv_con_una_risposta_vuota_o_non_atom_e_la_paginazione` | 200 con HTML o corpo vuoto: lista vuota senza eccezioni (P22); una voce scartata nella pagina da 200 ferma la paginazione (P23) | `MockTransport` e `monkeypatch` di `arxiv.PAUSA` | S-25, S-26 | `tests/fonti/test_arxiv.py` | S |
| **T-49** `test_la_stessa_esecuzione_da_dashboard_cli_telegram_e_programmazione` | `POST /esecuzione`, `POST /api/esegui`, `/aggiorna` e il programmatore producono la stessa esecuzione (stessa `Esecuzione`, stesse notizie e metriche) e cambia solo `avviata_da` | un `Esecutore` con fonti e provider finti nel `client`; il bot e il programmatore con `EsecutoreFinto` non bastano: serve quello vero | requisito "avviabile da dashboard e da CLI con lo stesso risultato"; oggi si prova solo il rifiuto della seconda (ACC-03) | `tests/app/test_servizio.py` | M |
| **T-50** `test_il_redirect_di_robots_txt_verso_la_rete_di_casa_viene_seguito` | `robots.txt` che reindirizza a `http://192.168.1.1/robots.txt`: la richiesta parte (P43) | `MockTransport` che registra gli indirizzi, come `tests/fonti/siti/test_sicurezza.py:17` | S-32; si ribalta con la correzione | `tests/fonti/siti/test_sicurezza.py` | S |

Totale: 23 + 17 + 10 = 50 test, 31 di sforzo S e 19 di sforzo M. Sforzo complessivo (stima, S circa 1,5 ore e M circa 4
ore): circa 120 ore, cioè **15 giorni di lavoro se fatti tutti**; i primi 10 (T-01...T-10, 6 S e 4 M) circa 3-4 giorni.

### 3.4 Test esistenti fragili

| Dove | Fragilità | Gravità |
|---|---|---|
| `tests/app/test_avvio_reale.py:1-15` | avvia un processo vero: la porta si ottiene da `porta_libera` (`tests/conftest.py:14-17`) e si rilascia prima che il servizio la usi (corsa); attesa di 20 s; il processo figlio legge il `.env` vero (solo porta e cartella dati sono forzate con variabili d'ambiente) | media |
| `tests/llm/test_claude_code.py:77-96` (`test_timeout`, `test_chiamata_cancellata_chiude_claude`) | attese fisse di 2 s e 3,5 s (5,5 dei 16 s totali) e `asyncio.sleep(0.5)` per sperare che il processo sia partito: su una macchina lenta o su Windows può dare un falso verde o un falso rosso | media |
| `tests/esecuzione/test_esecutore.py:190`, `:342` | `asyncio.sleep(0.1)` e `(0.05)` per aspettare che il compito parta; un evento è più sicuro | bassa |
| `tests/fonti/test_youtube.py:77-101` | `time.sleep(0.05)` e programmazione dei thread per vedere "al massimo 2" | bassa |
| `tests/esecuzione/test_esecutore.py:32-35` (`candidata`) | l'orario è `adesso() - ore_fa` calcolato alla chiamata: due candidate con lo stesso `ore_fa` differiscono di microsecondi e l'ordine del tetto dipende da quale è creata dopo (visto in P05) | bassa |
| `tests/esecuzione/test_programmatore.py:75` | `astimezone(UTC)` dipende dal fuso della macchina; la suite passa con tre fusi diversi (P02) ma non è pensata per i giorni di cambio d'ora | bassa |
| `tests/app/test_avvio_sistema.py:14, 20, 29, 126, 155, 165` | sostituiscono tutto `os` del modulo con un `SimpleNamespace`: un nuovo `os.path` o `os.getpid` nel modulo li rompe; i confronti di percorsi "alla Windows" girano con le regole di Linux (P19) | media |
| `tests/conftest.py:20-25` | l'autouse non isola `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `APPDATA`: se un test dimentica di sostituire `attiva_avvio` o `crea_icone`, scrive nei file veri dell'utente | media |
| `tests/fonti/siti/conftest.py:12-17` | `PAUSA = 0.0` per tutti i test: le pause non si provano mai | bassa (ma nasconde WEB-18) |
| asserzioni esatte su fixture (es. `profilo.esclusi == [...]` in `tests/fonti/siti/test_siti.py:25`) | si rompono apposta con la decisione 22 | informativa |
| date assolute (`DAL = datetime(2026, 11, 1)`, feed di novembre 2026) | nessuna bomba a orologeria: le date assolute sono sempre passate come argomento; non ho trovato test che dipendano dalla data odierna | nessuna |

### 3.5 Strumenti che mancano

1. **Orologio finto comune.** Nel codice "adesso" ha sette nomi indipendenti: `dati/notizie.adesso` (importato anche
   da `dati/esecuzioni.py:10`, `dati/argomenti.py:11`, `dati/proposte.py:13`), `fonti/siti/date.adesso` (importato da
   `strategie/feed.py:10` e `strategie/html.py:9`), `datetime.now()` in `programmatore.py:32` (già iniettabile),
   `dati/database.py:62` e `:76` (nomi delle copie), `dashboard/comune.py:63`, `servizio.py:108` e
   `claude_code.avviso_login` (iniettabile). Sostituirne uno non cambia gli altri: serve una fixture che li sostituisce
   insieme e che finge anche `time.monotonic` e `asyncio.sleep` (attesa della rete, pause). Serve a T-44, T-46.
2. **Finto `claude` completo.** Oggi salva argomenti, stdin e solo `ANTHROPIC_API_KEY`
   (`tests/llm/test_claude_code.py:11-33`): deve salvare tutto l'ambiente, il percorso di lavoro, accettare una coda di
   risposte (quota, `null`, uscita vuota, `usage` completo, ritardo) e restare uno script Python eseguito con
   `sys.executable`. Serve a T-29.
3. **`Finto` migliorato.** Registra solo `(sistema, messaggio)` (`llm/finto.py:13`): servono schema e modello, una
   latenza opzionale, risposte per numero di chiamata, errori programmabili. Serve a T-04, T-05, T-24, T-28.
4. **`Application` e `Update` finti di Telegram** (P09, P10 li hanno già mostrati fattibili): `Application` che registra
   i gestori, `Bot` con `_bot_user`, fabbrica di `Message`. Serve a T-32, T-33.
5. **Server HTTP locale su 127.0.0.1** (asyncio, porta 0) per i test di lentezza (P13b), e un generatore di sitemap e
   feed grandi. Serve a T-46, T-47.
6. **Fixture del sistema operativo**: sostituisce `os` del modulo con `name`, `environ`, `path` coerenti e
   le costanti di `subprocess`. Serve a T-37, T-38.
7. **Isolamento di `HOME`, `XDG_*`, `APPDATA`, `USERPROFILE`** in un autouse (rete di sicurezza di 3.4).
8. **Costruttore di database "vecchi" con dati** (alla versione N, con dati in tutte le tabelle), perché il database vero non si
   usa nei test. Serve a T-01, T-43, T-45.
9. **Misura**: `pytest-cov` (domanda 1).
10. **Risposte registrate di Claude** per il pre-filtro (fixture anonime), solo dopo una chiamata vera autorizzata
    (domanda 4): senza, nessun test può dire come l'LLM giudica un video.
11. **Una cartella `tests/accettazione/` e un report datato in `docs/test/`** (domanda 6).

---

## 4. Sospetti bug per la fase 4

Gravità (stima): alta, media, bassa. "Provato" rimanda al registro; "letto" vuol dire solo lettura del codice. Il test
di regressione è quello che servirebbe dopo la correzione; il test di caratterizzazione corrispondente è in sezione 3.

### 4.1 Elenco

**S-01. Tutti i video YouTube esclusi come "sponsorizzato o offerta" (decisione 13).** Gravità alta.
- *Comportamento*: nelle esecuzioni 8, 9 e 10 (8-11 nov) 1 + 3 + 3 = 7 video esaminati, 7 `escluse` con motivo "sponsorizzato o offerta", 0 mostrati; i 7 indirizzi sono nel registro delle viste e non tornano (9 indirizzi YouTube nel registro in tutto: 2 + 7). Nell'esecuzione 1 (6 nov), prima del campo `sponsorizzate` (ipotesi: il codice in esecuzione corrispondeva ai commit), 2 video esaminati su 2 mostrati. Dati veri letti con `mode=ro`.
- *Dove*: `esecuzione/prompt.py:24-34` (l'istruzione, valida per ogni tipo e senza nominarlo; dal 7 nov chiede anche di mettere gli id in `sponsorizzate`, commit `0aba1f2`), `esecuzione/esecutore.py:405-413` (i segnalati finiscono in `notizie_viste` e non si riconsiderano), `fonti/youtube/__init__.py:99` (il sommario è la descrizione del feed), `esecuzione/prompt.py:47-49` (titolo e sommario fino a 1.500 caratteri: il pre-filtro non vede la trascrizione).
- *Ricostruzione senza LLM* (P07): il sommario di un video è `voce.get("summary")`, cioè la descrizione del feed (`media:description`); a `messaggio_prefiltro` arriva `{id, titolo, sommario[:1500]}`; il prompt di sistema dice "Escludi i contenuti sponsorizzati e le offerte commerciali" senza distinguere video, siti e paper; il requisito `WEB-22` e `WEB-23` sta nella sezione dei siti ma il codice lo applica a tutto. Con l'interruttore attivo e un LLM finto che segnala chi nomina uno sponsor: video non salvato, `escluse` 1, alla seconda esecuzione non si riconsidera; con l'interruttore spento lo stesso video è mostrato.
- *Perché sembra sbagliato*: una descrizione di YouTube contiene quasi sempre link, codici sconto e righe di sponsor; il pre-filtro giudica solo titolo e descrizione e l'esclusione è definitiva.
- *Cosa non è dimostrato*: **il verdetto dell'LLM**. L'ipotesi "la descrizione contiene link di sponsor" non è sostenuta dall'unico sommario salvato (uno short da 224 caratteri, senza link né parole di sponsor, mostrato nell'esecuzione 1); le 7 descrizioni escluse non sono state salvate. Le spiegazioni compatibili con i dati: (a) la regola vale per ogni tipo, (b) il campo `sponsorizzate` introdotto il 7 nov dà all'LLM un posto dove segnare, (c) descrizioni con sponsor e link, (d) giudizio su sola descrizione. Per separarle serve una chiamata vera sulle descrizioni vere (domanda 4) oppure salvare il sommario degli esclusi.
- *Test di regressione*: T-09 oggi; dopo la correzione, un test che dica la nuova regola (per esempio che l'esclusione non vale per i video, o è recuperabile) con il `Finto`; per il verdetto reale serve una risposta registrata.

**S-02. Quota esaurita insieme a un altro errore nello stesso gruppo: esecuzione "fallita" invece che "interrotta".** Bassa (serve la quota insieme a un errore che non sia `ErroreLLM`; stessa radice di S-04, S-05 e S-07: `_esegui` usa il testo dell'`ExceptionGroup` come motivo). Provato (P03). `esecutore.py:458-466` e `:148-155`: con due blocchi (quota e `RuntimeError`) stato `fallita`, motivo `" (2 sub-exceptions)"`. Test: T-27.

**S-03. "rate limit" e "quota" trattati come quota esaurita.** Da chiedere all'utente: `PAROLE_QUOTA` contiene "rate limit" di proposito (`llm/claude_code.py:26`), quindi è una scelta, non un difetto accertato. Provato (P36): "API Error: rate limit exceeded" e "would exceed your quota of tokens per minute" danno `QuotaEsaurita` (`llm/claude_code.py:26`, `:53`) e interrompono l'esecuzione; "Overloaded" e un 500 danno `ErroreLLM`. Test: T-29.

**S-04. `interpreta` solleva `AttributeError` con JSON che non è un oggetto.** Bassa. Provato (P04): `null`, `[]`, `"x"`, `42`, `true`; con un finto `claude` che stampa `null` l'esecuzione fallisce con motivo "unhandled errors in a TaskGroup (1 sub-exception)" (`claude_code.py:51`; il pre-filtro prende solo `ErroreLLM`, `esecutore.py:393`). Test: T-29.

**S-05. Risposte LLM di forma inattesa: perdita silenziosa o esecuzione fallita.** Media. Provato (P28): pre-filtro `{}` o stringa: tutte le notizie del blocco scartate e segnate viste, esecuzione "completata"; `pertinenti: null` o `punteggi` non lista di oggetti: `fallita` con motivo opaco; `riassunto: null` salvato come stringa `"None"` (`esecutore.py:449`); `pertinenza` 85,5 ignorata e notizia scartata e vista; `true` vale 1. Non verificato se `--json-schema` di Claude Code rende queste forme impossibili. Test: T-28.

**S-06. `termina` che fallisce lascia `avanzamento` impostato.** Media. Provato (P17) e con un blocco di scrittura vero (P39): `esecutore.py:162-164`; ogni `avvia` dà `GiaInCorso` fino al riavvio; nel database l'esecuzione resta `in_corso`. Test: T-26.

**S-07. Errore in `_salva` o `conta_token` fa fallire tutta l'esecuzione con un motivo che non dice niente.** Media. Provato (P18, P39): `esecutore.py:318-319`, `:454`; motivo "unhandled errors in a TaskGroup (2 sub-exceptions)" (ESE-13 chiede un motivo utile). Test: T-26.

**S-08. Database bloccato: il ciclo di eventi si ferma per 5 secondi a ogni tentativo.** Media. Provato con una seconda connessione che tiene il blocco (P39): l'esecuzione solleva `OperationalError: database is locked` dopo 10,0 s (due attese di 5 s: `cancella_scadute` e `termina`), per tutto il tempo il ciclo non risponde (un "battito" ogni 0,1 s ha uno scarto di 10,0 s). Nessun `journal_mode` né `busy_timeout` espliciti (`dati/database.py:17-27`). Collegato a S-11 e S-37. Test: T-26.

**S-09. Programmatore: ora solare, due esecuzioni.** Bassa. Provato (P01): con orario tra 02:00 e 02:59 e l'orologio locale che torna indietro, `ultimo < scadenza <= adesso` (`programmatore.py:63`) è vera due volte. Test: T-41.

**S-10. Programmatore: esecuzione non recuperata se il PC è sospeso mentre passa l'orario.** Bassa: **comportamento previsto da `ESE-01`** (il recupero scatta solo all'avvio, se l'orario di oggi è già passato, una volta sola); resta impreciso solo il docstring (`programmatore.py:4-6`). Provato (P01): sospeso dalle 23:10 alle 00:40 con orario 23:30: 0 esecuzioni; sospeso 02:00 del giorno 7, svegliato 06:00 del giorno 8: il giorno 7 è perso (le 2 esecuzioni osservate sono il recupero del giorno 6 al primo controllo e quella dell'8). Il recupero esiste solo al primo controllo dopo l'avvio (`:59-61`). Le notizie si perdono per la durata della pausa, non per il programmatore. Test: T-41.

**S-11. Un secondo servizio avviato mentre il primo è acceso segna interrotta l'esecuzione in corso.** Media. Provato per la parte `crea_app` (P16): `app/servizio.py:95-102`. Il resto (secondo bot, recupero) è letto, non provato. Innesco realistico: `leggi_stato` ha timeout 2 s (`app/cli.py:20`) e un servizio fermo da S-08 o S-24 sembra spento. Test: T-40.

**S-12. Due `avvia()` del bot insieme creano due poller.** Bassa. Provato con `Application` finta (P09): `bot.py:106-134`, 2 create, 2 in polling, `ferma()` ne ferma 1. Test: T-33.

**S-13. Il bottone del cuore inverte il database, non il bottone; con `reply_markup` `None` solleva dopo aver scritto.** Bassa: la prima metà non è un bug (il bottone inverte il valore del database e la tastiera viene aggiornata), la seconda è praticamente irraggiungibile. Provato (P09b): `bot.py:244-261`, riga 255-256. Test: T-34.

**S-14. `/api/spegni` e `X-Forwarded-For` dietro un proxy locale.** Media nel contesto 6c, bassa oggi. **Non provato**: `TestClient` non applica `ProxyHeaders` di uvicorn (P34); serve uvicorn vero con `proxy_headers=True`. `app/servizio.py:50-51`.

**S-15. `HX-Current-URL` uguale a `/configurazione` con una sezione fuori dai passi dà 500.** Bassa. Provato (P30): `rotte_impostazioni.py:47-48`. Test: T-31.

**S-16. `POST /impostazioni/esecuzione` con soli `soglia` e `finestra_giorni` mette in pausa e spegne le due esclusioni.** **Non è un bug** (tolto dopo la rilettura): una casella non spuntata non viene inviata (commento in `rotte_impostazioni.py:246`), l'unico modulo che fa quel POST invia tutte le caselle, e il comportamento è già fissato da `tests/dashboard/test_rotte.py:134-138` e `:307-313`. Provato (P31): da (False, True, True) a (True, False, False); `rotte_impostazioni.py:242-249`. Test: T-31.

**S-17. `GRADIENS_CLAUDE` nel `.env` non ha effetto.** Bassa: è un disallineamento della documentazione (nessun documento cita proprio `GRADIENS_CLAUDE` tra le opzioni del `.env`; README e `struttura.md` parlano delle opzioni `GRADIENS_*` in generale). Provato (P20): `llm/claude_code.py:31` legge solo `os.environ`; `struttura.md` e README dicono che le opzioni `GRADIENS_*` vanno nel `.env`. Test: T-29.

**S-18. Migrazione fallita a metà: stato parziale e secondo avvio che rifallisce.** Alta per l'ADR 0011. Provato (P15b, P15c): senza ricreazioni nessun rollback (restano le tabelle create), con una ricreazione restano `_alembic_tmp_*` e le tabelle create prima del primo DML; il secondo avvio dà "table ... already exists"; nessun ripristino automatico. Una `add_column` su `siti` è DDL puro e velocissima (P15: 0,01 s), ma proprio per questo non è annullabile. Test: T-01, T-43.

**S-19. La copia di sicurezza che fallisce impedisce l'avvio del servizio.** Bassa, **probabilmente voluto**: succede solo quando il database non è all'ultima versione (`database.py:41`), cioè al primo avvio dopo un aggiornamento con una migrazione, ed è plausibile come protezione (meglio non partire che migrare senza copia). Letto: `dati/database.py:41-42`, a differenza della copia giornaliera (`programmatore.py:54-55`). Disco pieno, cartella sincronizzata (OneDrive). Test: T-43.

**S-20. Date future accettate da feed e sitemap.** Media. Provato (P12) per il feed; per la sitemap solo letto (in `sitemap.py` non c'è nessun rifiuto delle date future): una voce datata tra 400 giorni diventa candidata con data certa, stato "ok"; vince l'ordine del tetto (`siti/__init__.py:109`) e non scade finché non passano 7 giorni dopo la sua data. Decisione 16. Test: T-21.

**S-21. Un feed in ritardo ferma la cascata e si perdono articoli.** Alta. Provato (P29): `siti/__init__.py:107-108`; stato "ok" e nessun guasto, quindi nessun segnale. Proposta 6a-5. Test: T-18.

**S-22. robots.txt con 503 o 429 vieta il sito per un'ora.** Bassa, **comportamento voluto**: un 503 singolo si riprova subito (`rete.py:162`; riprovato nella rilettura: 2 richieste, poi la pagina risponde 200) e tradurre un 5xx persistente in "tutto vietato" è la regola di RFC 9309 citata nel codice (`rete.py:92`). L'unico punto discutibile è che conti come guasto per `WEB-24`. Provato (P13): `rete.py:114-116`; il guasto "robots.txt ora vieta" entra nel conteggio dei 3 guasti di WEB-24. Test: T-46.

**S-23. Il timeout di `httpx` è per operazione, non totale.** Bassa. Provato (P13b): con `TIMEOUT` 0,5 s un server che manda un byte ogni 0,3 s tiene la lettura per 3,9 s (`rete.py:145`). Test: T-46.

**S-24. Una sitemap o un feed grandi bloccano il ciclo di eventi.** Bassa-media. Provato (P11): `sitemap.interpreta` è sincrona, 2,0 s per 50.000 voci e 8,6 s per 200.000 (il limite del protocollo è 50.000 voci). Test: T-47.

**S-25. Una risposta 200 non valida di arXiv o YouTube dà zero risultati e stato "ok".** Media. Provato (P22): pagina HTML o corpo vuoto danno lista vuota senza eccezioni; `rete_disponibile` guarda solo il DNS (`esecutore.py:96-102`), quindi un portale captive passa. Test: T-22, T-48.

**S-26. arXiv: una voce scartata ferma la paginazione.** Bassa. Provato (P23): `arxiv/__init__.py:65` confronta 200 con le voci interpretate. Test: T-48.

**S-27. `soglia` 0 con punteggio 0: notizia "mostrata" ma invisibile.** Bassa. Provato (P06): `esecutore.py:439`, `:452`. Test: da aggiungere a T-28.

**S-28. `cli._riepilogo` indicizza chiavi che le metriche vecchie non hanno.** Bassa. Provato (P21): `KeyError: 'scartate_prefiltro'` (`app/cli.py:109-112`); oggi si legge sempre una metrica appena scritta. Test: T-30.

**S-29. `stato_da_xml` e la codifica dell'uscita di `schtasks`.** Media se confermato. La decodifica è provata (P35): un'uscita in cp850 o cp1252 letta come UTF-8 con `errors="replace"` (`avvio_sistema.py:106`) dà "un'altra cartella" per un percorso con accenti; **non verificato** che `schtasks /Query /XML` scriva in quella codifica su una pipe (serve il PC Windows). Test: T-38.

**S-30. Un errore di rete in `completa` diventa "errore di estrazione" definitivo.** Media. Provato per `completa` (P42); il lato esecutore è solo letto: `estrazione.py:56-57`; nell'esecutore la notizia entra nelle viste e nei "problemi" e non si riprova (`esecutore.py:304-309`, come `ContenutoAssente`), al contrario degli errori di rete in valutazione. Un guasto passeggero perde l'articolo. Test: T-12 (lato esecutore) e uno in `test_siti.py`.

**S-31. `completa` non ricontrolla la finestra.** Bassa-media. Provato (P41): una candidata incerta la cui pagina dice 60 giorni fa viene valutata (quota) e poi cancellata per età (`estrazione.py:61-62`). Test: da aggiungere a T-17.

**S-32. Il redirect di robots.txt verso la rete di casa viene seguito.** Media (sicurezza). Provato (P43): la richiesta a `http://192.168.1.1/robots.txt` parte (`rete.py:105`, `follow_redirects=True`); i test controllano solo i redirect delle pagine (`test_sicurezza.py:17`). Test: T-50.

**S-33. Timeout e nuovo tentativo raddoppiano durata e quota.** Bassa-media. Provato (P38): con timeout 1 s, 2 processi in 2,0 s; con 300 s fino a 600 s e quota doppia per una sola notizia (`claude_code.py:81-83`). Test: T-29.

**S-34. La rigenerazione sostituisce un profilo buono con uno senza strategie.** Alta. Provato (P32): `rigenera` con un sito che risponde 404 o con rete assente dà `strategie = []`, diagnosi "nessuna strategia funzionante"; l'esecutore la salva (`esecutore.py:233-241`) e il profilo buono resta solo in `profilo_precedente`, che la rigenerazione successiva sovrascrive (`dati/siti.py:58`). Decisione 21. Test: T-14.

**S-35. Le date incerte oltre il tetto di pagine passano come nuove.** Bassa, **comportamento previsto da `ESE-03`** ("per le notizie con data incerta conta la data di scoperta"): il problema è il costo, di cui si occupano l'ADR 0011 e la proposta 6a-3. Provato (P33): con 5 pagine e 12 voci senza data, 8 candidate restano incerte e vanno al pre-filtro con la data di scoperta anche se vecchie (`siti/__init__.py:148`). Test: T-16.

**S-36. Una valutazione fallita fa ripassare la notizia dal pre-filtro e dalla valutazione a ogni esecuzione.** Media. Provato (P37): la seconda esecuzione rifà una chiamata di pre-filtro e una di valutazione per la stessa notizia (`esecutore.py:312-315`). Quota sprecata fino a 7 giorni. Test: T-04.

**S-37. `gradiens esegui`: la prima richiesta non è protetta e il servizio occupato sembra spento.** Bassa. Letto: `app/cli.py:128` non intercetta `httpx.HTTPError`; con il ciclo bloccato (S-08, S-24) `httpx.post` con timeout 10 s dà una traccia. Non provato.

**S-38. `aggiorna` e il pannello: spegnimento in un momento sbagliato.** Bassa. Letto: `aggiornamento.py:46-52` controlla "esecuzione in corso" e poi spegne; una programmata che parte nel mezzo viene interrotta. Non provato (corsa tra due richieste).

**S-39. Il motivo di un'esecuzione fallita non si accorcia nel messaggio Telegram.** Bassa. Provato (P45): un motivo da 5.151 caratteri (un `OperationalError` con SQL e parametri) dà un messaggio di 5.421 caratteri, sopra i 4.096 che `messaggi.py:13` indica come limite di Telegram; l'errore di invio va solo nel log (`bot.py:177-178`): proprio la segnalazione del guasto può non arrivare (ESE-13). Test: T-35.

**Conteggio**: 39 sospetti. Provati 35: S-01 (il meccanismo, non la causa), S-02...S-10, S-11 (solo la parte `crea_app`),
S-12, S-13, S-15...S-18, S-20...S-28, S-29 (solo la decodifica), S-30...S-36, S-39. Solo letti 4: S-14, S-19, S-37,
S-38. Non verificabili qui: la causa di S-01 (serve un verdetto vero dell'LLM), il formato dell'uscita di `schtasks`
in S-29 (serve Windows), `X-Forwarded-For` con uvicorn in S-14.

### 4.2 Esito per ogni osservazione della mappa

Legenda: **C** = confermata con una prova; **P** = resta da provare; **N** = non è un bug (scelta, costo, requisito non
implementato o già deciso).

**A6** ([mappa-moduli.md](../architettura/mappa-moduli.md#a6-osservazioni-per-le-fasi-successive))

| Osservazione | Esito | Rimando |
|---|---|---|
| Tetto arXiv dopo il pre-filtro | N: deciso (ADR 0010) | T-02, T-03 |
| Il pre-filtro scarta poco | N: dato di quota | |
| Notizie non viste ripassano dal pre-filtro (blocchi falliti, valutazioni fallite, dirette, resti di un'interruzione) | C per la valutazione fallita (P37) | S-36, T-04 |
| Nuovo tentativo per ogni `ErroreLLM`, timeout compreso | C (P38) | S-33 |
| "rate limit" come quota | C (P36) | S-03 |
| Token in ingresso sommano la cache; ipotesi sulla quota | N: ipotesi sulla quota di Anthropic, non testabile | T-29 |
| Riuso della cache dei prompt | N: misura della 6b | |
| Video tutti esclusi come sponsorizzati | C nel meccanismo, non nella causa (P07 e dati) | S-01 |
| Provider e modello non modificabili dalla dashboard | N: 7a rimandata | |
| `termina` che fallisce | C (P17, P39) | S-06 |
| Errore in `_salva` e `conta_token` | C (P18) | S-07 |
| Argomenti: un blocco fallito salta i successivi | N: scelta dell'ADR 0008; da caratterizzare, non provata | T-24 |
| `pronto()` due volte | N: costo di un processo | |
| Secondo servizio prima dell'apertura della porta | C per `segna_interrotte` (P16); P per bot doppio e recupero | S-11 |
| `await bot.avvia()` ritarda la porta oltre 20 s | P: serve una rete lenta | |
| `GRADIENS_CLAUDE` nel `.env` ignorato; ambiente ereditato dal pannello | C la prima parte (P20); P la seconda | S-17 |
| `invia_prova` e `gira` insieme | C (P09) | S-12 |
| `drop_pending_updates`, `invia_esecuzione` senza riprova | N: scelte documentate | |
| `aggiorna` interrompe un'esecuzione programmata che parte nel mezzo | P: corsa tra due richieste | S-38 |
| Programmatore: sospensione e risveglio | C (P01) | S-10 |
| Programmatore: ora solare, doppia esecuzione | C (P01) | S-09 |
| Documenti non allineati (ADR 0006, `struttura.md`) | N: documentazione | |
| Riga di comando su Windows (32.767 caratteri) | N oggi (3 interessi, 181 caratteri di descrizioni), ma il limite si supera: 41.903 caratteri con 100 argomenti dai nomi pieni di virgolette, 32.615 nella valutazione con 30 interessi, oltre 63.000 con 60 (P08, rilanciata nella rilettura); `Interesse.descrizione` non ha un limite di lunghezza | |

**B5**

| Osservazione | Esito | Rimando |
|---|---|---|
| Migrazione fallita a metà | C (P15b, P15c) | S-18 |
| Nessun `journal_mode` né `busy_timeout`; `database is locked` fa fallire l'esecuzione | C (P39) | S-08 |
| Accesso al database sincrono nel ciclo di eventi | C (P39: ciclo fermo 10 s) | S-08 |
| `stato_avvio` esegue processi nelle rotte `async` | P: serve il tempo reale di `systemctl` o `schtasks` | |
| `notizie_viste` cresce senza limite | N: oggi 1.447 righe | |
| Home e Telegram caricano tutto; `/notizie` non è paginata | N: prestazioni | |
| La dashboard scrive e fa commit da sola | N: stile | |
| Cuore: inversione e bottone di Telegram | C (P09b) | S-13 |
| `approva` non atomico | P: serve far fallire il secondo commit | |
| `salva_segreto` non atomico, `chmod` dopo la scrittura | P: non osservabile in modo deterministico | |
| `/api/spegni` dietro un proxy | P: serve uvicorn con proxy | S-14 |
| `HX-Current-URL` e `KeyError` | C (P30) | S-15 |
| Configurazione iniziale: `POST /esecuzione` parte comunque, il programmatore no | N: incoerenza letta; non provata (la prova avvierebbe `claude`) | |
| `messaggi.py` importa `dashboard.comune` | N: dipendenza | |
| `migra` e `segna_interrotte` prima della porta | C per `segna_interrotte` (P16) | S-11 |
| Liste di valori duplicate, nessun `CHECK` | N: manutenzione | |
| `salva_esecuzione` riaccende la programmazione; POST parziale | N: non è un bug (vedi S-16) | |
| notizie con `esecuzione_id` nullo (4 nel database il 13 novembre) | N: dati storici | |
| `tests/dati/` senza file per `impostazioni`, `interessi`, `siti`, `esecuzioni` | N: sono coperti da altri test; i comportamenti a rischio sono in T-30 e T-45 | |

**C4**

| Osservazione | Esito | Rimando |
|---|---|---|
| Tetti di hwupgrade; tetto prima del registro delle viste | N: deciso (ADR 0011, 6a-3, 6a-6) | T-16, T-17 |
| Date incerte oltre il tetto di pagine passano al pre-filtro | C (P33) | S-35 |
| Data dalla sola `lastmod` | N: decisione 16 (si lascia così) | |
| `updated_parsed` come data di pubblicazione | N: scelta analoga alla 16; letto (`feed.py:36`) | |
| `completa` non ricontrolla la finestra | C (P41) | S-31 |
| Cache e robots.txt in memoria | N: 6a-10 | T-46 |
| Sezioni proposte poco utili | N: qualità della ricerca | |
| Sezioni non modificabili (WEB-03) | N: requisito non implementato | |
| `sembra_articolo` troppo largo | N: qualità | |
| Feed della home accettati senza perimetro | C il comportamento (P29b); N come bug: decisione 18 | T-19 |
| Siti collegati che non fanno leggere nulla | N: limite documentato | |
| WordPress senza paginazione; piattaforme senza strategia | N: limite noto (oltre 100 voci si passa all'HTML) | T-10 |
| Ordine delle date nell'HTML diverso da WEB-15 | N: scelta dichiarata | |
| Pre-filtro con poco testo | N: 6b-8 | |
| "Accesso bloccato" conta come guasto | N: scelta; WEB-24 va allineato | T-08 |
| "ok" con guasto | N: comportamento | T-08 |
| La rigenerazione copia interi i campi modificati | N: comportamento del test esistente | |
| Differenze, anteprima, `data_da` | N: requisiti non implementati | |
| Rigenerazione fallita: guasti non azzerati | N: comportamento; da fissare | T-13 |
| Errore di rete in `completa` = errore definitivo | C (P42) | S-30 |
| Pagina dell'articolo scaricata due volte | N: costo | |
| SSRF residua (redirect di robots.txt, DNS, feed a mano) | C per il redirect di robots.txt (P43); P per DNS e feed a mano | S-32 |
| Solo https | N: limite | |
| Agente non uniforme (yt-dlp) | N | |
| Tetto arXiv dopo il pre-filtro | N: deciso | |
| Arresto della paginazione arXiv | C (P23) | S-26 |
| "Nessuna fonte raggiungibile" non scatta per i siti | N: comportamento; combinato con S-34 diventa grave | S-34 |

---

## 5. Domande per l'utente

Solo scelte che dipendono da te, ciascuna con la risposta consigliata.

1. **`pytest-cov` sì o no?** *Consiglio: sì.* Dà la copertura per ramo, vede i processi figli (servizio e `__main__`) e
   mostra in CI i rami Windows davvero eseguiti; costa una dipendenza di sviluppo, una riga nel flusso di GitHub e due
   righe in `.gitignore`. Prima si verifica che `coverage` supporti Python 3.14.
2. **Una soglia minima di copertura in CI?** *Consiglio: no, solo il rapporto.* Una soglia spinge a coprire righe
   facili; conta di più coprire i casi della sezione 2.
3. **I test di caratterizzazione che fissano un comportamento sbagliato restano verdi con un commento "vedi S-nn", o
   diventano `xfail`?** *Consiglio: verdi con commento.* Così la suite resta una garanzia di non-regressione, e quando
   il bug si corregge il test si ribalta insieme al codice (nessun marcatore nuovo in `pyproject.toml`).
4. **Una chiamata vera di prova per il difetto dei video (S-01)?** Servono le 7 descrizioni (una richiesta al feed del
   canale) e un solo pre-filtro con Haiku; stima di circa 5.000 token (ipotesi, da misurare). *Consiglio: sì, nella
   fase 4*, perché è l'unico modo di separare le cause (a)-(d) di S-01 e di registrare la prima risposta vera da usare
   come fixture. In alternativa, salvare il sommario degli esclusi e aspettare la prossima esecuzione.
5. **Prove sul PC Windows**: tre comandi da lanciare quando sei al PC (`schtasks /Query /TN Gradiens /XML` e la pagina di codici
   della console; il percorso reale di `claude` dopo `claude.cmd`; `gradiens stato` con il nome utente con accenti,
   se ce n'è uno). *Consiglio: sì*, perché S-29 e il layout di `claude.cmd` sono i due rischi Windows senza prova.
6. **`tests/accettazione/` e `docs/test/`** sono previsti da `struttura.md` ma non esistono; `verifica_reale.py`
   sta in `tests/fonti/siti/` e stampa solo a video. *Consiglio: non crearli* (la decisione 15 ha tolto le misure di
   generalizzazione dei siti) e correggere `struttura.md`; un report datato si scrive solo se rifai la verifica dei 13 siti.
7. **Isolare `HOME` e le cartelle di configurazione in `tests/conftest.py`** (autouse). *Consiglio: sì*, costa
   una decina di righe e impedisce a un test dimenticato di scrivere nei file veri (`~/.config/systemd`, menu).
8. **Quanti test prima di cambiare il codice delle decisioni 8 e 17 (ADR 0010 e 0011)?** *Consiglio: T-01...T-10 prima
   del primo commit di codice* (circa 3-4 giorni, stima) e gli altri del gruppo A insieme alle modifiche; il gruppo B
   solo quando si decide un refactoring.

### Che cosa non ho potuto verificare

- Tutto il ramo Windows reale (UAC, `schtasks`, layout npm di `claude.cmd`, OneDrive): provato solo ciò che si può
  simulare (P19, P35).
- Il verdetto di Claude sui video (S-01) e se `--json-schema` impedisce le forme inattese di S-05.
- `X-Forwarded-For` con uvicorn vero (S-14); due processi veri sullo stesso database (S-11 oltre `crea_app`);
  `SIGTERM` di systemd; la rete lenta contro i 20 s di `gradiens avvia`.
- `rete_disponibile` reale (non eseguita: nessuna rete); la compatibilità di `coverage` con Python 3.14.
- Il contenuto del `.env`, che non ho aperto.

---

## Appendice: registro delle prove

Cartella delle prove: `scratchpad/fase2/` dentro la cartella temporanea della sessione di lavoro (sotto `/tmp`: si svuota al riavvio del PC, quindi l'esito di ogni prova sta qui).
Comando tipo, da quella cartella con il `conftest.py` copiato da `tests/`: `PYTHONDONTWRITEBYTECODE=1 uv run --frozen pytest
--rootdir=<cartella> -p no:cacheprovider -q -s -c /dev/null <file>` (dalla radice del progetto). Nessuna prova ha scritto
in `.gradiens/` né nel progetto, chiamato un LLM o fatto richieste esterne: `rete_disponibile` finta dal `conftest.py`,
fonti con `httpx.MockTransport`, database temporanei, copie del database vero fatte con `sqlite3.backup` da una
connessione `mode=ro`; l'unico server è locale (127.0.0.1, P13b). Suite del progetto prima e dopo: 182 passati, `git status`
senza modifiche al progetto.

- **P01** (`p01_programmatore.py`, con `TZ=UTC` e `TZ=Europe/Rome`, stesso esito): ora solare, orario 02:30, orologio locale
  da 02:59:50 a 02:00:20: 2 esecuzioni; ora legale (01:59:50 -> 03:00:20): 1; sospeso 23:10-00:40 con orario 23:30: 0; avvio
  alle 00:40 con orario 23:30: 0; sospeso e svegliato nello stesso giorno: 1; orario 07:00, sospeso 02:00 del 7 e svegliato 06:00
  dell'8: 2 esecuzioni (recupero del giorno 6 al primo controllo e quella dell'8: la 07:00 del 7 è persa).
- **P02**: suite con `TZ=Pacific/Auckland`, `America/Los_Angeles`, `Asia/Kolkata`: 182 passati ogni volta.
- **P03** (`test_p_esecutore.py`): quota + `RuntimeError` in due blocchi: `fallita`, motivo `" (2 sub-exceptions)"`; la sola quota: `interrotta`.
- **P04**: `interpreta` con `null`, `[]`, `"x"`, `42`, `true`: `AttributeError`; con un finto `claude` che stampa `null`: `fallita`, "unhandled errors in a TaskGroup (1 sub-exception)".
- **P05**: caso normale: esaminate 4 = 1 + 2 + 1 + 0; blocco fallito: esaminate 2, esiti 1, errori 1. **P06**: soglia 0, punteggio 0: 1 salvata, 0 pertinenze, `mostrate` 1, visibili 0.
- **P07** (`test_p_youtube.py`): vedi S-01; `escludi_sponsorizzati=True`: 0 salvate, `escluse` 1, 2ª esecuzione `esaminate` 0; `False`: 1 salvata.
- **P08** (`p08_riga_comando.py`, `subprocess.list2cmdline`): 21.903 (100 nomi da 200); 41.903 (100 nomi di virgolette); 32.140 (30 interessi da 500+500); database vero: 3 interessi, 181 caratteri.
- **P09, P10** (`test_p_bot.py`): vedi 2.5 e S-12, S-13; i 7 comandi con i gestori veri: chat autorizzata sì, altra chat no.
- **P11** (`test_p_fonti.py`): sitemap 50.000 voci 2,0 s, 200.000 voci 8,6 s; risposta da 18 MB: `ERRORE_RETE`. **P12**: voce a 400 giorni nel futuro accettata. **P13**: `ReadTimeout` 2 tentativi; risposta a metà: 0; robots.txt 503 e 429: `VIETATA`, 403: permesso, timeout: 0. **P13b**: 3,9 s con `TIMEOUT` 0,5 s.
- **P15, P15b, P15c** (`test_p_dati_app.py`, copia del database vero): vedi S-18 e 2.4; P15: conteggi 13/145/227/1.447/10/76 invariati, 0,01 s.
- **P16** secondo `crea_app`: `in_corso` -> `interrotta`. **P17, P18, P39**: `termina` e `_salva` che falliscono; blocco di scrittura vero: 10,0 s, ciclo fermo 10,0 s, `OperationalError`, `avanzamento` impostato, stato `in_corso`.
- **P19, P19b** (Windows su Linux), **P35** (`p35_schtasks.py`): vedi 2.6 e S-29. **P20**: `GRADIENS_CLAUDE` solo nel `.env`: ignorato. **P21**: `KeyError: 'scartate_prefiltro'`.
- **P22, P23**: risposte 200 non valide e paginazione arXiv. **P27**: profilo con campi mancanti. **P28**: tabella delle forme inattese (vedi S-05).
- **P29, P29b, P32, P33** (`test_p_siti.py`): feed in ritardo, voci di altri domini, rigenerazione con 404 e con rete assente, 12 voci senza data con e senza tetto di pagine. **P30, P31, P34** (`test_p_dashboard.py`): 500, pausa e esclusioni spente, `should_exit`.
- **P36** (`test_p_varie.py`): "rate limit" e "quota" danno quota, "Overloaded" e un 500 no. **P37**: valutazione fallita, 2ª esecuzione con una chiamata in più di pre-filtro e di valutazione. **P38**: timeout 1 s, 2 processi, 2,0 s. **P41, P42, P43**: `completa` senza controllo della finestra, errore di rete come "errore di estrazione", redirect di robots.txt verso 192.168.1.1 seguito. **P44**: 60 valutazioni intrecciate, tutte salvate. **P45**: motivo da 5.151 caratteri, messaggio da 5.421.
- **Dati veri** (sola lettura): vedi S-01; `escludi_sponsorizzati` = 1; cronologia git del prompt: `76e947c` (6 nov) "Escludi i contenuti sponsorizzati e le offerte commerciali."; `0aba1f2` (7 nov) campo `sponsorizzate` e "non metterli tra i pertinenti e restituisci i loro id".
