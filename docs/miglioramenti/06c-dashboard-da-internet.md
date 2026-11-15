# 6c — Dashboard raggiungibile da fuori casa, in modo semplice e gratuito

Data: 15 novembre 2026. Stato: **bozza da discutere con l'utente**.

> **Decisioni dell'utente (15 novembre 2026)**, numeri 50-57 di [decisioni.md](decisioni.md): accesso da fuori casa con Tailscale Serve; certificati HTTPS accettati dopo aver controllato il nome della macchina; **versione completa** (sezione nelle Impostazioni e link al resoconto su Telegram); solo dal PC anche togliere i cuori, eliminare interessi e fonti e alzare i tetti; `AMB-01` e ADR 0001 aggiornati. La decisione è l'[ADR 0013](../adr/0013-dashboard-da-fuori-casa-con-tailscale-serve.md), che comprende le correzioni della rilettura di sicurezza. Il testo sotto è la bozza e non è stato riscritto.

Documento di sola analisi: non modifica codice, test, configurazione né dipendenze. Riferimenti `pacchetto/file.py:riga`
relativi a `src/gradiens/`. Termini di [CONTEXT.md](../../CONTEXT.md). I due registri delle decisioni hanno numeri
diversi: qui "decisione N" rimanda a [decisioni.md](decisioni.md) (miglioramenti) e "intervista N" a
[decisioni-intervista.md](../requisiti/decisioni-intervista.md) (requisiti). Valgono soprattutto le decisioni 2 e 50-52
e le interviste 1, 30 e 51.

## Riepilogo

**Oggi** la dashboard ascolta solo su 127.0.0.1 e risponde solo ai nomi `127.0.0.1` e `localhost`: dal telefono non si
apre. Non ha autenticazione. Le richieste che modificano devono avere `HX-Request` o `X-Gradiens-Cli` (difesa dal
CSRF, non un controllo d'accesso). Solo lo spegnimento è riservato al PC, e dietro un proxy sullo stesso PC questo
controllo dipende da come il proxy scrive `X-Forwarded-For`: senza quell'intestazione, lo spegnimento da remoto passa
(provato con lo strato vero di uvicorn). Chi raggiunge la dashboard può leggere tutto (ma non il token di Telegram),
avviare esecuzioni che consumano quota, togliere i cuori e quindi far cancellare l'Archivio, **sostituire il bot o
spostarlo sulla propria chat**, cambiare l'avvio all'accensione su Linux, far fare al server richieste verso la rete
di casa con un feed aggiunto a mano.

**Raccomandazione**: **Tailscale Serve**, che fa da proxy HTTPS solo dentro la rete Tailscale dell'utente. Gradiens
resta su 127.0.0.1 (importante perché gira su un portatile, che cambia rete), nessun dominio, nessuna autenticazione
da scrivere: entra solo chi ha un dispositivo nel tailnet. In più, le azioni pericolose diventano "solo dal PC" con un
controllo che non dipende dal proxy. Niente tunnel pubblici: richiederebbero autenticazione, limiti e controlli che
oggi mancano (sezione 3.3).

**Che cosa cambia**: nel codice, `dashboard/comune.py` (funzione `dal_pc`), `app/servizio.py` (spegnimento e
valori di uvicorn espliciti), `dashboard/rotte_impostazioni.py` e due modelli (rotte solo dal PC), la pagina Aiuto;
nella versione completa anche database, controllo dell'`Host`, una sezione delle Impostazioni e il messaggio
Telegram. Nessun codice specifico di un sistema. Nei requisiti `AMB-01`, `AMB-02`, `TG-03`, l'intervista 51, una
nota all'ADR 0001 e la regola di `struttura.md`; un ADR nuovo (0013). Fuori da Gradiens, una volta: abilitare HTTPS
nel tailnet, `tailscale serve --bg 8765`, l'app Tailscale sul telefono.

| Codice | Problema | Raccomandazione | Sforzo (stima) | Rischio |
|---|---|---|---|---|
| 6c-1 | "Solo dal PC" dipende da `X-Forwarded-For` e dai valori predefiniti di uvicorn | `dal_pc`: cliente locale, `Host` locale, niente `X-Forwarded-For`; valori di uvicorn nel codice | S, 2-3 h | basso |
| 6c-2 | Da remoto si sostituisce il bot, si sposta la chat, si cambiano avvio e icone | Quelle rotte solo dal PC, e l'interfaccia lo dice | S, 2-3 h | basso |
| 6c-3 | Dal telefono la dashboard non si apre | Tailscale Serve; nome `*.ts.net` nel `.env`; passi nella pagina Aiuto | S, 1-2 h più i passi a mano | basso |
| 6c-4 | Il nome va scritto nel `.env`, con un riavvio | Sezione "Accesso da fuori casa" nelle Impostazioni, nome nel database | M, 1-1,5 g | medio (riscrive il controllo dell'`Host`) |
| 6c-5 | Telegram senza link alla dashboard (intervista 51) | Link al resoconto, solo con l'accesso attivo | S, 1-2 h | basso |
| 6c-6 | Requisiti e ADR non dicono dove gira Gradiens né come lo si raggiunge | Testi nuovi di `AMB-01`, `AMB-02`, `TG-03`, ADR 0013, `struttura.md` | S, 2 h | nessuno |
| 6c-7 | Tunnel pubblico (Funnel, Cloudflare, ngrok, port forwarding) | Non ora; elenco delle protezioni obbligatorie in 3.3 | L se si fa | alto |
| 6c-8 | Nomi DNS verso indirizzi privati nelle fonti (decisione 39) | Non serve con il solo tailnet; obbligatorio con 6c-7 | M se si fa | — |

Versione minima: 6c-1, 6c-2, 6c-3, 6c-6 (0,5-1 giorno). Completa: più 6c-4 e 6c-5 (2-2,5 giorni).

## Esito della rilettura di sicurezza (15 novembre 2026)

Rilettura mirata sulla sicurezza, con prove su `TestClient` e sullo strato di uvicorn. L'analisi di com'è
protetta oggi la dashboard regge. **La protezione proposta però non è sicura così com'è scritta**: dove questa
sezione e il testo sotto dicono cose diverse, vale questa sezione.

**1. Bloccante: `dal_pc` dipende da come Tailscale Serve scrive le intestazioni.** Il testo dice che il
controllo "non dipende dal proxy" (riepilogo, 3.1, 4.2): non è vero. La funzione considera "dal PC" una
richiesta con cliente locale, `Host` locale e senza `X-Forwarded-For`. Ma l'`Host` lo scrive il cliente, e
Serve inoltra da 127.0.0.1: un dispositivo del tailnet che manda una richiesta scritta a mano con
`Host: localhost` è fermato **solo se** Serve aggiunge `X-Forwarded-For`. Prova: proxy locale senza
`X-Forwarded-For` e `Host` falsificato → `dal_pc` vero, e oggi anche `/api/spegni` risponde 200; lo stesso con
un proxy che scrive solo l'intestazione `Forwarded`. Che Serve aggiunga `X-Forwarded-For` è stato letto nel
sorgente del ramo principale di Tailscale, non verificato sulla versione installata (1.104.7), e la pagina
ufficiale di Serve (letta il 15 novembre 2026, https://tailscale.com/kb/1312/serve) **non lo documenta**:
documenta solo le intestazioni di identità `Tailscale-User-Login`, `Tailscale-User-Name` e
`Tailscale-User-Profile-Pic`, assenti nel traffico di Funnel. Con le modalità TCP di Serve non arriva nessuna
intestazione e le rotte "solo dal PC" si aprirebbero. **Correzione**: rendere il controllo indipendente dal
proxy. Serve punta a una **seconda porta locale** usata solo da lui, e una richiesta vale "dal PC" solo se
arriva sulla porta principale (uvicorn mette la porta locale nello `scope` e accetta più socket). In più, tra
i passi a mano, una verifica dal vero: dal telefono, un'azione "solo dal PC" deve essere rifiutata.

**2. Importante: incorniciamento (clickjacking), anche nel tailnet.** Mancano `X-Frame-Options` e
`frame-ancestors`. Un sito aperto sul telefono può incorniciare la dashboard: i clic dentro la cornice sono
della stessa origine, htmx manda `HX-Request` e la difesa CSRF non protegge. Così si possono avviare
esecuzioni, togliere cuori, eliminare interessi e fonti. Il testo chiede queste intestazioni solo per i tunnel
pubblici: vanno aggiunte **già nella versione minima** (un middleware in `app/servizio.py`). Vale già oggi sul
PC. Non verificato: se i blocchi dei browser verso la rete locale lo impediscono.

**3. Importante: richieste verso la rete locale a disposizione di chi è nel tailnet.** Un feed aggiunto a
mano accetta indirizzi come `http://127.0.0.1:<porta>`, `http://100.x` o `http://192.168.x`
(`dashboard/rotte_impostazioni.py:150-155`) e `leggi` non controlla l'indirizzo iniziale
(`fonti/siti/rete.py:119-132`). Con Serve, chi ha un dispositivo del tailnet fa fare al portatile richieste
verso i suoi servizi locali e verso la rete su cui si trova. Inoltre il filtro degli indirizzi riconosce solo
la forma canonica: `http://127.1/`, `http://2130706433/`, `http://0x7f000001/` passano
(`fonti/siti/indirizzi.py:25-28`). **Correzione** nella versione minima: il controllo dell'indirizzo pubblico
anche sugli indirizzi aggiunti a mano e sulle forme non canoniche. È il punto che la decisione 39 rimandava
alla 6c.

**4. Rischi residui da dichiarare, anche con le correzioni.** Da remoto restano possibili: avviare esecuzioni
e alzare i tetti (siti fino a 1.000 articoli e 500 pagine, arXiv fino a 500, finestra a 7 giorni), quindi
moltiplicare il consumo di quota; togliere i cuori e far cancellare subito l'Archivio (la pulizia parte
all'inizio di ogni esecuzione, che da remoto si può avviare: non "alla pulizia successiva"); eliminare
interessi e fonti. "Le azioni pericolose diventano solo dal PC" è troppo ottimista: due dei gruppi a gravità
alta restano da remoto. Vale per chiunque abbia in mano un dispositivo del tailnet (telefono rubato).

**5. Altri punti.**
- **Funnel**: Gradiens non distingue Serve da Funnel (stesso nome `Host`); attivare Funnel per errore
  renderebbe pubblica tutta la dashboard senza autenticazione. Da valutare un rifiuto esplicito (ipotesi: il
  traffico di Funnel porta un'intestazione riconoscibile; non verificato).
- **Host consentiti**: nel `.env` va scritto il nome completo della macchina, mai il modello `*.ts.net`, che
  lascerebbe passare qualunque nome.
- **"Disable Key Expiry"** è consigliato per i server: su un portatile, se viene rubato, resta nel tailnet
  senza scadenza. Da non consigliare senza dirlo.
- **Avvio all'accensione su Linux**: l'attivazione lancia anche `loginctl enable-linger`
  (`app/avvio_sistema.py:166-167`), una modifica di sistema che resta.
- **Test**: dopo il passo 3 le fixture `client` e `client_nuovo` (`tests/conftest.py:36-48`) usano un cliente
  che `dal_pc` rifiuta: falliscono `tests/dashboard/test_rotte.py:326-362`,
  `tests/telegram/test_bot.py:181-187` e `tests/dashboard/test_configurazione.py:77-81`. La fixture va
  cambiata (file del tester, decisione 31).
- **Requisiti**: `AMB-01`, `AMB-02` e l'ADR 0001 dicono già "da fuori casa tramite Tailscale"; il problema è
  che contraddicono `TG-03`, la decisione 51 dell'intervista sui requisiti e il codice. Anche con la versione
  minima il capoverso di `TG-03` ("la dashboard resta raggiungibile solo dal PC") diventa falso e va cambiato.
- **Permessi**: su Linux `tailscale serve` richiede `sudo` o l'utente operatore (il testo si contraddice).
- **Uso dal PC con l'indirizzo `ts.net`**: le azioni solo dal PC vengono rifiutate anche stando al PC; una
  configurazione iniziale fatta dal telefono non si completa (il passo Telegram è solo dal PC).

**Non riletto**: le fonti esterne e la tabella di confronto 2.3, Serve e uvicorn dal vero, il ramo Windows,
la sezione 4.4 (link su Telegram). Non verificato: che la dashboard ascolti davvero solo su 127.0.0.1 (dipende
dal `.env`, che non è stato letto).

## 1. Com'è protetta oggi la dashboard

Verificato leggendo il codice e con prove `TestClient` del 15 novembre 2026 (script usa e getta nella cartella
temporanea della sessione, con un database nuovo in quella cartella; nessun servizio vero, nessuna rete, nessuna
chiamata LLM; Telegram, avvio all'accensione ed esecutore sostituiti da finti dove servono). Gli esiti sono riportati
qui sotto come "Prova N". Lo script non è conservato (la cartella temporanea si svuota al riavvio): i test dei passi 1-3
della sezione 4.2 rifanno le stesse prove.

### 1.1 Dove ascolta

- `uvicorn.Config(app, host=conf.host, port=conf.porta, log_config=None)` (`app/servizio.py:137`). Valori predefiniti:
  `host="127.0.0.1"`, `porta=8765` (`app/configurazione.py:25-26`). Si cambiano con `GRADIENS_HOST` e `GRADIENS_PORTA`
  nel `.env` (prefisso `GRADIENS_`, `app/configurazione.py:20-22`); il `.env` si legge una volta all'avvio, quindi
  serve un riavvio.
- CLI e pannello parlano sempre con `http://127.0.0.1:<porta>` (`Configurazione.indirizzo_locale`,
  `app/configurazione.py:40-42`; `app/cli.py:20`, `:81`, `:128`; `app/pannello.py:66` apre la dashboard su quell'indirizzo).
  Se un giorno `GRADIENS_HOST` diventasse l'IP del tailnet, CLI e pannello non troverebbero più il servizio: per
  ascoltare anche fuori dal PC servirebbe un secondo indirizzo accanto a `127.0.0.1`, non una sostituzione (vedi 3.2).
- Al 15 novembre la porta 8765 non era in ascolto su questa macchina (controllo in sola lettura con `ss -ltn`): con la
  porta predefinita il Gradiens dell'utente era spento, quindi non ho potuto vedere l'indirizzo effettivo (non ho letto
  il `.env`).

### 1.2 Host consentiti

`TrustedHostMiddleware(allowed_hosts=conf.host_consentiti)` (`app/servizio.py:117`), predefinito
`["127.0.0.1", "localhost"]` (`app/configurazione.py:28`, nel `.env` come JSON). È aggiunto per ultimo, quindi controlla
per primo ogni richiesta, comprese `/api` e `/static`. Difende dal DNS rebinding dei browser, non da un client che
scrive `Host: localhost` a mano.

**Prova 1** (GET `/api/stato` con varie intestazioni `Host`): `127.0.0.1`, `localhost`, `127.0.0.1:8765` → 200;
un IP del tailnet inventato (`100.101.102.103`), lo stesso con `:8765`, un nome `*.ts.net` inventato, il nome corto
`gradiens` → **400**. Quindi oggi, anche se la porta fosse raggiungibile, un browser che apre l'indirizzo del tailnet
riceve "Invalid host header". La porta nell'intestazione non conta (Starlette la toglie prima del confronto).

### 1.3 Controllo delle intestazioni sulle richieste che modificano

Middleware `blocca_richieste_forgiate` (`app/servizio.py:110-114`): ogni metodo fuori da GET, HEAD, OPTIONS deve
avere `HX-Request` (htmx) oppure `X-Gradiens-Cli` (CLI, `app/cli.py:14`), di qualunque valore; altrimenti 403. Si
basa sul fatto che una pagina di un altro sito non può aggiungere intestazioni personalizzate senza il permesso CORS,
che Gradiens non concede (nessun `CORSMiddleware`).

**Prova 2**: POST `/impostazioni/tema` senza intestazioni → 403; con `HX-Request: x` → 200; con `X-Gradiens-Cli: 0` →
200 (il valore non conta). Preflight `OPTIONS` da un'altra origine → 405, nessuna intestazione `Access-Control-*`:
il browser non manderebbe la POST con l'intestazione. È una difesa contro il CSRF, **non un'autenticazione**: chiunque
scriva le richieste a mano (curl, uno script) la supera.

### 1.4 Rotte riservate al PC e come si decide "locale"

- Una sola: POST `/api/spegni` (`app/servizio.py:48-56`), che accetta solo `request.client.host` in
  `{"127.0.0.1", "::1"}` (`:28`, `:50`). Nient'altro distingue il PC dagli altri clienti.
- `request.client` lo decide uvicorn. `uvicorn.Config` ha `proxy_headers=True` e `forwarded_allow_ips` preso da
  `FORWARDED_ALLOW_IPS` o, se manca, `"127.0.0.1,::1"` (`.venv/.../uvicorn/config.py:225, 228, 361-363`, uvicorn
  0.54.0); `Config.load()` avvolge l'app in `ProxyHeadersMiddleware` (`config.py:543-544`). Se la connessione arriva
  da un indirizzo fidato e contiene `X-Forwarded-For`, il cliente diventa il primo indirizzo non fidato letto da
  destra; se tutti sono fidati, il primo della lista (`uvicorn/middleware/proxy_headers.py:169-187`).

**Prova 4** (TestClient, che non applica `ProxyHeadersMiddleware`): cliente `127.0.0.1` o `::1` → 200; cliente del
tailnet o della rete di casa → 403. Coincide con `tests/app/test_servizio.py:48-53`.

**Prova 5** (stessa app passata da `uvicorn.Config(...).load()`, cioè con lo strato `ProxyHeadersMiddleware` costruito
da uvicorn con i valori predefiniti, senza aprire porte; il tipo dello strato esterno è `ProxyHeadersMiddleware`,
`forwarded_allow_ips='127.0.0.1,::1'`):

| Scenario (POST `/api/spegni`) | Esito |
|---|---|
| proxy o tunnel sullo stesso PC che **non** aggiunge `X-Forwarded-For` | **200: spegnimento da remoto** |
| proxy sullo stesso PC che aggiunge `X-Forwarded-For: <cliente vero>` | 403 |
| proxy che inoltra un `X-Forwarded-For: 127.0.0.1` scritto dal cliente, senza accodare il proprio | **200** |
| proxy che accoda il cliente vero dopo quello falso (`127.0.0.1, <cliente vero>`) | 403 |
| accesso diretto dal tailnet (senza proxy) con `X-Forwarded-For: 127.0.0.1` falso | 403 (il cliente non è fidato, l'intestazione si ignora) |

Con l'intestazione `Host` pubblica inoltrata dal proxy (per esempio il nome `*.ts.net`) la dashboard risponde **400**
finché quel nome non entra in `GRADIENS_HOST_CONSENTITI`; con l'`Host` riscritto dal proxy in `127.0.0.1:8765`
risponde 200. Aggiungendo il nome `*.ts.net`, o l'IP del tailnet, a `host_consentiti`: 200.

Conclusione: **dietro un proxy o un tunnel sullo stesso PC, "solo dal PC" dipende da come quel proxy scrive
`X-Forwarded-For`**, cosa che Gradiens non controlla. È il sospetto S-14 del documento 02, ora dimostrato con lo strato
vero di uvicorn (non con un server in ascolto). Con l'accesso diretto all'IP del tailnet, invece, il controllo regge.

### 1.5 Autenticazione, cookie, sessioni, CORS

- **Nessuna autenticazione**: niente password, cookie, sessioni, token d'accesso, `Depends` di sicurezza (mappa B4e;
  ricontrollato: l'unica dipendenza è `comune.sessione`, `dashboard/comune.py:109-114`).
- **Prova 3**: la Home non manda `Set-Cookie`, né `Content-Security-Policy` né `X-Frame-Options`.
- **CORS**: nessuno (Prova 2).
- **OpenAPI, `/docs`, `/redoc`**: spenti (`app/servizio.py:98`).

### 1.6 Che cosa finisce nei log

- `configura_log` (`app/servizio.py:123-130`): file a rotazione in `.gradiens/log/`, livello INFO; `httpx` a WARNING
  perché gli indirizzi di Telegram contengono il token (`PER-04`).
- `log_config=None` lascia a uvicorn i suoi logger, che finiscono nello stesso file: `uvicorn.access` scrive ogni
  richiesta con l'indirizzo del cliente e il percorso con i parametri (documento 05, appendice: 2.056 righe, compreso il
  testo cercato nella dashboard). Dietro un proxy senza `X-Forwarded-For` tutti i clienti risultano `127.0.0.1`: dal
  log non si capirebbe chi ha fatto che cosa.
- I comandi Telegram ricevuti finiscono nel log con l'indicazione "chat non autorizzata" (`telegram/bot.py:191-196`).
- Nessun segreto nelle risposte: **Prova 6**, sotto.

### 1.7 Che cosa può fare chi raggiunge la dashboard così com'è

Vale per chiunque raggiunga la porta con un `Host` accettato (oggi solo dal PC; domani dal tailnet o da internet,
secondo l'opzione scelta). Le rotte che modificano stato sono 34, tutte POST (conteggio dei decoratori `.post(` in
`app/servizio.py` e `dashboard/*.py`; elenco in mappa B4e). Gravità "se l'accesso è di un estraneo": alta = danno
duraturo o difficile da notare; media = fastidio o costo recuperabile; bassa = nessun danno vero.

| Gruppo | Rotte (file:riga) | Che cosa può fare | Gravità con un estraneo |
|---|---|---|---|
| **Leggere** | tutte le GET: `dashboard/rotte.py:28-176`, `/impostazioni/{sezione}` (`rotte_impostazioni.py:93`), `/api/stato`, `/api/esecuzione` (`app/servizio.py:34`, `:69`) | Notizie, Archivio, interessi con descrizioni e raffinamenti, fonti seguite, profili dei siti, resoconti con metriche, soglia, orari, pausa, stato dell'avvio all'accensione. Telegram: **username del bot e nome della chat** sì, **token no**, id della chat no (**Prova 6**: nessuna delle 8 sezioni delle Impostazioni contiene il token finto; il modello riceve solo `token_salvato`, `rotte_impostazioni.py:59`). Chiavi API: non esiste una sezione che le mostri (la sezione Modelli LLM non è implementata). Claude Code: solo la data di scadenza del rinnovo nella Home (`claude_code.avviso_login`) | media: profilo di interessi e abitudini di lettura dell'utente; nessun segreto |
| **Consumare quota** | POST `/esecuzione` (`rotte.py:191`), POST `/api/esegui` (`app/servizio.py:59`) | Avviare esecuzioni una dopo l'altra (una alla volta, `ESE-02`): ogni esecuzione consuma quota dell'abbonamento (circa 226 mila token, stima riportata nel README dei miglioramenti). **Prova 7c**: da un cliente remoto entrambe accettate | **alta**: esaurisce la quota delle 5 ore, che serve anche all'uso interattivo di Claude Code |
| | POST `/impostazioni/siti` (`:168`), `/siti/{id}/rigenera` (`:217`), `/youtube` (`:133`) | Analisi di siti (decine di richieste con pause) e risoluzione di canali: oggi niente LLM; con l'ADR 0012 l'analisi con LLM su richiesta, tetto 10.000 token per sito | media |
| | POST `/configurazione/completa` (`rotte_configurazione.py:80`) | Lancia `claude auth status` anche a procedura conclusa (se consumi quota non è verificato, README) | bassa |
| **Modificare dati** | interessi, proposte, fonti, profili, soglia, finestra, orario, pausa, tema (`rotte_impostazioni.py:98-249`); argomenti (`rotte.py:97-113`) | Cambiare o eliminare interessi (l'eliminazione cancella le pertinenze), togliere fonti, alzare la soglia, mettere in pausa la programmazione | media: si nota e si rimedia, ma intanto le notizie non arrivano |
| | POST `/notizie/{id}/cuore` (`rotte.py:179`) | Togliere il cuore alle notizie dell'Archivio: alla pulizia successiva quelle più vecchie di 7 giorni si cancellano (`ESE-09`) | **alta**: perdita dell'Archivio; si recupera solo dalle copie di sicurezza in `.gradiens/backup/` (ultime 7 giornaliere) |
| **Telegram** | POST `/impostazioni/telegram/token`, `/cerca`, `/conferma`, `/prova`, `/cambia-chat` (`rotte_impostazioni.py:254-314`) | Sostituire il bot: un token di un altro bot viene verificato con Telegram e **sovrascrive** quello dell'utente nel `.env` (`configurazione.py:51-53`). Spostare il bot su un'altra chat: `/conferma` accetta qualunque `chat_id` dal modulo, senza controllare che venga da `/cerca` (**Prova 7a**: chat 999 salvata e bot riavviato). Chi vede lo username del bot gli scrive `/start` e poi si conferma come chat: riceve le notizie e comanda `/aggiorna`, `/pausa` | **alta**: l'utente perde il canale di notifica e di comando, e l'estraneo ne prende il controllo |
| **Far fare richieste al server** | POST `/impostazioni/siti` e soprattutto `/impostazioni/siti/{id}/feed` (`:184`) | Un feed aggiunto a mano passa solo da `_indirizzo_web` (`rotte_impostazioni.py:150-155`): **Prova 7d**, `http://192.168.1.1/feed` salvato nel profilo. Alla raccolta `leggi` controlla i redirect ma non l'indirizzo iniziale (`fonti/siti/rete.py:119-132`) e `_regole` scarica `/robots.txt` seguendo i redirect (`:105`). `normalizza` rifiuta i numeri IP non pubblici, compresi quelli del tailnet `100.x` (`fonti/siti/indirizzi.py:19-28`), ma non i nomi che puntano a indirizzi privati, compresi i nomi MagicDNS. Mappa C2e, decisione 39 | **alta** se l'accesso è pubblico (GET verso router e dispositivi di casa o del tailnet senza password); bassa con solo l'utente |
| **Spegnere** | POST `/api/spegni` (`app/servizio.py:48`) | Da remoto no, se l'accesso è diretto; **sì dietro un proxy sullo stesso PC che non scrive `X-Forwarded-For`** (Prova 5). Da remoto non si riaccende (intervista 30) | media: Gradiens resta spento fino al riavvio |
| **Avvio all'accensione** | POST `/impostazioni/avvio` (`:318`) | Linux: registra o toglie il servizio utente di systemd **senza conferme** (contenuto fisso, deciso da Gradiens: `avvio_sistema.py:127-143`); toglierlo significa che dopo il prossimo riavvio Gradiens non parte. Windows: chiede la conferma UAC sullo schermo del PC (`avvio_sistema.py:229-238`); se nessuno conferma fallisce, e se Gradiens gira nella sessione 0 fallisce subito. **Prova 7b**: rotta accettata da un cliente remoto | media su Linux; bassa su Windows (salvo una conferma UAC data per sbaglio) |
| **Icone** | POST `/impostazioni/avvio/icone` (`:333`) | Crea o toglie l'icona del pannello (contenuto fisso). Prova 7b: accettata da remoto | bassa |

Note:
- **Esecuzione di codice**: non ho trovato rotte che facciano eseguire comandi o file scelti dal cliente. I processi
  lanciati (`systemctl`, `loginctl`, PowerShell, `claude auth status`) hanno argomenti costruiti da Gradiens.
- **Dati del PC**: solo quando c'è un problema, la sezione Avvio mostra il comando da lanciare a mano
  (`impostazioni/avvio.html:27-31`): su Linux `sudo loginctl enable-linger <utente>` (`avvio_sistema.py:188-189`), su
  Windows lo script con cartella, Python e utente (`avvio_sistema.py:203-213`). Rivela il nome utente del PC.

### 1.8 Se davanti c'è un proxy o un tunnel sullo stesso PC

Riassunto della Prova 5: (1) l'`Host` che arriva è quello pubblico, e `TrustedHostMiddleware` lo rifiuta con 400
finché non si aggiunge a `GRADIENS_HOST_CONSENTITI`; (2) tutte le connessioni arrivano da `127.0.0.1`, quindi
`/api/spegni` diventa raggiungibile da remoto se il proxy non aggiunge `X-Forwarded-For` o se inoltra quello scritto
dal cliente; (3) il log di accesso mostra `127.0.0.1` per tutti, salvo `X-Forwarded-For`. Come si comportano i proxy
reali (Serve, cloudflared, ngrok) è nella sezione 2, dalle loro documentazioni.

## 2. Confronto delle opzioni

### 2.1 Punto di partenza

- **Chi e da dove** (decisioni 50-52): solo l'utente, dal telefono e dal portatile, dove può installare un'app; nessun
  dominio; Tailscale già installato e attivo.
- **Dove gira Gradiens** (decisione 2): ogni giorno su questa macchina Linux (Debian 13), che la decisione 6 chiama
  "questo portatile". L'ADR 0001 e `AMB-01` dicono invece il PC Windows di casa. Conta per la scelta: un portatile
  cambia rete (casa, ufficio, Wi-Fi pubblici), quindi **un Gradiens che ascolta su tutte le interfacce sarebbe
  esposto anche sulle reti degli altri**.
- **Tailscale su questa macchina** (sola lettura, 15 nov 2026; `tailscale version`, `tailscale serve status`,
  `tailscale funnel status` e un riassunto senza nomi di `tailscale status --json`):

| Voce | Esito |
|---|---|
| Versione del client | 1.104.7 |
| Stato | in funzione (`BackendState: Running`) |
| Serve e Funnel | nessuna configurazione ("No serve config") |
| MagicDNS | attivo |
| Certificati HTTPS del tailnet | **non abilitati** (nessun dominio di certificato; nessuna capacità `https` o `funnel` sul nodo) |
| Altri dispositivi nel tailnet | 1, Windows (il PC di casa). **Il telefono non c'è ancora** |
| Utenti nel tailnet | 1 |
| Scadenza della chiave del nodo | presente (non ho letto la data) |

### 2.2 Le opzioni

- **(a1) Tailscale, accesso diretto.** Gradiens ascolta anche fuori da 127.0.0.1 (`GRADIENS_HOST`) e il nome MagicDNS o
  l'IP del tailnet entrano in `GRADIENS_HOST_CONSENTITI`. Si apre `http://<macchina>:8765`. Il traffico è cifrato da
  Tailscale anche se l'indirizzo è `http` ("Connections between Tailscale nodes are secured with end-to-end
  encryption", F4), ma il browser lo mostra come non sicuro.
- **(a2) Tailscale Serve.** Gradiens resta su 127.0.0.1; `tailscale serve --bg 8765` fa da proxy HTTPS **solo dentro
  il tailnet** (F2, F3) con un certificato vero per `<macchina>.<tailnet>.ts.net`. Si apre
  `https://<macchina>.<tailnet>.ts.net`.
- **(b1) Tailscale Funnel.** Come Serve ma pubblico su internet (F5).
- **(b2) Cloudflare Tunnel con dominio** (F9-F11) e **(b3) senza dominio** ("quick tunnel" su `trycloudflare.com`, F8).
- **(b4) ngrok, piano gratuito** (F13, F14).
- **(c) Port forwarding sul router con DNS dinamico** (F15).
- **(d) Lasciare così**: dashboard solo dal PC; da fuori casa solo Telegram (`/aggiorna`, `/stato`, `/ultima`, cuore).

### 2.3 Tabella di confronto

Le "F" rimandano alle fonti della sezione 6, tutte lette il 15 novembre 2026. Dove una cella dice "non verificato",
la fonte letta non lo diceva.

| Criterio | (a1) Tailscale diretto | (a2) Tailscale Serve | (b1) Funnel | (b2) Cloudflare Tunnel + dominio | (b3) Quick tunnel | (b4) ngrok gratuito | (c) Port forwarding + DNS dinamico | (d) Così com'è |
|---|---|---|---|---|---|---|---|---|
| **Costo** | 0: piano gratuito, fino a 6 utenti, dispositivi illimitati, solo uso non commerciale (F1) | come (a1) | 0, "available for all plans" (F5) | dominio a pagamento (non ce l'ha, decisione 51); Zero Trust gratuito fino a 50 utenti (F11); prezzo del Tunnel: la pagina non lo dice | 0, senza account (F8) | 0, con 1 GB al mese, 20.000 richieste al mese, 1 dominio di sviluppo (F13, F14) | 0 con No-IP gratuito, da confermare ogni 30 giorni (F15); router | 0 |
| **Semplicità** (chi non usa il terminale; dal telefono) | app Tailscale sul telefono (Android 8+ da Google Play, iOS 15+ da App Store, F6, F7), poi un indirizzo; sul PC va cambiato il `.env` e, per non esporre il portatile, serve codice nuovo (3.2) | app sul telefono; sul PC: abilitare HTTPS nella console web (F3), un comando una volta (`tailscale serve --bg 8765`, che resta attivo dopo i riavvii, F2b); su Linux `sudo` o l'operatore (F12) | come Serve, più un attributo nella policy (F5) | registrare un dominio, spostarlo su Cloudflare, creare il tunnel, installare `cloudflared` (F9, F10) | un comando; **l'indirizzo cambia a ogni avvio** (F8) | account, agente, un indirizzo fisso; pagina di avviso nel browser ogni 7 giorni (F13) | router, DNS dinamico, certificati da gestire; impossibile se l'operatore usa il CGNAT (non verificato per l'utente) | niente |
| **Windows e Linux** | sì (client ufficiali, F6) | sì; su Windows i comandi di porta non chiedono l'amministratore (F2) | sì (F5) | non verificato: le pagine lette (F9, F10) non elencano i sistemi né dicono come si installa `cloudflared` come servizio | come (b2) | non verificato | non dipende dal sistema (si configura sul router) | sì |
| **Avvio all'accensione con Gradiens** (ADR 0005, 0007) | Tailscale: servizio di sistema su Linux; su Windows serve "Run unattended", altrimenti senza accesso è scollegato (F16) | come (a1); Serve è dentro `tailscaled`: nessun secondo servizio da gestire | come (a2) | `cloudflared` è un secondo servizio da registrare (come, non verificato) | da rilanciare a ogni avvio, con indirizzo nuovo | secondo servizio (non verificato) | client DNS dinamico (router o programma) | — |
| **Che cosa resta esposto e a chi** | la porta a tutte le reti a cui è collegato il PC se si ascolta su `0.0.0.0` (per un portatile anche i Wi-Fi pubblici), oppure solo al tailnet se si ascolta sull'IP del tailnet (vedi 3.2) | **solo i dispositivi del tailnet**; Gradiens resta su 127.0.0.1 | **tutta internet**, nessuna autenticazione davanti (F5) | internet, ma con Cloudflare Access davanti (F11) | internet; con `--allowed-mail` codice via email davanti (F8) | internet; OAuth possibile sul gratuito (3 identità, F14) | internet, PC raggiungibile direttamente | nessuno |
| **HTTPS** | no (cifrato da Tailscale, F4) | sì, certificato Let's Encrypt; **i nomi della macchina e del tailnet finiscono nel registro pubblico Certificate Transparency** (F3) | sì, come Serve (F3, F5) | sì | sì | sì (F13) | da fare a mano | — |
| **`/api/spegni` e `Host`** (sezione 1.4) | spegnimento rifiutato (cliente 100.x, Prova 4); `Host` da aggiungere | Serve scrive `X-Forwarded-For` con l'IP del cliente sovrascrivendo quello ricevuto, e conserva l'`Host` (F2c, sorgente) → spegnimento rifiutato (Prova 5, riga 2); `Host` `*.ts.net` da aggiungere | come Serve | Cloudflare accoda l'IP del visitatore a `X-Forwarded-For` (F17) → rifiutato; `Host` pubblico da aggiungere | come (b2) (non verificato per i quick tunnel) | non verificato | dipende dal router (nessun proxy: cliente vero) | — |
| **Chi vede il traffico** | nessuno oltre ai due dispositivi (F4) | idem | i relay di Funnel non decifrano (F5) | Cloudflare (proxy inverso: non verificato su una pagina in questa sessione) | Cloudflare (idem) | ngrok (idem) | nessuno | — |
| **Se il servizio cambia condizioni** | Gradiens non cambia: si torna a (d) | si spegne Serve e si torna a (d) | idem | dominio e account da tenere | "no uptime guarantee", per prove (F8) | limiti che possono stringersi; credito di 5 $ per un anno (F14) | No-IP cancella il nome non confermato (F15) | — |
| **Limiti del gratuito che contano qui** | uso non commerciale (F1) | idem; HTTPS va abilitato nella console | beta; banda limitata e non configurabile; porte 443, 8443, 10000 (F5) | 50 utenti (F11) | 200 richieste contemporanee; niente SSE; indirizzo che cambia (F8) | 20.000 richieste al mese: l'avanzamento interroga ogni 2 s (`templates/avanzamento.html:5`), circa 300 richieste per un'esecuzione seguita per 10 minuti (stima) | conferma ogni 30 giorni (F15) | — |

### 2.4 Lettura della tabella

- Per l'uso dichiarato (solo l'utente, dai suoi dispositivi, Tailscale già attivo) le opzioni pubbliche (b) e (c)
  aggiungono rischio senza aggiungere niente: obbligano ad autenticazione, limiti e controlli che oggi mancano
  (sezione 3.3) e, per (b2), a comprare un dominio.
- Tra (a1) e (a2), **Serve vince sul portatile**: Gradiens resta su 127.0.0.1, quindi nessun Wi-Fi pubblico vede la
  porta; l'HTTPS è vero; il log di accesso registra l'IP del tailnet di chi chiede (grazie a `X-Forwarded-For`).
  Costa due passi una tantum in Tailscale (abilitare HTTPS, lanciare `tailscale serve --bg`) e la pubblicazione del
  nome della macchina nel registro dei certificati.
- (a1) resta un'alternativa senza certificati, ma solo se Gradiens ascolta sull'IP del tailnet, non su `0.0.0.0`, e
  questo chiede codice in più (sezione 3.2).

## 3. Protezioni minime per ogni opzione

### 3.1 Due correzioni utili in ogni caso

- **"Dal PC" che non dipende dal proxy.** Una funzione `dal_pc(request)` vera solo se (1) il cliente è `127.0.0.1` o
  `::1`, (2) l'intestazione `Host` è locale (`127.0.0.1`, `localhost`, `[::1]`, con qualunque porta) e (3) la
  richiesta non ha `X-Forwarded-For`. Una richiesta passata da un proxy sullo stesso PC ha di solito l'`Host`
  pubblico o una `X-Forwarded-For` (Serve: entrambe, F2c; Cloudflare: `X-Forwarded-For`, F17), quindi non vale come
  locale anche nelle righe 1 e 3 della Prova 5. CLI e pannello mandano `Host: 127.0.0.1:<porta>` e nessuna
  `X-Forwarded-For` (`app/cli.py:20`, `:81`): continuano a funzionare. Anche un tunnel SSH verso il PC
  (`ssh -L 8765:127.0.0.1:8765 …`) conta come "dal PC", ed è giusto: chi apre il tunnel ha già un accesso al PC.
- **Valori espliciti in uvicorn**: `proxy_headers=True, forwarded_allow_ips="127.0.0.1,::1"` in `uvicorn.Config`
  (`app/servizio.py:137`), come proposto dal documento 05 (2.7). Con Serve servono proprio questi valori: uvicorn
  deve fidarsi della `X-Forwarded-For` scritta da `tailscaled` su 127.0.0.1, così `request.client` e il log
  registrano l'IP del tailnet di chi chiede. Scritti nel codice, non cambiano più con una versione nuova di uvicorn o
  con la variabile d'ambiente `FORWARDED_ALLOW_IPS`.

### 3.2 Rete privata: (a1) e (a2)

**Che cosa serve come minimo**

| Protezione | (a1) diretto | (a2) Serve | Perché |
|---|---|---|---|
| Nome (e IP) del tailnet tra gli host consentiti | sì: nome MagicDNS corto, nome completo e IP `100.x` | sì: solo `<macchina>.<tailnet>.ts.net` | oggi rispondono 400 (Prova 1, 5). Mai `*`: il controllo dell'`Host` è l'unica difesa dal DNS rebinding, perché con il rebinding la pagina ostile è "della stessa origine" e può aggiungere anche `HX-Request` (comportamento noto dei browser, non provato qui) |
| Dove ascolta Gradiens | **non `0.0.0.0`** su un portatile: solo 127.0.0.1 più l'IP del tailnet, con due socket (`uvicorn.Server.run(sockets=[...])` li accetta, `uvicorn/server.py:85`) e un nuovo tentativo se all'avvio `tailscaled` non ha ancora l'indirizzo | 127.0.0.1, come oggi | con `0.0.0.0` la dashboard si apre da qualunque rete a cui è collegato il portatile |
| Rotte solo dal PC | sì | sì | vedi sotto |
| `dal_pc` e valori espliciti (3.1) | consigliati | **necessari** | con Serve tutte le connessioni arrivano da 127.0.0.1 |
| HTTPS | no (cifrato da Tailscale, F4; nessuna funzione della dashboard richiede HTTPS: `static/app.js` non usa API riservate alle pagine sicure) | sì, automatico | |
| Autenticazione nell'app | **no** | **no** | la fa Tailscale: entra solo chi ha un dispositivo collegato al tailnet con l'account dell'utente |
| Limite alle esecuzioni avviate da remoto | no | no | `/aggiorna` da Telegram ha già lo stesso potere; una alla volta (`ESE-02`) |
| Controllo dei nomi DNS nelle fonti (decisione 39) | no | no | l'indirizzo lo sceglie solo l'utente: la decisione 39 resta "solo i redirect" |

**Rotte solo dal PC anche dentro la rete privata.** Chiunque sia nel tailnet, o abbia in mano un dispositivo
dell'utente sbloccato, raggiunge tutto il resto. Oggi nel tailnet ci sono solo dispositivi dell'utente (sezione 2.1),
ma il piano gratuito ammette fino a 6 utenti (F1) e un dispositivo si può condividere. Le azioni da riservare al PC
sono quelle con danno duraturo o che riguardano il PC stesso:
- spegnimento (`/api/spegni`, già così);
- avvio all'accensione e icone (`/impostazioni/avvio`, `/impostazioni/avvio/icone`, e le icone di
  `/configurazione/completa`): riguardano il sistema del PC; su Windows l'avvio all'accensione chiede comunque la
  conferma sullo schermo (ADR 0005), le icone no (ADR 0009);
- cambio del bot e della chat (`/impostazioni/telegram/token`, `/conferma`, `/cambia-chat`): è il furto del canale
  di comando della sezione 1.7. `/cerca` e `/prova` restano libere (leggono o mandano un messaggio alla chat già
  confermata).

Restano raggiungibili da un dispositivo rubato: leggere, togliere i cuori, cambiare interessi e fonti, avviare
esecuzioni. **Non le proteggerei con una password**: per un solo utente il rimedio è fuori da Gradiens (blocco
dello schermo del telefono; togliere il dispositivo dal tailnet dalla console di Tailscale, passo non verificato su
una pagina in questa sessione), e le copie di sicurezza giornaliere coprono la perdita dell'Archivio.

**Integrazione con le Impostazioni** (versione completa, 6c-4): sezione **"Accesso da fuori casa"** nel gruppo
Funzionamento, accanto ad Avvio e Telegram.
- Interruttore "Apri la dashboard dai miei dispositivi Tailscale" e campo "Indirizzo Tailscale di questo PC" (si
  incolla `https://<macchina>.<tailnet>.ts.net`, Gradiens ne tiene solo il nome).
- Stato: spento; acceso con l'indirizzo da aprire (link); da sistemare se l'indirizzo manca. Testo e passi per Linux,
  per Windows e per il telefono, uno accanto all'altro (CLAUDE.md, Portabilità).
- Si cambia solo dal PC (è una rotta "solo dal PC").
- **Dove si salva**: interruttore e nome nel **database** (tabella `impostazioni`): sono impostazioni che si cambiano
  dalla dashboard (`struttura.md`, "Dati a runtime") e non sono segreti, quindi niente `.env` e niente `PER-04`.
  Nella versione minima il nome va invece a mano in `GRADIENS_HOST_CONSENTITI` nel `.env`, con un riavvio.
- **Fuori dalla repository**: niente. La configurazione di Serve la scrive Tailscale nel suo stato, ma la crea
  l'utente con un comando: è un'impostazione di Tailscale, come il login di Claude Code per `PER-03`. Se invece
  Gradiens lanciasse `tailscale serve` da solo, sarebbe una terza eccezione di `PER-03` e codice che cerca
  l'eseguibile di Tailscale su Windows e su Linux (`app/avvio_sistema.py`): per questo la proposta non lo fa.
- **Windows e Linux**: nessun codice specifico di un sistema; cambiano solo i passi a mano (4.2).

### 3.3 Tunnel pubblico (b1-b4) o port forwarding (c): che cosa diventerebbe obbligatorio

Se un giorno servisse aprire la dashboard da un dispositivo dove non si può installare Tailscale, prima di aprire il
tunnel servirebbe **tutto** questo:
1. **Autenticazione davanti all'app o nell'app.** Davanti: Cloudflare Access (gratuito fino a 50 utenti, F11, ma
   richiede il dominio), OAuth di ngrok (3 identità sul gratuito, F14), `--allowed-mail` del quick tunnel (codice via
   email, F8). Funnel non ha niente davanti (F5): l'autenticazione andrebbe nell'app (password con hash, cookie di
   sessione `Secure`, `HttpOnly`, `SameSite=Strict`, tentativi limitati).
2. **Rotte solo dal PC** come in 3.2 e `dal_pc` (3.1).
3. **Limite alle esecuzioni avviate dalla dashboard da remoto** (per esempio una ogni qualche ora): un estraneo con
   accesso esaurirebbe la quota delle 5 ore (sezione 1.7).
4. **Controllo dei nomi DNS** verso indirizzi privati e del tailnet, anche per i feed aggiunti a mano (opzione C della
   scheda 8 del documento 04; decisione 39; Prova 7d).
5. **Intestazioni contro l'incorniciamento** (`X-Frame-Options: DENY` o `Content-Security-Policy: frame-ancestors
   'none'`): oggi mancano (Prova 3).
6. **Host pubblico esatto** tra gli host consentiti, mai `*`; HTTPS sempre (nel caso (c) da gestire a mano).
7. **Log con l'IP vero** del visitatore (`X-Forwarded-For` o `CF-Connecting-IP`, F17).
8. Un link nel messaggio Telegram solo con l'autenticazione davanti.

Stima di tutto questo: L (più giorni). È il motivo principale per non scegliere un tunnel pubblico.

### 3.4 Lasciare così (d)

Nessuna protezione nuova necessaria. Restano consigliati i valori espliciti di uvicorn (3.1), già proposti dal
documento 05.

## 4. Raccomandazione

### 4.1 Per il caso dell'utente

**Tailscale Serve (a2)**, nella versione minima subito (6c-1, 6c-2, 6c-3, 6c-6) e in quella completa (6c-4, 6c-5)
solo se l'accesso da fuori casa si usa davvero. Perché:
- l'utente, i dispositivi e Tailscale ci sono già (decisioni 50-52): manca solo il telefono nel tailnet;
- Gradiens resta su 127.0.0.1: un portatile su un Wi-Fi pubblico non espone niente, e la frase "la dashboard ascolta
  solo sul PC (127.0.0.1)" dell'intervista 51 resta vera;
- HTTPS vero senza dominio e senza gestire certificati;
- nessun secondo servizio da avviare all'accensione: Serve sta dentro `tailscaled`, che è già un servizio di sistema;
- nessun legame nel codice: se Tailscale cambiasse condizioni, si spegne Serve e si torna a (d);
- nessuna autenticazione da scrivere: per un solo utente con i suoi dispositivi la rete privata basta, con le rotte
  pericolose riservate al PC.

**Se le esigenze cambiano**: un'altra persona → la si aggiunge al tailnet o le si condivide il dispositivo, e si
limita con la policy di Tailscale (F19) o leggendo `Tailscale-User-Login` che Serve aggiunge (F2); un dispositivo dove
non si può installare un'app → quick tunnel di Cloudflare con `--allowed-mail` solo per il tempo che serve, dopo le
protezioni di 3.3; un accesso pubblico stabile → dominio più Cloudflare Tunnel e Access (b2), con tutta la 3.3.

### 4.2 Scheda della proposta raccomandata

**Problema** (verificato, sezione 1):
- La dashboard ascolta solo su 127.0.0.1 (`app/servizio.py:137`, `app/configurazione.py:25`) e risponde solo a
  `127.0.0.1` e `localhost` (`app/configurazione.py:28`, `app/servizio.py:117`): dal telefono non si apre.
- Lo spegnimento "solo dal PC" (`app/servizio.py:50`) dipende dai valori predefiniti di uvicorn e da come un proxy
  scrive `X-Forwarded-For` (Prova 5).
- Chi raggiunge la dashboard può sostituire il bot o spostarne la chat (`dashboard/rotte_impostazioni.py:254-296`,
  Prova 7a) e cambiare l'avvio all'accensione e le icone (`:318-344`, Prova 7b), senza distinzione tra PC e remoto.

**Opzioni** (dettaglio nella sezione 2):

| Opzione | Pro | Contro |
|---|---|---|
| Lasciare così | zero rischio, zero lavoro | dal telefono solo Telegram |
| **Minima: Serve + nome nel `.env` + rotte solo dal PC** | poche ore di codice; nessuna migrazione | il nome si scrive a mano nel `.env` e serve un riavvio; niente link su Telegram |
| Completa: minima + sezione "Accesso da fuori casa" + link su Telegram | tutto dalla dashboard; un tocco da Telegram al resoconto | migrazione del database; controllo dell'`Host` riscritto (rischio sulla difesa dal DNS rebinding, da coprire con test) |
| Accesso diretto (a1) | niente certificati, nessun nome pubblicato | codice per ascoltare anche sull'IP del tailnet; `http` segnato come non sicuro dal browser |

**Impatto su Windows e Linux**
- Codice di Gradiens: nessuna differenza tra i sistemi; niente in `app/avvio_sistema.py`.
- Linux (dove gira oggi, decisione 2): Serve si configura una volta, con `sudo` o dopo aver reso l'utente "operatore"
  di Tailscale (F12); `tailscaled` è un servizio di sistema, attivo anche senza accesso (F16), coerente con l'ADR 0007.
- Windows (ADR 0001): stesso comando in PowerShell; per l'avvio senza accesso (ADR 0005) Tailscale va messo in "Run
  unattended", altrimenti all'accensione è scollegato fino all'accesso (F16).
- Telefono: app Tailscale (Android 8+ o iOS 15+, F6, F7) collegata allo stesso account; poi il browser.

**Passi di implementazione** (ognuno con la suite verde; proprietari da `struttura.md`; passi separati per
proprietario, decisione 32):

| # | Passo | File | Proprietario | Test |
|---|---|---|---|---|
| 1 | `dal_pc(request)` e la dipendenza `solo_dal_pc` (403 "Si fa stando al PC su cui gira Gradiens.") | `dashboard/comune.py` | frontend-engineer | `tests/dashboard/`: cliente `127.0.0.1` e `::1` con `Host` locale → vero; cliente `100.x` → falso; cliente `127.0.0.1` con `Host` `*.ts.net` → falso; con `X-Forwarded-For` → falso |
| 2 | `/api/spegni` usa `dal_pc`; `proxy_headers` e `forwarded_allow_ips` espliciti | `app/servizio.py` | backend-engineer | `tests/app/test_servizio.py`: l'app passata da `uvicorn.Config(...).load()` (senza porte, come la Prova 5) rifiuta lo spegnimento in tutte le righe della tabella 1.4 tranne il PC; lo stesso con `FORWARDED_ALLOW_IPS=*` nell'ambiente; `test_spegnimento_solo_dal_pc_stesso` resta verde |
| 3 | `solo_dal_pc` su avvio, icone, token, conferma e cambio di chat; in `completa` le icone solo dal PC; nei modelli `avvio.html` e `telegram.html` comandi disattivati e la nota "Si cambia stando al PC" quando la richiesta non è dal PC | `dashboard/rotte_impostazioni.py`, `dashboard/rotte_configurazione.py`, `templates/impostazioni/` | frontend-engineer | da un cliente `100.x`: 403 su ognuna e nessuna chiamata ai finti (come la Prova 7); dal PC: come oggi; un test che scorre `app.routes` e verifica che le rotte dell'elenco abbiano la dipendenza, così un rinomina non la perde |
| 4 | Pagina Aiuto: "Dashboard da fuori casa", con i passi a mano qui sotto per Linux, Windows e telefono | `templates/aiuto.html` | frontend-engineer | `test_aiuto` esteso: la sezione c'è |
| 5 | Documenti: `AMB-01`, `AMB-02`, `TG-03` (4.3), ADR 0013, `struttura.md` | `docs/` | architetto, analista dei requisiti | — |
| *fine della versione minima* | | | | |
| 6 | Colonne `accesso_remoto` e `indirizzo_remoto` in `impostazioni`, con migrazione e validazione del nome (si accetta un indirizzo incollato, si tiene solo il nome host) | `dati/modelli.py`, `dati/impostazioni.py`, `dati/migrazioni/` | backend-engineer | `tests/dati/`: validazione; migrazione su un database con dati |
| 7 | Controllo dell'`Host` che legge l'elenco del `.env` più il nome salvato se l'accesso è attivo (in `app.state`, aggiornato dalla rotta del passo 8), al posto di `TrustedHostMiddleware` | `app/servizio.py` | backend-engineer | stessi casi della Prova 1, porte, IPv6 tra parentesi, maiuscole; `test_nome_host_sconosciuto_rifiutato` verde |
| 8 | Sezione "Accesso da fuori casa" (3.2), rotta solo dal PC | `dashboard/rotte_impostazioni.py`, `templates/impostazioni/accesso.html` | frontend-engineer | da remoto 403; dal PC salva e il nome viene accettato subito |
| 9 | Link al resoconto in fondo al messaggio di fine esecuzione e nel messaggio di prova, solo con l'accesso attivo | `telegram/messaggi.py`, `telegram/bot.py` | backend-engineer | `tests/telegram/`: con l'accesso spento nessun link (come oggi); acceso: `https://<nome>/esecuzioni/<id>` |

Codici del riepilogo: 6c-1 = passi 1-2; 6c-2 = passo 3; 6c-3 = passo 4 più i passi a mano; 6c-6 = passo 5; 6c-4 =
passi 6-8; 6c-5 = passo 9.

**Passi a mano, fuori da Gradiens** (una volta; i comandi vengono dalle pagine F2, F2b, F3, F12, F16, F18; la
combinazione `tailscale serve --bg 8765` non compare così in una pagina: unisce l'esempio `tailscale serve 3000` e
l'opzione `--bg`):

| Dove | Passi |
|---|---|
| Console web di Tailscale (anche dal telefono) | 1. Controllare che il nome della macchina di Gradiens non contenga dati personali (sarà pubblico, F3) e cambiarlo se serve. 2. Pagina DNS: MagicDNS è già attivo; "Enable HTTPS" (F3). 3. Pagina Machines, macchina di Gradiens: "Disable Key Expiry", altrimenti dopo 180 giorni l'accesso si ferma fino a un nuovo login (F18; consigliato da Tailscale per i server) |
| Linux (macchina di Gradiens) | `sudo tailscale serve --bg 8765` (oppure una volta `sudo tailscale set --operator=$USER`, poi senza `sudo`, F12). Resta attivo dopo i riavvii (F2b). L'indirizzo è `https://<macchina>.<tailnet>.ts.net`: nome della macchina più nome del tailnet, che la console mostra nella pagina DNS (F20). Controllo: `tailscale serve status` (che cosa stampa con Serve attivo non l'ho visto). Per toglierlo: `tailscale serve reset` (F2b; oggi non ci sono altre configurazioni di Serve) |
| Windows (se Gradiens gira lì) | PowerShell: `tailscale serve --bg 8765` (se `tailscale` non è nel `PATH`, il percorso completo dell'installazione: non verificato). Icona di Tailscale → Preferences → "Run unattended" (F16) |
| Gradiens | versione minima: aggiungere il nome a `GRADIENS_HOST_CONSENTITI` nel `.env` (JSON, per esempio `["127.0.0.1","localhost","<macchina>.<tailnet>.ts.net"]`) e riavviare; versione completa: incollare l'indirizzo nella sezione "Accesso da fuori casa" |
| Telefono | installare Tailscale (Google Play o App Store, F6, F7), accedere con lo stesso account, aprire `https://<macchina>.<tailnet>.ts.net`; tenere attivo il blocco dello schermo |
| Portatile, se diverso dalla macchina di Gradiens | installare Tailscale e accedere con lo stesso account |

Se si cambia `GRADIENS_PORTA`, va rifatto anche il comando di Serve.

**Rischi**
- Il comportamento di Serve su `X-Forwarded-For` e `Host` l'ho letto nel sorgente del ramo principale di Tailscale
  (F2c), non nella documentazione né nella versione 1.104.7 installata. `dal_pc` non ne dipende (guarda anche `Host`
  e la presenza dell'intestazione), quindi un cambiamento renderebbe solo meno preciso il log.
- Nomi della macchina e del tailnet nel registro pubblico dei certificati (F3): irreversibile una volta emesso il
  certificato.
- Dispositivo rubato e sbloccato: legge e modifica tutto tranne le rotte solo dal PC (3.2).
- Gradiens spento o portatile in sospensione: dal telefono si vede un errore di Serve, non "Gradiens è spento" (che
  cosa mostra Serve non l'ho verificato); da remoto non si riaccende (intervista 30).
- Versione completa: il passo 7 riscrive la difesa dal DNS rebinding; i test devono coprire gli stessi casi di oggi.

**Stima dello sforzo** (stima): minima 0,5-1 giorno (passi 1-5); completa 2-2,5 giorni (passi 1-9). I passi manuali
richiedono circa mezz'ora all'utente (stima).

### 4.3 Requisiti, decisioni e ADR toccati: testo proposto

- **`AMB-01`**: "L'applicazione gira su un computer di casa, con Windows 11 o con Linux, con le stesse funzioni.
  L'installazione usata ogni giorno è oggi un portatile Linux (Debian 13). Da fuori casa la dashboard si apre dai
  dispositivi dell'utente collegati alla sua rete Tailscale. Vedi ADR 0001 e ADR 0013."
- **`AMB-02`**: "L'applicazione non è esposta su internet. La dashboard ascolta solo su `127.0.0.1`; da fuori casa la
  raggiungono solo i dispositivi della rete Tailscale dell'utente, tramite Tailscale Serve sullo stesso PC, con
  HTTPS. Si fanno solo dal PC su cui gira Gradiens: spegnimento, avvio all'accensione, icone del pannello, cambio del
  bot o della chat Telegram."
- **`TG-03`**, ultimo capoverso: "Se l'accesso da fuori casa è attivo, in fondo al messaggio c'è il link al resoconto
  dell'esecuzione nella dashboard; il link funziona solo dai dispositivi della rete Tailscale. Altrimenti il messaggio
  non contiene link alla dashboard." (Nella versione minima il capoverso resta com'è.)
- **Intervista 51**: nota "Superata in parte dall'ADR 0013: la dashboard ascolta ancora solo su 127.0.0.1, ma con
  l'accesso da fuori casa attivo il messaggio contiene il link."
- **ADR 0001**: nota in fondo "Aggiornamento (decisione 2 dei miglioramenti): l'installazione usata ogni giorno è un
  portatile Linux; il PC Windows resta supportato. Per l'accesso da fuori casa vedi ADR 0013." La conseguenza "L'app
  non va esposta su internet" resta vera.
- **`struttura.md`, "Sicurezza della dashboard"**: "Ascolta solo su 127.0.0.1; da fuori casa passa da Tailscale Serve
  sullo stesso PC (ADR 0013). Risponde solo ai nomi host consentiti: quelli del `.env` e, con l'accesso da fuori casa
  attivo, il nome Tailscale salvato nelle Impostazioni (difesa dal DNS rebinding; mai `*`). Le richieste che
  modificano qualcosa devono avere `HX-Request` o `X-Gradiens-Cli` (difesa CSRF). Le rotte solo dal PC (spegnimento,
  avvio all'accensione, icone, token e chat di Telegram) usano `comune.dal_pc`: cliente `127.0.0.1` o `::1`, `Host`
  locale, nessuna `X-Forwarded-For`. uvicorn riceve `proxy_headers` e `forwarded_allow_ips` espliciti. Non c'è
  autenticazione: la fa Tailscale. Un tunnel pubblico richiede prima le protezioni della sezione 3.3 della proposta
  6c." Corregge anche la discrepanza segnata nel README ("solo da 127.0.0.1": il codice accetta anche `::1`).

### 4.4 Il link alla dashboard nel messaggio Telegram

L'intervista 51 l'aveva tolto perché la dashboard ascoltava solo sul PC: un link non si sarebbe aperto dal telefono.
Con Serve si apre, quindi **conviene rimetterlo, a tre condizioni**:
1. solo con l'accesso da fuori casa attivo e il nome salvato (versione completa): altrimenti il link non funziona;
2. un solo link, al resoconto di quell'esecuzione (`/esecuzioni/<id>`), in fondo al messaggio: il messaggio resta
   corto (intervista 52);
3. solo l'indirizzo del tailnet, mai un indirizzo pubblico senza autenticazione davanti (3.3). Il nome finisce sui
   server di Telegram (per i bot la cifratura da un capo all'altro non c'è: non verificato su una pagina in questa
   sessione), ma è già pubblico nel registro dei certificati (F3) e fuori dal tailnet non apre niente.

Nella versione minima il messaggio resta senza link: l'indirizzo è solo nel `.env`, mescolato agli altri nomi
consentiti, e il bot non saprebbe quale usare.

## 5. ADR proposti e domande per l'utente

### 5.1 ADR proposti

**ADR 0013 — La dashboard si apre da fuori casa solo dal tailnet, tramite Tailscale Serve** (stato: proposto;
diventa "accettato, da implementare" se l'utente risponde sì a D1 e D2).
- Decisione: Gradiens continua ad ascoltare solo su 127.0.0.1; l'accesso da fuori casa passa da `tailscale serve`
  sullo stesso PC, configurato una volta dall'utente; il nome `*.ts.net` entra tra gli host consentiti; spegnimento,
  avvio all'accensione, icone e cambio di bot o chat si fanno solo dal PC (`dal_pc`); nessuna autenticazione
  nell'app.
- Alternative scartate: accesso diretto all'IP del tailnet (codice per due indirizzi; `0.0.0.0` esporrebbe il
  portatile sui Wi-Fi pubblici); Tailscale Funnel e ngrok (pubblici, autenticazione da scrivere); Cloudflare Tunnel
  (richiede un dominio); quick tunnel (indirizzo che cambia, solo per prove); port forwarding con DNS dinamico
  (esposizione diretta, certificati a mano); lasciare così.
- Conseguenze: `AMB-01`, `AMB-02`, `TG-03` e `struttura.md` cambiano (4.3); i nomi della macchina e del tailnet sono
  pubblici nel registro dei certificati; un tunnel pubblico richiederà un ADR nuovo con le protezioni di 3.3.

Non propongo un ADR per la macchina di riferimento: basta una nota all'ADR 0001 e il nuovo `AMB-01` (domanda D5).

### 5.2 Domande per l'utente (una alla volta, nell'ordine)

| # | Domanda | Risposta consigliata e perché |
|---|---|---|
| D1 | Vuoi aprire la dashboard da fuori casa, e come: Tailscale Serve, accesso diretto all'IP del tailnet, o lasciare così? | **Tailscale Serve.** Hai già Tailscale; Gradiens resta su 127.0.0.1, quindi il portatile non espone niente sulle reti degli altri, e l'HTTPS è automatico. |
| D2 | Accetti di abilitare i certificati HTTPS del tailnet, sapendo che il nome della macchina e quello del tailnet finiscono in un registro pubblico? | **Sì, dopo aver controllato (o cambiato) il nome della macchina.** È la condizione per Serve; il nome del tailnet non dice chi sei (F3). Se la risposta è no, l'alternativa è l'accesso diretto (a1). |
| D3 | Versione minima (nome scritto una volta nel `.env`) o completa (sezione nelle Impostazioni e link su Telegram)? | **Minima ora.** Costa mezza giornata e basta per un utente che usa il terminale; la completa (2 giorni) si fa se dopo qualche settimana la dashboard dal telefono si usa davvero. |
| D4 | Quali azioni restano solo dal PC? | **Spegnimento, avvio all'accensione, icone, cambio di bot o di chat Telegram.** Sono quelle con danno duraturo o che riguardano il PC; tutto il resto da remoto, come già con Telegram. |
| D4 bis | (dopo la rilettura) Accetti che da remoto restino possibili l'avvio di esecuzioni, la modifica dei tetti, la rimozione dei cuori e l'eliminazione di interessi e fonti? | **Sì per le esecuzioni e la lettura; da valutare "solo dal PC" anche per tetti, cuori ed eliminazioni**, perché un telefono rubato nel tailnet potrebbe consumare la quota o svuotare l'Archivio. |
| D5 | `AMB-01` e ADR 0001 vanno aggiornati per dire che Gradiens oggi gira sul portatile Linux? | **Sì, con il nuovo `AMB-01` e una nota all'ADR 0001**, senza un ADR nuovo: la scelta "un solo computer di casa, niente server" resta la stessa. |

## 6. Fonti esterne

Tutte lette il **15 novembre 2026**. Le date tra parentesi sono quelle indicate dalle pagine stesse.

| # | URL | Che cosa ne ho preso | Che cosa non dice |
|---|---|---|---|
| F1 | https://tailscale.com/pricing | Piano gratuito: 0 $, "Free forever", "Up to 6 users", "Unlimited user devices", uso non commerciale | Se Serve, Funnel e HTTPS sono inclusi (la tabella non si leggeva per colonne); nessuna data di aggiornamento |
| F2 | https://tailscale.com/kb/1312/serve | Serve: solo dentro il tailnet; richiede i certificati HTTPS; esempio `tailscale serve 3000` verso `http://127.0.0.1:3000`; intestazioni `Tailscale-User-Login`, `-Name`, `-Profile-Pic`, tolte se arrivano dal cliente; consiglia di far ascoltare il servizio solo su localhost; inoltrare una porta non richiede root su nessun sistema | `X-Forwarded-For`, trattamento dell'`Host`, `--bg`, rinnovo del certificato |
| F2b | https://tailscale.com/kb/1242/tailscale-serve | `--bg`: resta attivo dopo un riavvio o `tailscale down`/`up`; `off` aggiunto al comando originale; `reset` toglie tutto; solo `http://127.0.0.1` come destinazione del proxy; sintassi cambiata dalla 1.52 | Porta HTTPS predefinita (gli esempi usano 443); intestazioni inoltrate |
| F2c | https://raw.githubusercontent.com/tailscale/tailscale/main/ipn/ipnlocal/serve.go (sorgente ufficiale, ramo principale) | Il proxy di Serve conserva l'`Host` ricevuto (`r.Out.Host = r.In.Host`), imposta `X-Forwarded-Host`, `X-Forwarded-Proto: https` sulle connessioni TLS e `X-Forwarded-For` con l'IP del cliente, sovrascrivendo quello ricevuto | Non è documentazione e non è la versione 1.104.7 installata |
| F3 | https://tailscale.com/kb/1153/enabling-https (validata il 10 dic 2025) | Passi nella console (pagina DNS, MagicDNS, "Enable HTTPS"); nomi delle macchine e del tailnet pubblicati nel registro Certificate Transparency ("Do not enable the HTTPS feature if any of your machine names contain sensitive information"); certificati Let's Encrypt di 90 giorni; "Connections between Tailscale nodes are secured with end-to-end encryption" | Se Serve rinnova da solo il certificato |
| F4 | come F3 | Cifratura da un capo all'altro tra i nodi; i browser non lo sanno e segnano `http` come non cifrato | — |
| F5 | https://tailscale.com/kb/1223/funnel | Funnel: beta; "available for all plans"; richiede 1.38.3+, MagicDNS, HTTPS, attributo `funnel`; porte 443, 8443, 10000; banda limitata e non configurabile; i relay non decifrano; DNS pubblico; nessuna autenticazione descritta | Valore dei limiti di banda |
| F6 | https://tailscale.com/download e https://tailscale.com/download/android | Client ufficiali per macOS, iOS, Windows, Linux, Android; Android da Google Play, "Requires Android 8 or later" | F-Droid |
| F7 | https://tailscale.com/download/ios | App Store, "Requires iOS 15 or later" | — |
| F8 | https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/ (aggiornata il 30 set 2026) | Quick tunnel: senza account né dominio; sottodominio casuale di `trycloudflare.com` che cambia a ogni creazione; per prove e sviluppo; 200 richieste contemporanee; niente SSE; nessuna garanzia di disponibilità; `--allowed-mail` con codice via email, "Access ends for everyone when the process stops" | Versione minima di `cloudflared` per `--allowed-mail`; durata della sessione |
| F9 | https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/ (aggiornata il 17 apr 2026) | `cloudflared` va installato e autenticato sul server | Dominio, prezzo, installazione come servizio |
| F10 | https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/ (aggiornata il 23 giu 2026) | "Before you publish an application through your tunnel, you must add a website to Cloudflare." | Se il comando di installazione registra un servizio |
| F11 | https://www.cloudflare.com/plans/sase-zero-trust.md (versione testuale della pagina dei piani) | Piano gratuito: 0 $, "50 users", ZTNA incluso, log per 24 ore | Il nome "Cloudflare Tunnel" e il suo prezzo |
| F12 | https://tailscale.com/docs/reference/troubleshooting/linux/linux-operator-permission (validata il 18 feb 2026) | Su Linux `tailscaled` gira come root; `sudo tailscale set --operator=<USERNAME>`; l'operatore gestisce Serve e Funnel verso porte senza `sudo` | — |
| F13 | https://ngrok.com/docs/pricing-limits/free-plan-limits/ | Gratuito: 3 endpoint, 1 dominio di sviluppo `*.ngrok-free.app` che resta uguale, 1 GB al mese, 20.000 richieste al mese (4.000 al minuto); pagina di avviso prima del traffico HTML dei browser, saltata per 7 giorni dopo "Visit"; niente domini propri | Autenticazione di base; data di aggiornamento |
| F14 | https://ngrok.com/pricing | 0 $ con credito una tantum di 5 $ per un anno; 3 identità OAuth/OIDC al mese; restrizioni per IP dell'account non incluse | Autenticazione di base; limiti d'uso (personale o commerciale) |
| F15 | https://www.noip.com/free e https://www.noip.com/faqs | Gratuito: 1 nome; "Free Dynamic DNS hostnames must be confirmed every 30 days", altrimenti cancellati | Certificati HTTPS |
| F16 | https://tailscale.com/kb/1088/run-unattended | Windows: senza "Run unattended" Tailscale si scollega all'uscita e al riavvio fino al nuovo accesso; come attivarlo (menu o `tailscale set --unattended=true`); Linux: `tailscaled` è un servizio di sistema attivo anche senza utenti collegati | Che su Linux parta all'accensione (implicito) |
| F17 | https://developers.cloudflare.com/fundamentals/reference/http-headers/ (aggiornata il 28 ott 2026) | Cloudflare imposta `X-Forwarded-For` come `CF-Connecting-IP` o accoda l'IP se l'intestazione esiste già | Il caso dei quick tunnel |
| F18 | https://tailscale.com/kb/1028/key-expiry | Scadenza predefinita di 180 giorni; alla scadenza le connessioni si fermano fino a un nuovo login; "Disable Key Expiry" dalla pagina Machines; consigliato per i server fidati | — |
| F19 | https://tailscale.com/kb/1018/acls | Il tailnet nuovo permette a tutti i dispositivi di parlarsi; le regole `src`/`dst` con porta limitano l'accesso | Un esempio pronto per "solo i miei dispositivi verso la porta 443 di una macchina" |
| F20 | https://tailscale.com/kb/1081/magicdns (validata il 5 gen 2026) | Nome corto e nome completo `<macchina>.<tailnet>.ts.net` equivalenti; attivo per default nei tailnet creati dal 20 ottobre 2022 | Il funzionamento su Android e iOS |
| F21 | https://core.telegram.org/bots | "Bots can't start conversations with users. A user must either add them to a group or send them a message first.": per spostare il bot sulla propria chat un estraneo deve prima scrivergli `/start` (sezione 1.7) | — |

Fonti interne (codice, non rete): uvicorn 0.54.0 e Starlette 1.10.0 installati nella `.venv`
(`uvicorn/config.py:225-228, 361-365, 543-544`; `uvicorn/middleware/proxy_headers.py:28-63, 169-187`;
`uvicorn/server.py:85`; `starlette/middleware/trustedhost.py:41-56`, che toglie la porta e accetta modelli come
`*.esempio.it`).

## Che cosa non ho potuto verificare

- **Serve dal vero**: non ho lanciato `tailscale serve` (vietato per questo incarico). Intestazioni e `Host` vengono dal
  sorgente del ramo principale (F2c), non dalla versione 1.104.7 né da una richiesta vera; che cosa vede il telefono
  quando Gradiens è spento non l'ho visto.
- **Uvicorn in ascolto**: la Prova 5 usa lo strato che `uvicorn.Config.load()` costruisce, senza aprire porte; non ho
  provato un server vero con un proxy vero (S-14 del documento 02 resta "dimostrato sullo strato", non "dal vero").
- **Indirizzo effettivo di ascolto del Gradiens dell'utente**: sulla porta 8765 non ascoltava niente; non ho letto
  il `.env`, quindi non so se la porta o l'indirizzo sono stati cambiati.
- **Quale "portatile"**: se il portatile da cui l'utente vuole aprire la dashboard (decisione 50) è la stessa
  macchina Linux su cui gira Gradiens (decisione 6) o un altro; nel tailnet oggi c'è solo il PC Windows oltre a questa.
- **Togliere un dispositivo dal tailnet** dalla console (rimedio per un telefono rubato, 3.2): non letto su una pagina.
- **Ramo Windows**: comportamento di `tailscale serve` su Windows oltre a quanto dicono F2 e F16; percorso di
  `tailscale.exe`; che cosa fa la conferma UAC chiesta da una richiesta remota se nessuno è al PC oltre al timeout di
  300 s di `_esegui` (`app/avvio_sistema.py:106`).
- **Cloudflare e ngrok**: che terminino il TLS sui loro server (vedono il traffico in chiaro) e come si installano come
  servizi; come i quick tunnel scrivono `X-Forwarded-For`.
- **CGNAT e router** dell'utente per l'opzione (c).
- **Rinnovo automatico del certificato di Serve**: nessuna pagina letta lo dice.
- **Firewall della macchina Linux**: non ho controllato le regole (servono i permessi di amministratore); conta solo
  per l'opzione (a1) con `0.0.0.0`.
- **Telegram**: che i messaggi dei bot non siano cifrati da un capo all'altro (4.4) non l'ho letto in questa sessione.
- **Suite**: `uv run --frozen pytest` verde il 15 nov 2026 (181 passati), **escluso** apposta
  `tests/app/test_avvio_reale.py`, che lancia un processo vero di Gradiens (vietato per questo incarico).
