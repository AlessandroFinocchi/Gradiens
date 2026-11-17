# Miglioramenti di Gradiens: indice e stato

Lavoro di analisi iniziato il 12 novembre 2026. Produce **solo documentazione** (analisi, proposte
e piani): nessuna modifica a codice, test, configurazione o dipendenze. I documenti stanno in
`docs/`; le risposte dell'utente in [decisioni.md](decisioni.md).

Questo file serve a riprendere il lavoro da un'altra sessione: dice a che punto siamo, cosa è
stato deciso e dove sono i documenti.

## Priorità concordate

Dall'intervista iniziale (decisioni 1-3 del 12 nov 2026):

1. **Quota LLM**: esplorare più notizie a parità di quota (proposta 6b).
2. **Ricerca delle notizie sui siti**: generalizzare ai siti nuovi e spendere meno (proposta 6a).
3. Affidabilità e accesso da fuori casa (6c) vengono dopo.

Macchina di riferimento: questa installazione Linux (dati e log veri in `.gradiens/`). Il ramo
Windows si verifica con prove chieste all'utente. Le proposte possono essere invasive
(riscritture, dipendenze nuove, modifiche allo schema), fermi i vincoli di CLAUDE.md.

## Fasi e stato

| Fase | Documento | Stato |
|---|---|---|
| 1 — Mappa e documentazione | [../architettura/mappa-moduli.md](../architettura/mappa-moduli.md) | fatta e riletta (12 nov 2026) |
| 2 — Test e copertura (piano) | [02-test-e-copertura.md](02-test-e-copertura.md) | chiusa (13 nov 2026): copertura 86,8% delle righe ([dati](dati/copertura-2026-11-13.md)), 50 test di caratterizzazione proposti, 31 sospetti bug per la fase 4 (S-03 chiuso dalla decisione 27), decisioni 23-27; rilettura abbreviata su richiesta dell'utente (il documento elenca le parti non rilette) |
| 3 — Revisione architetturale | [03-revisione-architetturale.md](03-revisione-architetturale.md) | chiusa (14 nov 2026): 15 problemi, piano di refactoring in 5 passi prima delle modifiche già decise più 6 rimandati; decisioni 28-35, ADR 0012 e precisazione dell'ADR 0011; riletta e corretta, la versione corretta non è stata riletta una seconda volta |
| 4 — Debugging difficile (analisi) | [04-debugging.md](04-debugging.md) | chiusa (15 nov 2026), versione corta: 15 schede e una prova vera sui video YouTube ([dati](dati/prova-video-youtube-2026-11-14.md)); decisioni 36-43; le correzioni della rilettura sono nella sezione "Esito della rilettura" (le schede non sono state riscritte); restano le prove che deve raccogliere l'utente |
| 5 — Lavori su larga scala (piano) | [05-dipendenze-e-stile.md](05-dipendenze-e-stile.md) | chiusa (15 nov 2026): decisioni 44-49; rilettura mirata, con le correzioni nella sezione "Esito della rilettura" del documento; resta da fare la prova vera di yt-dlp (autorizzata) |
| 6a — Ricerca delle notizie sui siti | [06a-ricerca-sui-siti.md](06a-ricerca-sui-siti.md) | chiusa (13 nov 2026): bozza riletta e corretta, decisioni 12 e 15-22 |
| 6b — Consumo di token e tetti | [06b-consumo-di-token.md](06b-consumo-di-token.md) | chiusa (13 nov 2026): bozza riletta e corretta, decisioni 8-14 |
| 6c — Dashboard raggiungibile da internet | [06c-dashboard-da-internet.md](06c-dashboard-da-internet.md) | chiusa (15 nov 2026): Tailscale Serve, versione completa; decisioni 50-57 e ADR 0013, che comprende le correzioni della rilettura di sicurezza (il documento non è stato riscritto) |

Ordine deciso dall'utente (decisione 4): prima 6b e 6a, poi le fasi 2, 3, 4, 5 e infine la 6c.
Alla fine di ogni fase: riepilogo breve e attesa dell'ok dell'utente.

Per la fase 6 valgono anche le decisioni 5-7: misura con 8 chiamate vere a Claude Code (fatta il
12 nov: 38.405 token), solo leve dentro l'abbonamento e senza LLM, un passaggio diagnostico sui
13 siti veri (al massimo 600 richieste, una volta sola).

## Riepilogo finale (15 novembre 2026)

Tutte e sei le fasi hanno un documento e le decisioni dell'utente sono in [decisioni.md](decisioni.md)
(numeri 1-57). Non è stato modificato né committato nessun file di codice, test o configurazione.

**Decisioni diventate ADR "accettato, da implementare"**
- [ADR 0010](../adr/0010-prefiltro-arxiv-fino-al-tetto.md): il pre-filtro dei paper arXiv si ferma quando i
  promossi riempiono il tetto (`ARX-02` cambia); tetto arXiv a 30.
- [ADR 0011](../adr/0011-raccolta-incrementale-dei-siti.md): raccolta incrementale dei siti, con la regola di
  "coperto fino a" e il rischio accettato sui feed in ritardo.
- [ADR 0012](../adr/0012-llm-del-profilo-del-sito-nel-backend.md): l'aiuto dell'LLM al profilo di un sito, su
  richiesta, in un modulo del backend.
- [ADR 0013](../adr/0013-dashboard-da-fuori-casa-con-tailscale-serve.md): dashboard da fuori casa con
  Tailscale Serve.

**Ordine suggerito per l'implementazione** (dai documenti delle fasi 2, 3 e 4)
1. I primi 10 test di caratterizzazione (decisione 26). **Fatti (15 nov 2026)**, tranne T-09, già coperto da
   `test_un_video_segnalato_come_sponsorizzato_si_valuta_comunque` dopo la correzione dei video. Con loro è entrato
   `pytest-cov` (decisione 23), anche nella CI.
2. I cinque passi di refactoring (decisione 28).
3. La correzione dei video YouTube (decisione 36): piccola e indipendente. **Fatta (15 nov 2026)**: test
   `test_un_video_segnalato_come_sponsorizzato_si_valuta_comunque`, correzione in `esecuzione/esecutore.py`
   (`filtra`), `WEB-23` aggiornato nel PRD.
4. ADR 0010, poi ADR 0011 con la protezione del profilo (decisione 21).
5. Le correzioni della fase 4 che hanno una soluzione pronta; ruff come linter. **Fatte le schede 7 e 11 (17 nov
   2026)**: lucchetto attorno all'avvio e allo spegnimento del bot (`telegram/bot.py`), così anche un `ferma()` arrivato durante
   un avvio lo spegne; `/pausa`, `/riprendi`, Aiuto e `TG-10` dicono
   che i comandi a Gradiens spento vanno persi e che `/riprendi` non recupera (decisione 41). Il caso d della
   scheda 11 (il modulo delle Impostazioni che toglie la pausa) resta per R-09. **Fatte le schede 8 e 14 (17 nov
   2026)**, in `fonti/siti/rete.py`: i redirect di robots.txt si seguono a mano con lo stesso controllo delle pagine
   (`_destinazione`); un redirect verso la rete di casa vale come rete assente (decisione 39, solo redirect). Un
   robots.txt con 5xx vieta il sito per 5 minuti invece di un'ora (non solo per il `Navigatore`: l'estrazione ne
   crea uno per articolo); il 429 resta un'ora. Test in `tests/fonti/siti/test_sicurezza.py` e nel nuovo
   `tests/fonti/siti/test_rete.py`. **Fatte le schede 9 e 13 (17 nov 2026)**: il programmatore controlla
   `avviate_dal` a ogni orario superato, così al ritorno all'ora solare parte una sola esecuzione
   (`esecuzione/programmatore.py`); l'attesa della rete passa a 15 minuti e un'esecuzione fallita per mancanza di
   rete (`esecuzioni.NESSUNA_RETE`) non conta per il recupero (decisione 40, `ESE-01` precisato). Le correzioni C e D
   della scheda 13 (avvisi Telegram persi, controllo della rete via HTTP) non sono state decise. Test in
   `tests/esecuzione/test_programmatore.py` e `test_esecutore.py`. `mappa-moduli.md` non è stata aggiornata (300 s,
   "conta qualsiasi esecuzione"). **Fatto ruff come linter (17 nov 2026)**: ruff 0.17.5 come dipendenza di sviluppo,
   configurazione minima della 6.1 del documento 05 in `pyproject.toml` (solo linter, niente formatter), passo
   `uv run ruff check` nella CI. Le segnalazioni vere erano 23 (non circa 15): oltre a quelle stimate, 4 UP037
   (annotazioni tra virgolette), 2 B008 (lambda con valori fissati, lasciate con `noqa`) e 1 F811 (due funzioni
   `esegui` in `app/servizio.py`: la rotta è diventata `esegui_da_cli`).
6. ADR 0013; ADR 0012 per ultimo.

**Ancora aperto**
- **Due correzioni senza soluzione pronta**: la migrazione del database in transazione (la variante provata
  fa perdere dati) insieme al cambio annunciato di `sqlite3` in Python 3.16, e la protezione dal secondo
  processo del servizio. Finché non c'è un test adatto, `dati/database.py` non va toccato.
- **Prove che deve fare l'utente**: l'elenco è in [04-debugging.md](04-debugging.md) (la più urgente: salvare
  il feed del canale YouTube) e in [06c-dashboard-da-internet.md](06c-dashboard-da-internet.md) (passi in
  Tailscale); tutto il ramo Windows resta solo letto.
- **Misure e prove autorizzate e non ancora fatte**: M1-M6 sui token (decisione 10, a tempi separati) e la
  prova vera di yt-dlp (decisione 46).
- **Domande minori mai fatte**: tre della fase 2 (elencate in decisioni.md) e la proposta P-3 della fase 3
  (le metriche salvate cambiano solo per aggiunta).
- **Documenti non riscritti dopo le riletture o le decisioni**: 03, 04, 05, 06a, 06b e 06c hanno in testa una
  nota o una sezione "Esito della rilettura" che vale sul testo sotto.
- **Documenti esistenti da allineare al codice quando lo si implementa**: PRD (`ARX-02`, `ESE-04`, `WEB-08`,
  `WEB-24`, `AMB-02`, `TG-03`, `ESE-01`), `struttura.md` (proprietari, contratto delle fonti,
  sicurezza della dashboard, `llm/compatibile_openai` che non esiste) e l'ADR 0006 (tre punti superati e il
  rischio di `--bare`).

## Fase 1: cosa è stato fatto e cosa resta aperto

- La mappa è stata scritta unendo tre analisi (app/esecuzione/llm/telegram; dati/dashboard;
  fonti) e poi riletta contro il codice da due revisori: circa 80 correzioni applicate
  (riferimenti di riga, affermazioni riformulate o declassate a ipotesi, omissioni sulla cascata
  dei siti). I 6 diagrammi Mermaid sono stati disegnati senza errori con Mermaid 10.9.1.
- Le scoperte più pesanti sono riassunte all'inizio della mappa ("Le dieci cose da sapere prima
  di toccare il codice"). Per le priorità concordate contano soprattutto: il tetto arXiv
  applicato dopo il pre-filtro (73-75% delle notizie pre-filtrate nelle esecuzioni 9 e 10 sono
  paper poi scartati dal tetto), le notizie che ripassano dal pre-filtro a ogni esecuzione,
  l'LLM mai usato nella ricerca sui siti, la cascata che di solito si ferma alla sitemap, le date
  prese da `lastmod`, le pagine spese per cercare le date.
- **Non verificato** (resta ipotesi nella mappa): se la cache dei prompt di Claude Code viene
  davvero riusata e come pesa sulla quota; se `claude auth status` consuma quota; tutto il ramo
  Windows (percorso di `claude` in modalità S4U, limite della riga di comando, migrazione
  fallita); le pagine lette per sito (le metriche non le registrano); le cause che richiedono
  richieste ai siti veri (feed ufficiale di ACN assente dal profilo, ilsoftware non riconosciuto
  come WordPress, pagine consumate da hwupgrade); le corse tra due servizi avviati insieme e tra
  scritture concorrenti sul database.
- **Documenti esistenti che non coincidono con il codice** (segnalati nella mappa, non corretti):
  `struttura.md` cita `llm/compatibile_openai`, che non esiste, e dice "spegnimento solo da
  127.0.0.1" (il codice accetta anche `::1`); tre punti dell'ADR 0006 (osservazioni A6); `WEB-02`
  (anteprima degli articoli) e `WEB-25` (differenze dopo la rigenerazione) non sono implementati;
  `GRADIENS_CLAUDE` nel `.env` non ha effetto. Da decidere con l'utente se correggere i documenti
  o il codice.

## Fase 6b e 6a: cosa è stato fatto e cosa resta aperto

- **Misure fatte** (non ripetibili senza un nuovo permesso): 8 chiamate vere a Claude Code il 12
  nov (38.405 token: carico fisso, cache, ragionamento); un passaggio diagnostico sui 13 siti veri
  il 12 nov (281 richieste su 600 ammesse). **I dati grezzi di entrambe sono andati persi** con il
  riavvio del PC del 13 nov, perché stavano nella cartella temporanea della sessione: restano le
  tabelle di sintesi dentro i due documenti. Regola da allora: i dati di una misura non ripetibile
  si copiano subito in `docs/` (o, per l'app, in `.gradiens/`).
- **Rilettura**: ogni bozza è stata riletta contro codice e database da un revisore; gli autori
  hanno applicato le correzioni (per la 6b: risparmio della proposta principale ricalcolato, stime
  dichiarate come tali, domande ridotte; per la 6a: effetti quantificati ridimensionati, un'idea
  smentita dal database tolta, banco di misura messo per primo). Le versioni corrette sono state
  controllate a campione dal coordinatore, **non rilette una seconda volta per intero**.
- **Fatti esterni** (prezzi, cache, variabili di Claude Code): verificati sulle pagine ufficiali
  il 12 e 13 nov 2026; elenco nella sezione 7 della 6b.
- **Non verificato**: come la quota dell'abbonamento pesa ingresso, cache, uscita e ragionamento
  (nessuna pagina ufficiale lo dice); alcuni campi della risposta di `claude -p` visti nei JSON poi
  persi (`thinking_tokens`, `rate_limit_event`); l'effetto delle proposte 6a su copertura e pagine
  (serve il banco di misura); tutto il ramo Windows.
- **Rischio da seguire** (emerso leggendo la documentazione, da riprendere nella fase 5): la
  pagina ufficiale di `claude -p` dice che `--bare` diventerà il predefinito in una versione
  futura, e in quella modalità Claude Code non usa il login dell'abbonamento. Le chiamate di
  Gradiens (ADR 0006) potrebbero smettere di funzionare dopo un aggiornamento di Claude Code.
- **Domande aperte per l'utente**: sezione 6 di ciascun documento. Le risposte vanno in
  [decisioni.md](decisioni.md); quelle che cambiano un requisito o l'architettura (per esempio
  `ARX-02`) diventano anche un ADR "accettato, da implementare".

## Stato delle proposte

Stati possibili: bozza, discussa, accettata, scartata. Aggiornati con le decisioni dell'utente
del 13 nov 2026 (8-22); "bozza" = non ancora discussa una per una. Gli sforzi sono stime (g = giorni, h = ore; S, M, L =
piccolo, medio, grande).

### 6b — Consumo di token ([06b-consumo-di-token.md](06b-consumo-di-token.md))

| Codice | Problema in breve | Raccomandazione | Sforzo | Stato |
|---|---|---|---|---|
| 6b-1 | Le metriche non separano cache, ragionamento, fase e tipo di fonte | Fare subito: solo aggiunte | 0,5 g | bozza |
| 6b-2 | Il 43% dei token (es. 10) va al pre-filtro di paper poi scartati dal tetto | Pre-filtro dei paper per data, a blocchi, fino a riempire il tetto (−44% / −34% di token); cambia `ARX-02` | 1-1,5 g | **accettata** (ADR 0010); tetto arXiv a 30 |
| 6b-3 | L'ingresso è scritto in cache a 1 ora e, tranne il prefisso, non riletto | Cache a 5 minuti nel provider Claude Code (valore in quota: ipotesi) | 1-2 h | bozza |
| 6b-4 | Una chiamata per paper, quasi tutta carico fisso | Valutazione a lotti di 5 paper, dopo una misura | 1-1,5 g | bozza, dopo la misura M3 (autorizzata) |
| 6b-5 | Ragionamento sempre attivo su Haiku 5.5 | Effort basso e istruzione nel prompt, dopo una misura | 0,5 g | bozza, dopo la misura M4 (autorizzata) |
| 6b-6 | Circa 825 token aggiunti da Claude Code a ogni chiamata | Diagnosi, poi variabili d'ambiente | 0,5 g | bozza, dopo le misure M1-M2 (autorizzate) |
| 6b-7 | Il tetto sceglie per data, non per pertinenza | Non ora: misurare e decidere | 1-1,5 g | bozza, rimandata |
| 6b-8 | Sommario fino a 1.500 caratteri nel pre-filtro | Solo se `ARX-02` non cambia | 1-2 h | bozza |
| 6b-10 | Taglio a 60.000 caratteri, trascrizioni lunghe | Misurare prima | 2-3 h | bozza |
| 6b-12 | Rivalutazioni, nuovi tentativi, `pronto` due volte | Solo `pronto` una volta, il resto dopo la misura | 2-3 h | bozza |
| 6b-9, 11, 13, 14, 15 | Blocchi più grandi, deduplicazione, altro modello, schema, argomenti | Lasciare così (schede brevi con il perché) | — | bozza |
| 6b-16 | Modello locale, embedding, API a pagamento | Solo descritti (decisione 6) | — | non pianificata |

Tetto arXiv sostenibile a parità del consumo dell'esecuzione 10 (oggi 10): circa 50 nello
scenario prudente (solo 6b-2 e 6b-3), 80-87 con lotti ed effort basso (da misurare).

### 6a — Ricerca sui siti ([06a-ricerca-sui-siti.md](06a-ricerca-sui-siti.md))

In ordine consigliato:

| Codice | Problema in breve | Raccomandazione | Sforzo | Stato |
|---|---|---|---|---|
| 6a-1 | Nessun modo di misurare una modifica senza nuove richieste | Banco di misura con risposte registrate in `.gradiens/banco/` | M | **non pianificata** (decisione 15: niente misura della generalizzazione) |
| 6a-11 | Profilo che diventa vuoto; niente anteprima, differenze, sezioni | Protezione del profilo subito; il resto dopo | S + M | protezione del profilo **accettata** (decisione 21); il resto bozza |
| 6a-4 | Feed di una sezione scartato (ACN: da 17 a 38 articoli in 7 giorni) | Accettare il feed linkato dalla pagina della sezione | S | bozza |
| 6a-5 | Un feed in ritardo ferma la cascata (redhotcyber: 9 articoli su circa 21-28) | Modulo che legge sempre news sitemap o API | S-M | bozza; traduzioni escluse per default (decisione 22) |
| 6a-2 | `lastmod` vale come data certa (7 falsi nuovi su 102); date future accettate | `lastmod` da confermare; date future rifiutate | S + M | `lastmod` **scartata** (decisione 16); resta solo il rifiuto delle date future |
| 6a-7 | Sitemap lette alla cieca | Figlie giuste, news sitemap prima | S-M | bozza |
| 6a-3 | La fonte non conosce il registro delle viste | Parametro `viste` e registro degli scartati per data | M | bozza |
| 6a-9 | HTML: non articoli, pagine per la data spese male | `non_articolo` più severo; priorità alle notizie | M | bozza |
| 6a-6 | Ogni esecuzione rifà tutta la finestra; tetti fissi (hwupgrade) | Raccolta incrementale e tetti adattivi; migrazione | L | **accettata** (ADR 0011) |
| 6a-13 | Candidate inutili al pre-filtro | Voci di terzi domini fuori; regola sui titoli facoltativa | S-M | voci di altri domini fuori: **accettata** (decisione 18); regola sui titoli **scartata** (decisione 20) |
| 6a-8 | Piattaforme riconosciute male | Più segnali, API paginata | S + M | bozza |
| 6a-10 | Cache solo in memoria | Cache su disco con richieste condizionali | S-M | bozza |
| 6a-12 | Euristiche che falliscono senza aiuto | LLM solo alla creazione del profilo, su richiesta, con tetto | M | **accettata**, su richiesta e per ultima (decisione 19) |

Le proposte 6a che trovano più articoli consumano parte della quota che la 6b libera (stima:
60-110 mila token per esecuzione su circa 226 mila): è la domanda 10 della 6a e la D5 della 6b.

## Sospetti bug e punti fragili raccolti

L'elenco completo e aggiornato è nella sezione 4 di [02-test-e-copertura.md](02-test-e-copertura.md)
(S-01…S-39, con l'esito di ogni prova): 32 passano alla fase 4. I più gravi: video YouTube tutti
esclusi (S-01), rigenerazione che svuota il profilo di un sito (S-34, già coperta dalla decisione 21),
feed in ritardo che ferma la cascata (S-21), database bloccato che ferma il servizio per 10 secondi e
lascia l'esecuzione "in corso" (S-06, S-08), due esecuzioni al ritorno all'ora solare (S-09), redirect
di robots.txt verso la rete di casa (S-32), risposte dell'LLM di forma inattesa che perdono notizie in
silenzio (S-05), migrazione fallita a metà (S-18).

- **Priorità alta per la fase 4** (decisione 13): tutti i video YouTube delle esecuzioni 8, 9 e
  10 (7 su 7) sono stati esclusi dal pre-filtro come "sponsorizzato o offerta", ma l'utente li
  voleva. Oggi YouTube non produce nessuna notizia. Ipotesi da verificare: la descrizione del
  video, usata come sommario, contiene link di sponsor e affiliazioni.
  **Corretto il 15 nov 2026** (decisione 36): i video segnalati come sponsorizzati passano alla valutazione.

Le osservazioni raccolte durante la mappa (fase 1) sono nell'ultima sezione di
[mappa-moduli.md](../architettura/mappa-moduli.md). Passano nelle liste delle fasi 2 (test di
caratterizzazione) e 4 (schede di debugging).

## Come si lavora

- Regole di CLAUDE.md: documentazione in italiano, Windows e Linux insieme, niente commit, merge
  o push da parte di Claude.
- Si chiede all'utente prima di consumare quota LLM, installare pacchetti o fare molte richieste
  a siti esterni.
- Sottoagenti di `.claude/agents` per l'analisi, mai due sullo stesso file. Livello di
  ragionamento: **xhigh** nelle fasi 3, 4 e 6, **high** nelle fasi 1, 2 e 5 (vale anche per la
  sessione: va ricordato all'utente prima di ogni fase).
- Ogni proposta contiene: problema (con `file:riga`), opzioni con compromessi, raccomandazione,
  impatto su Windows e Linux, passi di implementazione piccoli e verificabili, test da scrivere,
  rischi, stima dello sforzo. Solo fatti verificati; ipotesi e stime sono dichiarate.
- Strumenti di analisi (script in sola lettura, fuori dal progetto): il grafo degli import è stato
  calcolato con uno script AST sui file di `src/gradiens`; il metodo è descritto in
  mappa-moduli.md. Gli script stavano nella cartella temporanea della sessione, che si svuota a
  ogni riavvio del PC: non sono conservati, e i documenti devono bastare a rifare i conti.
- I sottoagenti a xhigh consumano molta quota dell'abbonamento (una bozza di proposta: circa
  500.000 token; una rilettura: 250-300.000). Il 12-13 nov il limite delle 5 ore è stato
  raggiunto due volte. Dopo un'interruzione e un riavvio i sottoagenti non si possono più
  riprendere: conviene lanciarne pochi alla volta.
