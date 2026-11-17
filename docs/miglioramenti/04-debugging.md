# Fase 4: debugging difficile (analisi)

**Data**: 14 novembre 2026. **Stato**: chiusa il 15 novembre 2026; le schede con una soluzione pronta sono state corrette il 17 novembre (vedi [README.md](README.md), "Fatto"). **Versione corta per scelta dell'utente**: schede

> **Decisioni dell'utente (15 novembre 2026)**, numeri 36-43 di [decisioni.md](decisioni.md): l'esclusione "sponsorizzati" non si applica più ai video; **nessun margine di rilettura** nell'ADR 0011 (rischio accettato: i siti con feed in ritardo perdono articoli); nessun'altra prova con l'LLM sui video; solo i redirect controllati contro la rete di casa; attesa della rete a 15 minuti e fallimento per rete che non conta per il recupero; `/pausa` e `/riprendi` restano come oggi, documentati; nessun ripristino automatico dopo una migrazione fallita; `gradiens aggiorna` resta spento e lo dice se il servizio non riparte.
complete solo per i sospetti gravi e per i problemi di interazione tra componenti; il resto è in due tabelle di rimandi.

Riferimenti `file.py:riga` relativi a `src/gradiens/`; quelli dei test relativi alla radice. Sigle: `S-nn` sono i sospetti del
[documento 02](02-test-e-copertura.md) (sezione 4), `T-nn` i suoi test di caratterizzazione, `R-nn` i passi di refactoring del
[documento 03](03-revisione-architetturale.md), `P4-nn`, `L-nn` e `D-nn` le prove, le letture dei log e le letture del
database di questa fase (registro in fondo). Gravità e sforzi sono **stime**: sforzo S = 1-2 ore, M = mezza giornata. In ogni
scheda "dimostrato" vuol dire provato con una prova o letto nei log veri; "probabile" e "ipotesi" sono dichiarati come tali.

## Riepilogo

**Che cosa è stato fatto.** Letti il codice dei moduli coinvolti, 54.155 righe di log veri (6-14 novembre), il database e le sue
copie in sola lettura. 18 prove usa e getta, tutte senza LLM, senza rete esterna e senza toccare il progetto (registro in
fondo). Una prova non è stata fatta perché vietata: due servizi veri sulla stessa porta.

**Le tre cose più importanti.**
1. **S-01 (video esclusi)**. Il verdetto dell'LLM non è stabile: nei tre blocchi misti delle esecuzioni vere i video sono
   stati segnalati 7 volte su 7, nel blocco di soli video della prova di oggi 1 volta su 7. Con gli stessi interessi
   (D-01), lo stesso prompt (in vigore dal 7 novembre) e lo stesso modello. La causa del verdetto è **probabile** (il video è una minoranza in un
   blocco misto), non provata. La correzione, dopo la rilettura: l'esclusione "sponsorizzato" **non si applica ai video** (non a tutto ciò
   che non è un sito: per arXiv farebbe danni, vedi "Esito della rilettura"); **non dipende dalla causa**.
2. **S-21 con l'ADR 0011**. Oggi un feed in ritardo fa solo arrivare gli articoli in ritardo, perché a ogni esecuzione si
   rilegge la finestra intera. Con "coperto fino a" come scritto nell'ADR 0011 gli articoli pubblicati nelle ore di ritardo
   del feed prima di ogni esecuzione **non si raccolgono mai** (P4-02), se il ritardo è minore dell'intervallo tra le
   esecuzioni: nella prova del revisore 12 articoli su 41, con stato "ok". Va deciso prima di scrivere il codice dell'ADR.
3. **Guasti che nessuno segnala**: un database bloccato lascia l'esecuzione "in corso" per sempre e blocca tutti e quattro i
   canali di avvio (S-06, P4-03); una migrazione fallita a metà cancella la copia pulita dopo 4 avvii (S-18, P4-07);
   `gradiens aggiorna` dice "aggiornato" anche se il servizio non riparte (P4-10).

**Nei log veri** (L-01, L-06): nessun "database is locked", nessun errore 500, il ciclo di eventi mai fermo più di circa 1 s,
nessun avviso di esecuzione fallita per risposte dell'LLM inattese. Sono stati osservati: 9 errori `Conflict` di Telegram
(due bot insieme), 1 secondo servizio che parte e poi scopre la porta occupata, 3 avvii su 16 (contando anche quello del 13 novembre alle 19:56, con lo stesso criterio) con la rete arrivata dopo
più di 4 minuti. I problemi di questo documento sono quindi in gran parte **latenti**: costano poco da correggere e molto se
capitano.

| Scheda | Codice | Gravità | Causa | Correzione in breve | Sforzo | Serve dall'utente |
|---|---|---|---|---|---|---|
| 1 | S-01 video esclusi | alta | meccanismo dimostrato; verdetto: probabile | l'esclusione "sponsorizzato" non si applica ai video, che vanno alla valutazione (per arXiv resta com'è) | S | domande 1 e 3; salvare oggi il feed del canale (A-1, A-2) |
| 2 | S-21 feed in ritardo (con ADR 0011) | alta se l'ADR resta com'è, media oggi | dimostrata (ritardo reale misurato una volta) | margine di rilettura legato al ritardo misurato del feed, dentro l'ADR 0011 (non 2 giorni fissi; e 6a-5 a parte) | S-M | domanda 2 |
| 3 | S-06, S-08 database bloccato | media | dimostrata; innesco reale non osservato | `termina` riprovato, `avanzamento` azzerato sempre, motivo leggibile | S | log (A-3) |
| 4 | S-05 con S-02, S-04, S-07 | media | dimostrata | `_tutti` che dà la precedenza alla quota; controllo di forma in un solo punto; motivo leggibile | M | niente |
| 5 | S-18 migrazione a metà | media (alta per l'ADR 0011) | dimostrata | copia pulita mai sovrascritta; la transazione esplicita va riprogettata (quella provata fa perdere dati: vedi "Esito della rilettura") | M | domanda 7 |
| 6 | S-11 con S-37 secondo servizio | media | meccanismo dimostrato; innesco reale raro | da ripensare: la porta riservata non basta (vedi "Esito della rilettura"); da valutare un file di blocco in `.gradiens/` | M | prova CI su Windows (A-6) |
| 7 | S-12 due bot | bassa-media | dimostrata | un `Lock` attorno ad `avvia` e `_riprova` | S | A-5 |
| 8 | S-32 redirect di robots.txt | media (sicurezza), poco probabile | dimostrata con socket veri | seguire i redirect a mano controllando l'indirizzo | S | domanda 4 |
| 9 | S-09 ora solare | bassa | dimostrata | `avviate_dal` a ogni scadenza | S | niente |
| 10 | I-1 programmatore e manuale | bassa | nessun difetto dimostrato | nessuna; facoltativo: rendere visibile la programmata saltata | - | niente |
| 11 | I-2 bot e pausa | bassa-media | dimostrata (3 punti) | decisioni; modulo che non riscrive la pausa | S | domanda 6, A-4 |
| 12 | I-3 aggiornamento | media | 3 punti dimostrati, Windows da indagare | verificare la ripartenza; spegnere prima di chiudere la porta; prova Windows | S-M | domanda 8, A-6, A-7 |
| 13 | I-4 rete che arriva tardi | media | dimostrata; frequenza bassa | attesa a 15 minuti; recupero che non conta il fallimento per rete | S | domanda 5 |
| 14 | I-5 cache e robots.txt | bassa | dimostrata | non ricordare i verdetti 5xx oltre l'esecuzione | S | niente |
| 15 | C-1 prove Windows non fatte | da indagare | manca la prova | nessuna: servono le prove | - | A-6 |

**Ordine consigliato.** (1) S-01, indipendente da tutto. (2) Prima del codice dell'ADR 0011: S-06 (il salvataggio di "coperto
fino a" sta nello stesso `finally`), S-18 (la migrazione dell'ADR), S-21 (il margine). (3) Il resto quando si tocca quel
codice. I test di regressione vanno scritti prima di ogni correzione; dove coincidono con un T-nn del documento 02 è
indicato.

**Compatibilità con il piano R-01...R-04.** Nessuna correzione richiede un passo R-nn e nessuna lo contraddice.
S-01 e S-05 toccano `filtra` e `_tutti`, che R-03 sposta in `prefiltro.py` e `parallelo.py`: se la correzione precede R-03
i test T-09, T-26, T-27, T-28 si ribaltano nello stesso commit, se segue R-03 si modifica il codice nel suo posto finale; in
entrambi i casi il commit è piccolo. S-06 non tocca `Avanzamento` (R-01): cambia solo dove `self.avanzamento` torna `None`.
S-21 e S-18 stanno nel codice che l'ADR 0011 e R-04 riscrivono (`raccolta.py`, `database.py`). La sessione unica (A-08)
resta com'è: nessuna correzione aggiunge un `await` tra una modifica e il suo `commit`. A-09 diceva di correggere la famiglia
S-02/S-04/S-05/S-07 in questa fase: è la scheda 4.

**Che cosa non ho potuto verificare.** Il verdetto vero dell'LLM sui video (serve una chiamata: vietata); due servizi veri
avviati insieme (vietato: "gradiens avvia"); tutto il ramo Windows (file in uso con il pannello aperto, UAC, icone, semantica
del `bind`); se `--json-schema` di Claude Code rende impossibili le risposte di forma inattesa; il ritardo del feed di
redhotcyber in giorni diversi dal 12 novembre; la causa dell'unico `Conflict` del 12 novembre alle 14:21.

---

## Esito della rilettura (15 novembre 2026)

Rilettura mirata, su cause e correzioni. **Le cause dichiarate reggono quasi tutte** (il revisore ha rifatto
cinque prove). **Tre correzioni farebbero danni** così come sono scritte nelle schede, e altre vanno
ristrette. L'autore è stato interrotto dal limite d'uso prima di riscrivere le schede: le correzioni sono
riportate qui e richiamate da un avviso in testa a ogni scheda interessata. **Dove questa sezione e una scheda
dicono cose diverse, vale questa sezione.**

**Correzioni che non reggono**

1. **Scheda 5, migrazione fallita (S-18).** La "migrazione in transazione esplicita" provata in P4-07 sposta
   il `PRAGMA foreign_keys = OFF` dentro la transazione, dove SQLite lo ignora. Prova del revisore: database
   alla 0008 con 2 pertinenze, aggiornamento all'ultima versione: con il codice di oggi restano 2, con la
   variante proposta diventano 0 (la ricreazione di `notizie` nella 0009 cancella a cascata). P4-07 e il test
   T-43 usano solo `add_column` e non vedono il problema; `foreign_key_check` vuoto non rileva righe cancellate
   a cascata. **Correzione riformulata**: il PRAGMA va impostato sulla connessione del driver prima che si apra
   qualunque transazione; il test di regressione deve fare una migrazione che ricrea una tabella con figlie
   in cascata e contare le righe figlie prima e dopo. Finché non c'è quel test, non toccare `migra`.
2. **Scheda 6, secondo servizio (S-11).** Riservare la porta e passarla a uvicorn non basta: uvicorn la mette
   in ascolto solo dopo l'avvio, e nel frattempo un secondo processo riesce a legarsi lo stesso (provato su
   Linux con `SO_REUSEADDR`), quindi eseguirebbe comunque migrazioni e `segna_interrotte`. Mettendola subito
   in ascolto, durante l'avvio la porta accetta ma non risponde: la correzione B ("nessuna risposta =
   occupato") scambierebbe per occupato ogni avvio lento. Con il socket passato, inoltre, un errore di uvicorn
   esce senza lo spegnimento ordinato. **Da ripensare**: una strada da valutare è un file di blocco in
   `.gradiens/` preso prima di toccare il database, con il suo comportamento su Windows e su Linux e dopo un
   arresto brusco. Nessuna correzione è pronta.
3. **Scheda 2, feed in ritardo e ADR 0011 (S-21).** Con la finestra di 3 giorni ed esecuzioni giornaliere un
   margine fisso di 2 giorni riporta il punto di partenza a quello di oggi: la raccolta incrementale non
   ridurrebbe più niente, nemmeno per hwupgrade. E non è "senza richieste in più": aggiunge la lettura della
   sitemap a ogni esecuzione. **Correzione riformulata**: il margine va legato al ritardo misurato del feed
   di quel sito (la distanza tra la sua ultima voce e l'ora della raccolta), non a un valore fisso. Va deciso
   prima di scrivere il codice dell'ADR 0011.

**Correzioni da restringere**

4. **Scheda 1, video YouTube (S-01).** L'esclusione degli sponsorizzati va tolta **solo ai video**, non a
   tutto ciò che non è un sito. Per arXiv i paper segnalati diventerebbero promossi ed entrerebbero nel tetto:
   con tetto 1, un paper segnalato più recente e uno pertinente più vecchio, oggi si salva il secondo, con la
   correzione larga nessuno (il pertinente finisce oltre il tetto ed è segnato visto). L'ADR 0010 aveva
   scartato un'opzione proprio per questo motivo. Cambiare il testo di `WEB-23` resta una modifica di
   requisito, da dichiarare.
5. **Scheda 4 (b).** Non togliere gli `except QuotaEsaurita: raise` (vedi l'avviso della scheda).
6. **Schede 6 C e 12 b.** Tra `esecutore.ferma()` e l'arresto del server il programmatore e le rotte restano
   attivi: un'esecuzione può partire in quei secondi ed essere poi interrotta; la correzione C non copre
   SIGTERM e Ctrl+C. Entrambe toccano `app/servizio.py`: la decisione 35 dell'utente (bot e servizio restano
   come sono) riguarda il refactoring, non la correzione di un bug, ma la correzione richiede comunque il suo
   test (T-40 o una sua parte).
7. **Schede 7, 9, 13, 14**: vedi gli avvisi in testa a ciascuna.

**Il feed in ritardo, precisato.** Prova del revisore con pubblicazione continua e 6 esecuzioni: con un
ritardo di 12 ore e l'ADR 0011 com'è scritto si perdono 12 articoli su 41, con stato "ok" e nessun guasto
(oggi 0 persi). Con un ritardo di 36 ore ed esecuzioni ogni 24 il feed non dà voci nuove, la cascata prosegue
e la sitemap porta gli articoli: a regime non si perde niente, ma a ogni esecuzione scatta il guasto "feed
fermo" e ogni 3 esecuzioni il profilo si rigenera (`WEB-24`). "Tutti persi, stato nessun articolo nuovo" vale
solo per i siti che hanno solo il feed. La perdita richiede che la cascata si fermi al feed in ritardo: non
viene dal solo punto di partenza.

**Prove che l'utente deve raccogliere, avvertenze.** A-6.1 e A-6.2 reinstallano pacchetti nell'ambiente vero
(con download): prima va spento il servizio, altrimenti un errore non si può attribuire al pannello. A-6.3
scarica tutte le dipendenze e contatta GitHub. A-1 su Windows: con Windows PowerShell 5.1 `Invoke-WebRequest`
può richiedere `-UseBasicParsing` (non verificato). A-3 su Windows: va aggiunta la ricerca di "Esecuzione .*
fallita", presente nell'elenco per Linux. A-4 è sicura: non consuma quota.

**Conteggi dai log ricontati**: 9 errori `Conflict` di Telegram, 56 avvii, 1 "address already in use", 0
"locked".

**Parti non rilette**: il ciclo di eventi fermo (P4-03), la tabella di P4-06, le prove P4-05, P4-10, P4-11
A-C e P4-12; le schede 10, 11 e 15 nei dettagli; tutto il ramo Windows; i rimandi ai passi R-nn.

## Schede

### Scheda 1. S-01: i video YouTube escono tutti come "sponsorizzato o offerta"

> **Dopo la rilettura**: la correzione A ("l'esclusione vale solo per i siti") **va limitata ai video** (tipi `video` e `short`). Estesa ad arXiv farebbe entrare nel tetto i paper segnalati come sponsorizzati, facendo perdere paper pertinenti (provato: tetto 1, si salva zero paper invece di uno), e si scontra con l'ADR 0010. Vedi "Esito della rilettura".

**Gravità**: alta (decisione 13: oggi YouTube non produce notizie). **Stato**: meccanismo **dimostrato**; causa del verdetto
dell'LLM **probabile, non dimostrata**; la correzione proposta non dipende dalla causa. **Sforzo** (stima): S, 2-3 ore.

**1. Percorso di esecuzione sospetto**
1. `fonti/youtube/__init__.py:88-103`: il sommario di un video è la descrizione del feed (`voce.get("summary")`, `:99`).
2. `esecutore.py:179-215`: le fonti si leggono in parallelo ma le candidate si accodano nell'ordine **arXiv, canali, siti**
   (`compiti` `:182-188`, `trovate += risultato` `:210`); `nuove` conserva l'ordine (`:263-264`). I video stanno dopo
   tutti i paper e prima di tutti gli articoli dei siti.
3. `esecutore.py:384`: blocchi da 30 voci. Dove finiscono i video (P4-01, con i numeri veri delle metriche):

   | Esecuzione | Prompt in vigore | Blocco dei video | Esito |
   |---|---|---|---|
   | 1 (6 nov) | istruzione senza il campo `sponsorizzate` (ipotesi: il codice dei commit `76e947c` o `f10a839`, stessa istruzione) | n. 3 di 3: 5 voci = 2 paper + 2 video + 1 articolo, id 2 e 3 | 2 short **mostrati** |
   | 8 (8 nov) | con il campo (commit `0aba1f2`, 7 nov) | n. 1 di 1: 2 voci = 1 video + 1 articolo, id 0 | 1 video escluso |
   | 9 (10 nov) | con il campo | n. 23 di 29: 30 voci = 17 paper + 3 video + 10 articoli, id 17-19 | 3 video esclusi |
   | 10 (11 nov) | con il campo | n. 14 di 17: 30 voci = 22 paper + 3 video + 5 articoli, id 22-24 | 3 video esclusi |
   | prova del 14 nov | con il campo | un blocco di 15 video (i 7 vecchi dentro), id 0-14 | 1 segnalato su 7 |

   (La prova del 14 novembre chiama "blocco di coda" quello delle esec. 9 e 10: non è l'ultimo, è il blocco di confine tra
   paper e siti.)
4. `esecuzione/prompt.py:24-34`, `:47-49`: ogni voce è `{id, titolo, sommario[:1500]}` (l'`id` è l'indice nel blocco); il
   prompt dice di escludere "i contenuti sponsorizzati e le offerte commerciali" e di restituirne gli id in `sponsorizzate`,
   senza dire che vale solo per i siti.
5. `llm/claude_code.py:76-110`: una chiamata `claude -p` per blocco, al massimo 3 insieme (processo esterno).
6. `esecutore.py:401-413`: `sponsorizzate = validi("sponsorizzate") - indici`; tutte le notizie non pertinenti, comprese le
   sponsorizzate, vanno in `notizie_viste` con un commit sulla sessione condivisa (`:406-408`); poi `m.escludi` registra
   fonte, titolo e motivo (`:409-411`).
7. `esecutore.py:263`: `gia_viste` toglie quegli indirizzi a ogni esecuzione. **L'esclusione è definitiva**; l'unico posto
   dove l'utente la vede è l'elenco delle escluse nel resoconto.

**2. Ipotesi in ordine di probabilità**
- **H1, contesto del blocco** (probabile). I video sono sempre una minoranza in un blocco misto (1 su 2, 3 su 30, 3 su 30);
  la riga di autopromozione del canale (invito a un corso a pagamento, in tutte le 15 descrizioni di oggi) risalta e,
  con l'istruzione di segnalare, viene letta come "offerta". Nel blocco di soli video la stessa riga è in 15 voci su 15 e
  passa per normale. Da sola non basta: nell'esec. 1 due short con una riga fissa di 48 caratteri (probabilmente la stessa autopromozione di oggi: D-02) passarono. Serve insieme
  al campo `sponsorizzate`, che c'è dal 7 novembre.
- **H2, caso** (possibile). Le chiamate sono 4 in tutto (3 vere e 1 di prova). Se ogni video avesse la stessa probabilità, 7
  su 7 contro 1 su 7 sarebbe poco probabile (test esatto di Fisher a una coda, calcolato a mano: circa 0,2%), ma i video di un
  blocco non sono indipendenti: il campione vero è di 3 chiamate contro 1.
- **H3, descrizioni diverse nei giorni 8-11** (possibile). Le 7 descrizioni non sono state salvate. Si sa solo che una riga
  fissa di 48 caratteri c'era già nei due short del 4 e 6 novembre (D-02); non è provato che sia la riga di oggi.
- **H4, difetto nel collegamento degli id** (esclusa). `validi`, `scartate` e `escludi` usano la stessa lista `blocco`
  (`:401-413`); P4-01 conferma gli id; gli altri tipi non vengono segnalati in massa (arXiv: 0 su 677 e 1 su 412; siti
  12-13%: 23 su 189 e 11 su 84).

**3. Esperimento più piccolo per ogni ipotesi**

| Ipotesi | Esperimento | Esito o che cosa serve |
|---|---|---|
| H1 | già fatto, senza LLM: composizione dei blocchi (P4-01) e stessi interessi (D-01) | i video sono sempre minoranza e nulla di diverso nel prompt: coerente, non conferma |
| H1 | con l'LLM: 1 video vecchio + 1 articolo di un sito, 3 volte (come l'esec. 8). Circa 2.500 token a chiamata (esec. 8 = 1.965 in + 507 out) | segnalato 2 volte su 3 o più: H1 |
| H1 | con l'LLM: i 7 video vecchi dentro un blocco da 30 con voci prese dal database (paper e articoli già salvati), 3 volte. Circa 15.700 token a chiamata (media delle esec. 9 e 10) | come sopra, ricostruisce il blocco vero |
| H1, ruolo del campo | con l'LLM: lo stesso blocco da 30 con il prompt senza `sponsorizzate` (come l'esec. 1), 1 volta | se i video passano, il campo conta |
| H2 | con l'LLM: il blocco di 15 video di oggi, altre 2 volte. Circa 7.600 token a chiamata | resta 0-1 su 7: il controllo è stabile e H2 perde |
| H3 | senza LLM: salvare oggi il feed del canale (A-1) | contiene le descrizioni attuali dei 7 video; i video escono dal feed quando il canale ne pubblica altri 15 |
| H4 | già fatto (P4-01, lettura del codice) | esclusa |

Totale delle prove con l'LLM: circa 85.000 token (stima), da autorizzare (domanda 3). **A costo zero** per le prossime
esecuzioni vere: salvare in `notizie_escluse` il tipo e i primi 300 caratteri del sommario di ogni notizia esclusa (le metriche
cambiano solo per aggiunta): così la prossima volta la causa si legge nei dati.

**4. Causa**. Dimostrato: la regola vale per ogni tipo; l'esclusione è definitiva; i video erano sempre una minoranza in blocchi
misti; interessi, prompt e modello erano gli stessi. **Non dimostrato**: perché l'LLM li segnali. Per decidere tra H1 e H2
manca la serie di chiamate della tabella (la riga con 1 video + 1 articolo da sola costa circa 7.500 token in tutto).

**5. Correzione proposta**
- **A (raccomandata)**: l'esclusione "sponsorizzato o offerta" vale solo per le notizie `sito`. Per gli altri tipi gli id
  segnalati (e non pertinenti) passano alla valutazione, che decide con gli interessi. Provato (P4-13): oggi 0 notizie
  salvate e 3 escluse; corretto: video e paper salvati, articolo del sito escluso. Sono 4 righe in `filtra`
  (`esecutore.py:405-413`; dopo R-03 in `prefiltro.py`). Costo: ogni video segnalato costa una valutazione (stima 6b: 7-29
  mila token), cioè ciò che l'utente vuole.
- B: dire all'LLM il tipo di ogni voce (campo `tipo` in `messaggio_prefiltro`, circa 300 token in più per blocco) e limitare
  l'istruzione ai siti. Meno valutazioni inutili; da misurare solo dopo A.
- C: esclusione reversibile (tabella delle escluse con scadenza). Scartata: più stato per un problema che A risolve.
- D: spegnere l'interruttore "Escludi contenuti sponsorizzati e offerte" (Impostazioni, Esecuzione). Rimedio immediato, ma
  smette di togliere le offerte dei siti (23 e 11 voci nelle esec. 9 e 10).
- **Requisito o ADR**: nessun cambio. `WEB-22` parla di "contenuti sponsorizzati mescolati agli articoli" (sezione dei siti);
  conviene scrivere in `WEB-23` che l'interruttore vale per gli articoli dei siti (decisione da annotare in `decisioni.md`).
  L'ADR 0010 non cambia ("siti e video continuano a passare tutti dal pre-filtro"). **Windows e Linux**: nessuna
  differenza. **Dipendenze**: nessun passo R-nn (conviene prima di R-03, ma anche dopo va bene); decisione dell'utente: domanda 1.
- **Test da scrivere prima** (`tests/esecuzione/test_esecutore.py`, fixture `sessioni`, `raccolta` estesa con fonti finte
  `youtube` e `siti` come in `:200`, `Finto` che mette un id tra `sponsorizzate` e non tra `pertinenti`):
  - T-09 `test_un_video_segnalato_come_sponsorizzato_si_valuta_comunque`: oggi fissa l'errore (video escluso, commento "vedi
    S-01", decisione 24); dopo la correzione il video è valutato e salvato e `escluse` di YouTube vale 0;
  - `test_un_articolo_di_un_sito_segnalato_come_sponsorizzato_resta_escluso`: `escluse` 1 e indirizzo nel registro delle viste;
  - `test_un_paper_segnalato_come_sponsorizzato_si_valuta_comunque`;
  - il test esistente `test_articoli_a_pagamento_e_sponsorizzati_secondo_gli_interruttori` (`:306`) usa una candidata arXiv per la
    parte "sponsorizzato" e diventa rosso con la correzione: va riscritto con una candidata `sito` nello stesso commit.

### Scheda 2. S-21 con l'ADR 0011: un feed in ritardo ferma la cascata e, con "coperto fino a", fa perdere gli articoli

> **Dopo la rilettura**: il problema è vero solo se il ritardo del feed è **minore** dell'intervallo tra le esecuzioni; con un ritardo maggiore la cascata prosegue e la sitemap porta gli articoli (ma scatta il guasto "feed fermo"). Il **margine fisso di 2 giorni non va usato**: con la finestra di 3 giorni annulla la raccolta incrementale. Vedi "Esito della rilettura".

**Gravità**: alta se l'ADR 0011 si implementa com'è scritto; media oggi. **Stato**: meccanismo **dimostrato** (P29 della fase 2,
P4-02); il ritardo reale è stato misurato **una sola volta** (feed di redhotcyber, 12 novembre, documento 6a) e non si è
visto nelle esecuzioni vere 9 e 10 (D-03). **Sforzo** (stima): S per il margine, S-M per il modulo di 6a-5.

**1. Percorso di esecuzione sospetto**
1. `fonti/siti/__init__.py:90-108`: la cascata prova feed, sitemap, WordPress, HTML e si ferma alla prima strategia che
   "copre" (`r.copre and (trovate or nome != "feed")`, `:107-108`).
2. `strategie/feed.py:99-105`: il feed "copre" se ogni feed letto ha una voce più vecchia di `dal` (`r.copre = bool(coperti) and
   all(coperti)`, `:105`). Guarda il fondo della finestra, non quanto è recente la voce più nuova.
3. Il guasto "feed fermo" (`siti/__init__.py:98-102`) scatta solo se il feed non dà candidate. Un feed in ritardo ma non vuoto dà
   stato "ok" e nessun guasto.
4. `esecutore.py:256`: `dal = adesso - finestra`; ogni strategia confronta la data di pubblicazione con `dal`.
5. **ADR 0011**: dopo l'implementazione `dal` diventa "coperto fino a" (regola della decisione 34). Punto d'incontro: esecutore
   (decide e salva) ↔ `fonti/siti` (usa `dal`) ↔ tabella `siti`.

**2. Ipotesi in ordine di probabilità**
- **H1 (dimostrata)**: un sito il cui feed mostra gli articoli con un ritardo L. Oggi gli articoli arrivano in ritardo; con
  "coperto fino a" come scritto si perdono.
- **H2 (probabile)**: il ritardo L esiste in molti feed (cache, feed per Google News, articoli programmati) e non solo a
  redhotcyber: con l'ADR si perde la frazione L/T degli articoli di ogni esecuzione (T = intervallo tra due esecuzioni). Non misurato.
- **H3 (esclusa da P4-02)**: "il feed copre sempre quindi non succede niente".

**3. Esperimento più piccolo**. P4-02, fatto (senza LLM né rete): sito finto con articoli di età 2, 8, 20, 30, 50, 80, 120
ore a R0, feed in ritardo di 36 ore, news sitemap in tempo reale, 4 esecuzioni a 24 ore, finestra 3 giorni.

| Regime | R0 | R1 | R2 | R3 | Articoli mai raccolti |
|---|---|---|---|---|---|
| oggi (rilegge la finestra) | [50] | [20, 30] | [2, 8] | nessuno nuovo | nessuno (ritardo 44-56 ore), stato "ok", nessun guasto |
| ADR 0011 come scritto | [50] | niente | niente | niente | **2, 8, 20, 30**; stato "nessun articolo nuovo", nessun guasto |

Con la sola sitemap R0 li trova tutti: la perdita viene da `dal`, non dalla cascata (la sitemap letta a R1 ha le voci, ma
più vecchie di `dal`). Per misurare L sui feed veri senza nuove richieste: la migrazione dell'ADR 0011 già prevede colonne
per "le statistiche di raccolta": basta che includano la data della voce più recente vista da ogni strategia.

**4. Causa**: dimostrata (P4-02). Con intervallo T e ritardo L si perdono gli articoli pubblicati nelle L ore prima di ogni
esecuzione: con L = 36 h e T = 24 h tutti.

**5. Correzione proposta**
- **A (raccomandata, dentro l'ADR 0011)**: margine di rilettura, `dal = max(adesso - finestra, coperto_fino_a - margine)`, con
  un margine di 2 giorni (più del ritardo misurato) e mai oltre la finestra. Nessuna richiesta in più (stessi feed e
  stesse sitemap); gli articoli già visti li toglie il registro (`esecutore.py:263`); costa solo le pagine lette per le
  date incerte, che la proposta 6a-3 (registro passato alla fonte) azzera.
- B: "coperto fino a" = la data più recente vista dalla strategia che ha chiuso la cascata, non l'ora della raccolta.
  Più preciso (un sito quieto resta fermo alla sua ultima voce), ma cambia la regola della decisione 34 e il valore
  restituito da `fonti/siti`; solo se il margine non basta.
- C: la proposta 6a-5 B (un modulo che legge sempre news sitemap o API, con `SEMPRE = True`): toglie il ritardo del feed,
  ma da sola non evita la perdita con un `dal` stretto (ultima riga di P4-02). Resta una bozza non accettata.
- **Dove**: il calcolo di `dal` sta nel codice dell'ADR 0011 (`esecuzione/raccolta.py` dopo R-04; `fonti/siti` non cambia).
  **ADR**: aggiunta all'ADR 0011 (come la precisazione del 14 novembre). **PRD**: `ESE-03` invariato. **Windows e Linux**:
  nessuna differenza. **Dipende da**: l'ADR 0011 (va deciso prima di scriverne il codice); decisione dell'utente: domanda 2.
- **Test da scrivere prima**: T-18 (caratterizzazione del feed in ritardo, `tests/fonti/siti/test_siti.py`) e
  `test_un_feed_in_ritardo_non_fa_perdere_articoli_con_coperto_fino_a` (nuovo, `tests/esecuzione/test_esecutore.py`): `Sito`
  finto con il feed che mostra gli articoli 36 ore dopo, quattro esecuzioni a 24 ore (il modello di P4-02), asserzione "tutti
  gli articoli entro la finestra arrivano"; rosso senza il margine. La fixture `sito` va spostata in `tests/conftest.py`
  (condizione di R-04).

### Scheda 3. S-06 e S-08: database bloccato, ciclo fermo, esecuzione "in corso" per sempre

**Gravità**: media (impatto alto, probabilità bassa). **Stato**: **dimostrata** (P17 e P39 della fase 2, P4-03); l'innesco reale
**non è mai stato osservato** (L-01: nessuna riga "locked" in 54.155). **Sforzo** (stima): S, 1-2 ore.

**1. Percorso di esecuzione sospetto**
1. Tutto gira in un thread: le scritture dell'esecutore (commit per notizia `:454`, per blocco `:408`, per sito
   `dati/siti.py:46-52`), del programmatore (`programmatore.py:51-56`), del bot (cuore, pausa) e delle rotte `async` sono
   **sincrone dentro il ciclo di eventi**.
2. `dati/database.py:17-27`: nessun `busy_timeout` esplicito (vale quello del driver, 5 s), nessun WAL: un lettore con
   transazione aperta blocca il commit di chi scrive, uno scrittore blocca tutti.
3. Se un'altra connessione tiene il blocco, la prima scrittura aspetta 5 s **con il ciclo fermo**; poi `OperationalError`.
4. `_salva` e `m.conta_token` stanno fuori dal `try` di `elabora` (`:318-319`): l'errore esce da `_tutti` (`:462-463`) come
   gruppo e cancella tutte le altre valutazioni; `_esegui` registra `fallita` (`:153-155`).
5. `finally` (`:156-165`): `esecuzioni.termina` (nuova sessione, altra scrittura, altri 5 s) fallisce di nuovo e solleva: la
   riga `self.avanzamento = None` (`:164`) non si esegue.
6. Effetto sugli altri componenti: `avvia` (`:122-123`) risponde `GiaInCorso` a dashboard, CLI, programmatore e bot
   (`/aggiorna`); `gradiens esegui` non finisce mai (`cli.py:143-145`); il pannello mostra "Esecuzione in corso"; `gradiens
   aggiorna` rifiuta ("Un'esecuzione è in corso", `aggiornamento.py:47`). Si esce solo spegnendo e riaccendendo il servizio.

**2. Ipotesi sull'innesco, in ordine di probabilità**
- **H1**: uno strumento esterno con una transazione aperta sul file (DB Browser, `sqlite3`): P4-03 mostra che blocca sia con
  una scrittura sia con una lettura aperta.
- **H2**: un secondo servizio (scheda 6): `migra` e `segna_interrotte` scrivono. Nei 9 avvii sovrapposti dei log (L-02) non
  c'è nessun errore.
- **H3**: Windows con antivirus o cartella sincronizzata: darebbe errori diversi (`disk I/O error`, `PermissionError`). Non provato.
- **H4**: la copia giornaliera: esclusa (usa l'API di backup in un passo, solo letture brevi).

**3. Esperimenti**. P4-03, fatto (`Esecutore` vero, 60 paper, blocco preso da un altro thread a 1 s):

| Caso | Esito |
|---|---|
| A) scrittura per 3 s | completata, 40 notizie salvate, ciclo fermo 3,02 s, `avanzamento` torna `None` |
| B) scrittura per 11 s | `OperationalError` esce da `attendi` (`termina`); riga `in_corso` nel database; `avanzamento` impostato; `avvia()` dà `GiaInCorso`; ciclo fermo fino a 4,98 s per volta |
| C) transazione di lettura per 11 s | come B, motivo salvato "unhandled errors in a TaskGroup (3 sub-exceptions)" |
| D) come B con la correzione | stato `fallita`, motivo "OperationalError: … database is locked", `avanzamento` `None`, nessuna eccezione fuori; ciclo ancora fermo 4,98 s |

Da raccogliere (A-3): se compare "locked" nei log nei prossimi giorni, con l'ora; se si usa uno strumento sul database
mentre Gradiens è acceso.

**4. Causa**: dimostrata per i due effetti (ciclo fermo fino a 5 s per scrittura; esecuzione "in corso" per sempre). L'innesco
reale: **da indagare** (nessuna occorrenza).

**5. Correzione proposta**
- **A (raccomandata)** in `_esegui` (`esecutore.py:141-167`): (1) `avanzamento = None` in un `finally` annidato attorno a
  `termina`; (2) `termina` riprovato 3 volte a 0,5 s; (3) motivo leggibile (scheda 4). L'ADR 0011 salverà "coperto fino a"
  nello stesso `finally`: va dentro lo stesso blocco protetto, quindi questa correzione va **prima** del suo codice.
- B: WAL con `busy_timeout`. Toglie il blocco causato da un lettore, non quello da uno scrittore; aggiunge due file
  (`-wal`, `-shm`) in `.gradiens/` e rende rischiosa la copia a mano del solo `.db`. Non ora.
- C: scritture fuori dal ciclo (`asyncio.to_thread`). Toglie lo stallo ma richiede una sessione per thread: contraddice la
  scheda A-08 (sessione unica) ed entra nel passo R-05. Non ora. Con A il ciclo resta fermo fino a 5 s per tentativo
  (P4-03 D): accettato finché l'innesco non si osserva.
- **Requisito**: `ESE-13` (motivo utile). **ADR**: nessuno. **Windows e Linux**: SQLite è lo stesso; su Windows i blocchi di
  file sono più frequenti (non provato). **Dipende da**: nessun R-nn.
- **Test da scrivere prima**: T-26 (`tests/esecuzione/test_esecutore.py`) `test_un_errore_di_database_alla_chiusura_non_lascia_l_esecuzione_in_corso`:
  `monkeypatch` su `esecuzioni.termina` che solleva `OperationalError` due volte e poi riesce; asserzioni: stato registrato,
  `esecutore.avanzamento is None`, una nuova `avvia` accettata. Oggi il test fissa l'errore con il commento "vedi S-06".
  Fixture `sessioni`, `Finto`. Facoltativa e lenta (11 s): la variante con una seconda connessione `sqlite3` di P4-03.

### Scheda 4. S-05 con S-02, S-04, S-07: risposte dell'LLM di forma inattesa e motivo opaco

> **Dopo la rilettura**: la parte (b) **non deve togliere** gli `except QuotaEsaurita: raise`: `QuotaEsaurita` eredita da `ErroreLLM`, quindi senza quelle righe la quota esaurita diventerebbe un errore per notizia e l'esecuzione continuerebbe (viola `LLM-06`). Vedi "Esito della rilettura".

**Gravità**: media. **Stato**: **dimostrata** (P03, P04, P18, P28 della fase 2; P4-06); **mai osservata** nei log (L-07: nessun
avviso di forma, nessuna esecuzione fallita per l'LLM). **Sforzo** (stima): M, 3-5 ore.

**1. Percorso di esecuzione sospetto**
1. `llm/claude_code.py:45-61`: `interpreta` solleva `ErroreLLM` per JSON non valido, `is_error` e `structured_output` non
   dizionario, ma un JSON che non è un oggetto (`null`, `[]`) dà `AttributeError` (`:48-51`, S-04).
2. `esecutore.py:387-414` (`filtra`): prende solo `QuotaEsaurita` ed `ErroreLLM`. `validi` legge `risposta.dati.get(chiave, [])` e
   itera: `{}` o `"tutti"` danno liste vuote, quindi **tutte le notizie del blocco scartate e segnate viste** (`:406-408`);
   `pertinenti: null` dà `TypeError`.
3. `esecutore.py:291-319` e `_salva` (`:429-455`): `p.get(...)` su un elemento che non è un dizionario dà `AttributeError`;
   `riassunto: null` diventa il testo `"None"` (`:449`); `m.conta_token` e `_salva` stanno fuori dal `try` (`:318-319`).
4. `_tutti` (`:458-466`): `TaskGroup` con `except* QuotaEsaurita`; ogni altro errore resta in un `ExceptionGroup`.
5. `_esegui` (`:153-155`): `str(errore)` di un gruppo è "unhandled errors in a TaskGroup (n sub-exceptions)", o " (2
   sub-exceptions)" se il testo dell'errore è vuoto; se nel gruppo c'è anche la quota, `except QuotaEsaurita` (`:148`) non la
   riconosce e lo stato è `fallita`, non `interrotta` (S-02).
6. Punti d'incontro: provider (processo esterno, ADR 0006) → esecutore → sessione condivisa (commit per blocco) → `Metriche` →
   dashboard e Telegram, che mostrano il motivo (S-39).

**2. Ipotesi in ordine di probabilità**
- **H1 (dimostrata)**: la forma delle risposte non si controlla in un punto solo, e il motivo si costruisce dal testo del gruppo.
- **H2 (non verificata)**: `--json-schema` di Claude Code rende queste forme impossibili. Spiegherebbe perché nei log non
  compaiono.
- **H3 (probabile per il futuro)**: un provider diverso (ADR 0006: OpenAI, Gemini, locale) non rispetta lo schema: il
  controllo serve comunque.

**3. Esperimenti**. P4-06, fatto (`Esecutore` vero, 6 paper, 2 blocchi, provider finto che altera una risposta; "oggi" /
con `_tutti` corretto (a) / con (a) e controllo di forma (b)):

| Risposta alterata | Oggi | (a) | (a) + (b) |
|---|---|---|---|
| pre-filtro `{}` | completata; 3 notizie scartate **e viste** | uguale | 3 errori, blocco da riprovare |
| `pertinenti: null` | fallita, "(1 sub-exception)", 0 salvate | fallita, "'NoneType' object is not iterable" | completata, 3 salvate, 3 errori |
| `pertinenti: "tutti"` | come `{}` | uguale | 3 errori |
| `punteggi: ["x"]` | fallita, "(6 sub-exceptions)" | motivo "'str' object has no attribute 'get'" | completata, 6 errori |
| `riassunto: null` | completata, testo `"None"` salvato 6 volte | uguale | 6 errori, nessuna salvata |
| quota + `RuntimeError` | fallita, " (2 sub-exceptions)" | **interrotta**, motivo della quota | uguale |

H2 non si può provare senza una chiamata vera (vietata). Da raccogliere solo se capita: se un'esecuzione ha come motivo
"unhandled errors in a TaskGroup", copiare da `.gradiens/log/gradiens.log` la riga "Esecuzione N fallita" e la traccia sotto.

**4. Causa**: dimostrata. Sono due difetti con la stessa radice: (a) motivo e quota dentro un gruppo; (b) nessun controllo
di forma al confine del provider.

**5. Correzione proposta**
- **(a)** `_tutti`: la quota ha la precedenza anche con altri errori; un errore solo si rilancia da solo, non dentro il gruppo
  (`esecutore.py:458-466`, dopo R-03 `parallelo.py`; 10 righe). In `_esegui` il motivo si costruisce dalle eccezioni foglia (S-07).
- **(b)** un controllo di forma in un solo punto: chiavi obbligatorie presenti e contenitori del tipo dello schema, `ErroreLLM`
  altrimenti (`{}` e `"tutti"` diventano blocchi da riprovare, non notizie perse). Va in una funzione `chiedi` di `esecuzione/`
  che chiama `provider.chiedi`, controlla la forma e lascia passare la quota: è l'opzione B della scheda A-09 e toglie le 5
  copie di `except QuotaEsaurita: raise`. Non nel provider: l'interfaccia resta unica (ADR 0006) e il controllo vale per ogni
  provider futuro. La stessa funzione serve all'ADR 0012. Severo su chiavi e contenitori, **tollerante sui valori** (un
  `85.5` si arrotonda; un controllo severo sui testi farebbe ripetere la valutazione a ogni esecuzione, come in S-36).
- **(c)** S-04: `interpreta` controlla `isinstance(d, dict)` (2 righe, `llm/claude_code.py:48-51`).
- **Requisito**: `ESE-13`, `LLM-06`. **ADR**: 0006 invariato. **Windows e Linux**: nessuna differenza. **Dipende da**: nessun
  R-nn; conviene dopo R-03 per correggere `_tutti` nel suo posto nuovo (T-05, T-27 e la parte di T-28 sul pre-filtro devono
  esistere prima di R-03).
- **Test da scrivere prima** (`tests/esecuzione/test_esecutore.py`, `tests/llm/test_claude_code.py`): T-27
  `test_quota_insieme_ad_un_altro_errore_nello_stesso_gruppo` (oggi `fallita`, dopo `interrotta`); T-28
  `test_risposte_llm_di_forma_inattesa` parametrizzato sulle sei righe della tabella; T-26 per il motivo (S-07); T-29 per S-04
  (`interpreta` con `null` e `[]`). Fixture: `Finto` che altera una risposta (strumento 3 del documento 02) e
  `BLOCCO_PREFILTRO` a 3.

### Scheda 5. S-18: migrazione fallita a metà

> **Dopo la rilettura: NON applicare la correzione A così com'è scritta.** Con il `BEGIN` esplicito provato in P4-07 il `PRAGMA foreign_keys = OFF` finisce dentro la transazione e non ha effetto: la ricreazione di `notizie` cancella a cascata le pertinenze (provato dal revisore: 2 → 0), la stessa perdita di dati del 7 novembre. Vedi "Esito della rilettura".

**Gravità**: media oggi, **alta per l'ADR 0011** (una migrazione sul database vero). **Stato**: **dimostrata** (P15b e P15c della
fase 2, P4-07). **Sforzo** (stima): S-M, 4-6 ore con i test.

**1. Percorso di esecuzione sospetto**
1. `app/servizio.py:94-96`: `crea_app` chiama `migra` prima di ogni altra cosa, una volta per processo.
2. `dati/database.py:34-42`: connessione dedicata; `PRAGMA foreign_keys = OFF` e commit; se il database non è all'ultima
   versione, `copia_di_sicurezza(motore, "migrazione", tenute=3)`.
3. `dati/database.py:44-46`: `with connessione.begin()` e `command.upgrade`. Il driver `sqlite3` (modalità legacy) non apre
   la transazione prima del primo `INSERT`, `UPDATE` o `DELETE`: il DDL che lo precede (`CREATE TABLE`, `ALTER TABLE ADD
   COLUMN`) è in auto-commit. Una migrazione di sole `add_column`, come quella dell'ADR 0011, **non ha nessun rollback**.
4. `dati/database.py:56-71`: la copia si chiama `gradiens-AAAAMMGG-HHMMSS-migrazione.db` (precisione del secondo); le copie
   `-migrazione` oltre le ultime 3 si cancellano (`:69-70`).
5. `migra` solleva e `servizio.esegui` non intercetta: il processo esce con la traccia (in `avvio.log` se avviato staccato,
   `cli.py:55`; nel journal con systemd).
6. A ogni nuovo avvio: il database non è all'ultima versione, quindi **un'altra copia** (del database già sporco) e un
   secondo errore ("duplicate column name"). Con systemd (`Restart=on-failure`, `RestartSec=30`, `avvio_sistema.py:137-138`)
   l'avvio si ripete ogni 30 s, senza fine.
Componenti: `migra` ↔ Alembic ↔ driver `sqlite3` ↔ copie di sicurezza ↔ systemd.

**2. Ipotesi in ordine di probabilità**
- **H1 (dimostrata)**: il DDL anticipato non si annulla.
- **H2 (dimostrata)**: ogni avvio fallito rifà una copia; dopo 4 avvii la copia pulita non c'è più; due avvii nello stesso
  secondo si sovrascrivono.
- **H3 (non provata)**: su Windows `unlink` di una copia vecchia può dare `PermissionError` (antivirus, cartella
  sincronizzata) dentro `migra` e impedire l'avvio (S-19).

**3. Esperimento**. P4-07, fatto (database alla 0011 con un sito; 0012 di prova con due `add_column` su `siti` e poi un errore):

| Prova | Esito |
|---|---|
| `migra` vero, avvio 1 | `RuntimeError`; colonna `coperto_fino_a` presente; `alembic_version` 0011; 1 copia (pulita) |
| avvii 2, 3 | "duplicate column name"; 2 e 3 copie, 1 pulita |
| avvio 4 | "duplicate column name"; 3 copie, **0 pulite** |
| due avvii nello stesso secondo | 1 sola copia, **non pulita** |
| migrazione con `BEGIN` esplicito, 2 tentativi | stesso errore della migrazione (non "duplicate column"), colonna assente, `alembic_version` 0011 |
| con `BEGIN` esplicito, migrazione corretta | colonne aggiunte, riga di `siti` presente, `PRAGMA foreign_key_check` vuoto |

**4. Causa**: dimostrata.

**5. Correzione proposta**
- **A (raccomandata)**: migrazione con `BEGIN` esplicito: una connessione con `isolation_level = None` e un `BEGIN` nel gancio
  `begin`, solo dentro `migra` (il motore normale non cambia). `PRAGMA foreign_keys` resta fuori dalla transazione, come oggi
  (`:37-38`, `:48`). Provato in P4-07 (due ultime righe della tabella).
- B: dopo un errore, ripristinare il file dalla copia. Protegge anche da una migrazione che "riesce" ma rovina i dati (la
  0009 del 7 novembre), ma può sovrascrivere dati scritti nel frattempo. Non ora (domanda 7).
- **C (con A)**: la copia pulita non si perde: nome con la revisione di partenza (`-da-0011-migrazione.db`), una sola copia per
  revisione di partenza, mai sovrascritta; un errore di `unlink` nella rotazione non ferma l'avvio.
- D: `RestartPreventExitStatus` nell'unità di systemd per l'uscita di una migrazione fallita. Tocca l'unità generata
  (`avvio_sistema.py`) e obbliga a rifare la registrazione; con A e C non serve.
- **Dove**: `dati/database.py:30-71` (backend). **ADR**: una nota nell'ADR 0004 (architetto), perché cambia il modo di migrare.
  **PRD**: nessuno. **Windows e Linux**: SQLite uguale; la CI prova entrambi. **Dipende da**: nessun R-nn; va fatta **prima**
  della migrazione dell'ADR 0011.
- **Test da scrivere prima** (`tests/dati/test_database.py`): T-01 (esiste in parte: `:36-52` e `:70-88`) e T-43
  `test_una_migrazione_fallita_a_meta_lascia_il_database_cosi` (oggi fissa lo stato sporco; si ribalta in "..._com_era"):
  0012 finta in una copia della cartella delle migrazioni con `monkeypatch.setattr(database, "CARTELLA_MIGRAZIONI", ...)`;
  asserzioni: colonna assente, `alembic_version` vecchia, secondo `migra` con lo stesso errore, **dopo 4 tentativi esiste
  una copia pulita** (si sostituisce `datetime` del modulo, niente `sleep`); più
  `test_due_avvii_nello_stesso_secondo_non_sovrascrivono_la_copia_pulita`.

### Scheda 6. S-11 con S-37: un secondo servizio agisce prima di accorgersi che la porta è occupata

> **Dopo la rilettura**: la correzione A (riservare la porta prima di toccare il database) **non protegge così com'è scritta**: un socket legato ma non in ascolto non impedisce a un secondo processo di legarsi (provato su Linux), e mettendolo subito in ascolto ogni avvio lento sembrerebbe "occupato" alla correzione B. Va ripensata. Vedi "Esito della rilettura".

**Gravità**: media. **Stato**: meccanismo **dimostrato** (P16 della fase 2 in un solo processo, sorgente di uvicorn, log L-04);
l'innesco "servizio fermo scambiato per spento" **non osservato** (L-06); la sovrapposizione spegni-avvia osservata 9 volte
senza danni. Due servizi veri avviati insieme **non provati** (vietato). **Sforzo** (stima): M, 4-6 ore.

**1. Percorso di esecuzione sospetto**
1. `app/cli.py:17-24` e `:42-56`: `gradiens avvia` chiede `/api/stato` con timeout di 2 s; se non risponde lancia
   `_avvia_staccato` (un nuovo processo) e aspetta fino a 20 s. Il pannello (`pannello.py:75-78`, ogni 3 s) e `aggiorna` usano la
   stessa `leggi_stato`: `None` vuol dire "spento".
2. Nel nuovo processo `servizio.esegui` → `crea_app` (`servizio.py:94-103`): `migra` (`:96`), `segna_interrotte` (`:100-102`, un
   `UPDATE ... WHERE stato = 'in_corso'` su **tutte** le righe), oggetti.
3. `server.run()`: uvicorn esegue la startup del lifespan **prima** di creare il socket (`uvicorn/server.py:115-118`). Il
   lifespan (`servizio.py:81-91`) avvia il bot (`:84`, `getUpdates` con lo stesso token) e crea i compiti del programmatore e
   del bot (`:85-86`): il primo controllo può avviare un recupero.
4. Poi crea il socket: se la porta è occupata, scrive l'errore, esegue lo spegnimento del lifespan (ferma bot ed esecuzione
   appena avviata, che diventa "interrotta") e `sys.exit(STARTUP_FAILURE)` = 3 (`server.py:180-192`, `config.py:81`).
5. Le righe `in_corso` del primo processo sono già `interrotta`, con motivo e `finita_il`; il primo le riscrive solo quando
   l'esecuzione finisce (`termina`, `esecutore.py:162`). Intanto CLI, pannello e `aggiorna` leggono "interrotta"
   (`aggiornamento.py:47` si fida di quel valore: potrebbe spegnere un'esecuzione viva).
6. Con systemd: uscita 3, `Restart=on-failure`, `RestartSec=30` (`avvio_sistema.py:137-138`): l'avvio si ripete ogni 30 s, ogni
   volta con `migra`, `segna_interrotte` e un bot che parte e si ferma.
7. Sovrapposizione spegni-avvia: `uvicorn/server.py:281-311`: `shutdown` chiude **per primi** i socket di ascolto e fa lo
   spegnimento del lifespan (esecuzione, `bot.ferma`) per ultimo; la CLI dichiara "spento" appena la porta tace (`cli.py:93`).
Componenti: CLI (processo) ↔ servizio (uvicorn, lifespan) ↔ SQLite (due processi) ↔ Telegram (due poller) ↔ systemd.

**2. Ipotesi sull'innesco, in ordine di probabilità**
- **H1 (osservata 9 volte, finora senza danni)**: `spegni` e `avvia` ravvicinati. La porta si chiude subito e il vecchio
  processo vive ancora fino a 4,9 s (12 spegnimenti su 41 durano 3,3-4,9 s, con il bot acceso nei 11 casi controllati): per qualche secondo ci
  sono due processi sul database e due bot (L-02, L-03: 8 errori `Conflict`).
- **H2 (osservata 1 volta, L-04)**: un secondo servizio parte mentre il primo è acceso. Il log mostra "Application startup complete"
  e subito dopo "address already in use".
- **H3 (non osservata)**: servizio acceso ma fermo oltre 2 s (database bloccato, scheda 3; una sitemap enorme interpretata nel
  ciclo, S-24; `stato_avvio` che esegue processi nel ciclo). Nei log il ciclo non è mai stato fermo più di circa 1 s (L-06).
- **H4 (non osservata)**: Windows, attività all'accensione più avvio a mano prima che la porta sia aperta (su Linux la porta
  apre in 1,2 s al massimo, L-05; su Windows non misurato).

**3. Esperimenti**

| Ipotesi | Esperimento | Esito |
|---|---|---|
| H1 | lettura dei log (L-02, L-03) | 9 sovrapposizioni su 41 spegnimenti; 8 `Conflict`; nessun errore sul database |
| H2 | lettura del log (L-04) e di uvicorn | startup prima del bind, uscita con codice 3 |
| H2 | P16 (fase 2, due `crea_app`) | la riga `in_corso` diventa `interrotta` |
| H3 | P4-08b (server muto) e P4-08c | `leggi_stato` dà `None` dopo 2,0 s, il pannello scrive "spento"; porta chiusa dà `ConnectError`, server muto `ReadTimeout` |
| H2, H4 | due servizi veri sulla stessa porta | **non fatto** (vietato) |

Da raccogliere (A-3): quante volte compaiono "address already in use" e "Conflict" nei log nei prossimi giorni, con l'ora e
che cosa si stava facendo.

**4. Causa**: dimostrata nel meccanismo (l'ordine di uvicorn e `segna_interrotte` in `crea_app`); l'innesco reale è raro.

**5. Correzione proposta**
- **A (raccomandata)**: riservare la porta **prima** di toccare il database: in `servizio.esegui` si crea e si lega il socket e si
  passa a uvicorn (`server.run(sockets=[sock])`); se il `bind` fallisce il processo esce con un messaggio chiaro prima di
  `migra`, `segna_interrotte`, bot e programmatore. Su Linux `SO_REUSEADDR` per i riavvii veloci; su **Windows non
  impostarlo** (permette il doppio `bind`). P4-14: su Linux il secondo `bind` è rifiutato con e senza. Dove:
  `servizio.py:133-141`.
- **B (con A)**: `leggi_stato` distingue "porta chiusa" (`ConnectError`: spento) da "nessuna risposta" (`ReadTimeout`: occupato).
  `avvia` non lancia un secondo servizio se è occupato; il pannello scrive "occupato". Dove: `cli.py:17-24`, `pannello.py`,
  `aggiornamento.py`.
- **C (copre la sovrapposizione e la scheda 12)**: fare il lavoro lento dello spegnimento **prima** di chiudere la porta.
  `/api/spegni` risponde subito e lancia un compito che ferma esecuzione e bot (`esecutore.ferma()`, `bot.ferma()`) e solo dopo
  imposta `should_exit`. La porta resta aperta fino alla fine del lavoro: "porta chiusa" vale "processo quasi finito". Dove:
  `servizio.py:48-56` e `:81-91`. Nessun codice specifico di un sistema (ADR 0007).
- D: un lock su file (`flock`, `msvcrt.locking`) in `avvio_sistema.py`. Più robusto del `bind`, più codice per due sistemi; con A non serve.
- **Requisito**: `CLI-01`, `CLI-04`, `ESE-12`. **ADR**: 0007 invariato. **Windows e Linux**: vedi A; il test gira nella CI
  Windows (A-6 per una prova a mano). **Dipende da**: nessun R-nn (R-06 rende pubbliche `_avvia_staccato` e `_attendi`: nessun conflitto).
- **Test da scrivere prima** (`tests/app/test_servizio.py`, `tests/app/test_cli.py`; fixture `conf`, `porta_libera`, socket
  in ascolto): T-40 diviso in tre. `test_un_secondo_servizio_non_tocca_il_database_se_la_porta_e_occupata`: socket in ascolto
  sulla porta di `conf`, riga `in_corso` nel database, `servizio.esegui(conf)` esce e la riga resta `in_corso` (oggi diventa
  `interrotta`: commento "vedi S-11"). `test_leggi_stato_distingue_occupato_da_spento` (P4-08b e P4-08c).
  `test_lo_spegnimento_ferma_esecuzione_e_bot_prima_di_chiudere_la_porta` (bot ed esecutore finti che registrano l'ordine).

### Scheda 7. S-12: due avvii del bot insieme

> **Dopo la rilettura**: `asyncio.Lock` non è rientrante e `_riprova` chiama `self.avvia()` (`telegram/bot.py:156`): avvolgendo entrambe alla lettera si va in stallo. Il lucchetto va preso in un solo punto (la prova P4-09 l'aveva evitato chiamando il metodo interno).

**Gravità**: bassa-media. **Stato**: **dimostrata** (P09 della fase 2, P4-09); il sintomo "due poller" è stato osservato 9
volte nei log, ma per un'altra via (la sovrapposizione di processi della scheda 6); la via dentro un solo processo no.
**Sforzo** (stima): S, 1-2 ore.

**1. Percorso di esecuzione sospetto**
1. `telegram/bot.py:106-134` `avvia`: `await self.ferma()`, costruisce l'`Application`, poi `await app.initialize()`, `await app.start()`,
   `await app.updater.start_polling(...)`: tre scambi di rete. Solo alla fine `self._app = app` (`:133`).
2. Chi lo chiama nello stesso ciclo di eventi: `gira` ogni 5-60 s (`:145-156`), la conferma della chat dalla dashboard
   (`rotte_impostazioni.py:295`, `await bot.avvia()`), "Messaggio di prova" (`bot.py:180-183`, `_riprova`).
3. `_riprova` controlla `self._app is None` (`:155`) e poi `await self.avvia()`. Durante gli `await` di `avvia`, un altro chiamante
   vede ancora `_app is None` e avvia un secondo `Application` con lo stesso token.
4. Il secondo assegna `self._app`; il primo resta in polling senza riferimento. `ferma()` (`:136-143`) ne ferma uno solo.
5. Libreria (L-08): il polling riprova sempre, anche su `Conflict`, con attese fino a 30 s. I due poller si tolgono le
   richieste a vicenda e il log si riempie di errori; i comandi arrivano a uno dei due.
Componenti: task `gira` ↔ rotta della dashboard ↔ libreria di Telegram ↔ polling.

**2. Ipotesi in ordine di probabilità**
- **H1 (dimostrata)**: finestra di 0,3-1 s per tentativo. Il caso più probabile è la conferma della chat nel tutorial se il
  ciclo `gira` scatta proprio in quel momento (periodo fino a 60 s: circa 1-2%, stima); "Messaggio di prova" solo con il bot spento.
- **H2 (osservata)**: un altro processo con lo stesso token (sovrapposizione della scheda 6: 8 errori `Conflict`). L'unico
  `Conflict` del 12 novembre alle 14:21 è in un processo acceso da ore, senza un secondo servizio sul PC e senza richieste
  alla dashboard in quel momento: causa **sconosciuta**; potrebbe essere una prova con lo stesso token da un altro PC (la prova
  su Windows è di quel giorno): A-5.

**3. Esperimenti**. P4-09, fatto (`BotGradiens` vero con `Application` finta): oggi `avvia()` + `_riprova()` insieme: 2 create, **1
ancora in polling** dopo `ferma()`; `avvia()` + `avvia()`: 2 create, 1 ancora in polling. Con un `asyncio.Lock` attorno ad
`avvia` e `_riprova`: 1 creata e 0 in polling; due `avvia()` in fila: 2 create in sequenza, 0 in polling.

**4. Causa**: dimostrata.

**5. Correzione proposta**
- **A (raccomandata)**: un `asyncio.Lock` in `BotGradiens` attorno ad `avvia` e `_riprova`; `_riprova` controlla `_app is None` dentro il
  lock. Dove: `telegram/bot.py:106-156`. P4-09: nessun poller perso.
- B: non fare niente: il danno osservato è solo rumore nel log. Non raccomandata: un poller perso resta fino allo spegnimento.
- **Requisito**: `TG-01`, `TG-02`. **ADR**: nessuno. **Windows e Linux**: nessuna differenza. **Dipende da**: nessun R-nn
  (decisione 35: il bot resta com'è, ma questa è una correzione, non un refactoring).
- **Test da scrivere prima**: T-33 `test_avvio_del_bot_errori_ferma_e_avvii_concorrenti` (`tests/telegram/test_bot.py`, `Application`
  finta come in P4-09): oggi fissa "2 create, 1 ancora in polling" (commento "vedi S-12"); dopo, 0. Va aggiunto "dopo un solo
  `ferma()` nessun poller resta".

### Scheda 8. S-32: il redirect di robots.txt verso la rete di casa viene seguito

**Gravità**: media (sicurezza), poco probabile. **Stato**: **dimostrata** (P43 della fase 2; P4-05 con socket veri). **Sforzo**
(stima): S, 1 ora. **Proprietario**: scraping-engineer (`fonti/siti/rete.py`): qui è solo analisi.

**1. Percorso di esecuzione sospetto**
1. `fonti/siti/rete.py:100-117` `_regole`: alla prima richiesta verso ogni origine (schema e host) scarica `/robots.txt` con
   `_scarica(origine + "/robots.txt", seguendo_redirect=True)` (`:105`).
2. `rete.py:137-146` `_scarica`: con `seguendo_redirect=True` è httpx a seguire i redirect, senza passare da `indirizzo_pubblico`.
3. Per le pagine invece `leggi` segue i redirect a mano e rifiuta schemi diversi da http/https e indirizzi non pubblici (`:128-135`).
4. Le origini vengono da dati non fidati: link di feed e sitemap, pagine di articoli di qualunque dominio (le voci di altri
   domini nei feed, decisione 18, sono ancora accettate), sezioni. `normalizza` toglie i numeri IP non pubblici e `localhost`
   (`indirizzi.py:19-28`) e forza `https` sul **link**, non sul redirect di robots.txt.
Componenti: rete dei siti ↔ rete di casa (router, NAS, dispositivi) ↔ esecutore (robots.txt di molti domini).

**2. Ipotesi in ordine di probabilità**
- **H1 (dimostrata)**: un sito (o chi lo controlla) risponde 302 a `/robots.txt` verso `http://192.168.1.x/...`: Gradiens fa
  una GET in chiaro alla rete di casa. È cieca (il corpo è letto come robots.txt e scartato) ma può far scattare comandi
  GET di dispositivi senza password.
- **H2**: nomi DNS che puntano a indirizzi di casa. `ip6-localhost` si risolve in `::1` e passa `normalizza` (P4-05), ma il link è
  forzato a `https`: la GET andrebbe come TLS, quindi in pratica innocua con server HTTP semplici.
- **H3 (non coperta)**: DNS rebinding.

**3. Esperimenti**. P4-05 e P4-05b, fatti (due server `asyncio` su 127.0.0.1): **codice di oggi**, il "dispositivo di casa"
riceve `GET /riavvia-il-router`; **correzione di prova** (redirect a mano con `indirizzo_pubblico`), non riceve niente, esito
"errore di rete"; un redirect legittimo (`e.org` verso `www.e.org`) si segue e le regole si applicano.

**4. Causa**: dimostrata.

**5. Correzione proposta**
- **A (raccomandata)**: seguire a mano i redirect di robots.txt con lo stesso controllo di `leggi` (circa 12 righe in `_regole`;
  meglio una funzione sola condivisa da `leggi` e `_regole`).
- B: un controllo a livello di trasporto httpx (`event_hooks` sulla richiesta) che rifiuta host non pubblici per ogni
  richiesta: copre ogni percorso, ma solo numeri IP e `localhost`.
- C: risolvere il nome (`getaddrinfo` in un thread) e controllare ogni indirizzo prima di connettere: copre H2, non H3; costo M;
  rischio di far fallire siti legittimi in reti con DNS particolari (VPN, Tailscale MagicDNS con nomi che risolvono in 100.x).
- **Raccomandazione**: A ora; C solo con la 6c (dashboard raggiungibile da internet), quando l'indirizzo lo sceglie un estraneo
  (domanda 4). **Requisito**: `WEB-17`, `AMB-02`. **ADR**: nessuno. **Windows e Linux**: nessuna differenza. **Dipende da**: nessun R-nn.
- **Test da scrivere prima** (`tests/fonti/siti/test_sicurezza.py`, `MockTransport` che registra gli indirizzi come in `:17`): T-50
  `test_il_redirect_di_robots_txt_verso_la_rete_di_casa_viene_seguito` (oggi fissa che la richiesta parte, commento "vedi
  S-32"; si ribalta in "..._non_viene_seguito") e `test_un_redirect_di_robots_txt_verso_una_pagina_pubblica_si_segue`.

### Scheda 9. S-09: due esecuzioni al ritorno all'ora solare

> **Dopo la rilettura**: il test proposto va scritto in un altro modo, perché `esecuzioni.inizia` non accetta `avviata_il` (`dati/esecuzioni.py:13-17`).

**Gravità**: bassa. **Stato**: **dimostrata** (P01 della fase 2, P4-04). **Sforzo** (stima): S, 1 ora.

**1. Percorso di esecuzione sospetto**
1. `esecuzione/programmatore.py:32`: l'orologio è `datetime.now()`, ora locale **senza fuso**; `_scadenza` combina la data di
   oggi con l'orario (`:26-27`).
2. `programmatore.py:63`: dal secondo controllo in poi `da_avviare = ultimo < scadenza <= adesso`. Il controllo "è già partita
   un'esecuzione da quella scadenza" (`avviate_dal`) si fa solo al primo controllo dopo l'avvio (`:59-61`).
3. Al ritorno all'ora solare (ultima domenica di ottobre) l'orologio locale passa da 02:59:30 a 02:00:00. Con un orario tra
   02:00 e 02:59 la condizione è vera due volte.
4. `esecutore.py:119-128`: la seconda `avvia` parte, perché la prima è finita da tempo.
Componenti: programmatore ↔ orologio del sistema ↔ esecutore ↔ database (`avviate_dal`).

**2. Ipotesi**. **H1 (dimostrata)**: doppia partenza solo con un orario nell'ora ripetuta (il predefinito è 07:00; l'orario
dell'utente è 07:00). **H2 (esclusa)**: all'ora legale la partenza è una sola, al primo controllo dopo le 03:00.

**3. Esperimento**. P4-04, fatto (`Programmatore.controlla` vero, `TZ=Europe/Rome`, 30 s alla volta, riga vera in `esecuzioni`):

| Giorno | Orario | Oggi | Con `avviate_dal` a ogni scadenza |
|---|---|---|---|
| 25 ottobre 2026 (ora solare) | 02:30 | **2** (02:30 CEST e 02:30 CET) | 1 |
| 25 ottobre 2026 | 07:00 | 1 | 1 |
| 29 marzo 2026 (ora legale) | 02:30 | 1 (03:00 CEST) | 1 |
| 29 marzo 2026 | 07:00 | 1 | 1 |

**4. Causa**: dimostrata. Frequenza: una volta l'anno e solo con l'orario tra 02:00 e 02:59 e il PC acceso. Costo: una
seconda esecuzione (quota).

**5. Correzione proposta**
- **A (raccomandata)**: a ogni scadenza si controlla `esecuzioni.avviate_dal(scadenza in UTC)`, come al primo controllo
  (`programmatore.py:61-63`, 3 righe). Una query in più solo quando la scadenza è appena passata.
- B: orologio con fuso (`datetime.now(ZoneInfo(...))`): cambia tutta l'aritmetica del file e richiede di scegliere un fuso. Non necessario.
- C: lasciare così e correggere il docstring (`:4-6` dice che i cambi d'ora sono gestiti). Accettabile data la rarità.
- **Requisito**: `ESE-01`. **ADR**: nessuno. **Windows e Linux**: `astimezone` di un `datetime` senza fuso usa il fuso del
  sistema su entrambi; il test usa solo l'orologio iniettato e calcola `avviata_il` con la stessa conversione (nessun `TZ`:
  su Windows `time.tzset` non esiste). **Dipende da**: nessun R-nn, nessuna decisione.
- **Test da scrivere prima** (`tests/esecuzione/test_programmatore.py`): T-41 `test_il_programmatore_con_ora_solare_ora_legale_e_mezzanotte`:
  oggi fissa 2 partenze (commento "vedi S-09"), dopo 1; orologio iniettato 02:29:30, 02:30:00, 02:59:30, 02:00:00, 02:30:00;
  l'esecutore finto scrive una riga `esecuzioni.inizia` con `avviata_il = scadenza.astimezone(UTC).replace(tzinfo=None)`.

### Schede di interazione

Le cinque schede seguenti riguardano punti in cui due componenti si incontrano. Per ognuna: nessun difetto è emerso dai log
veri; i comportamenti sono dimostrati con prove o con il codice e dichiarati come tali.

### Scheda 10. I-1: programmatore ed esecuzione manuale insieme

**Gravità**: bassa. **Stato**: **nessun difetto dimostrato** (P4-11 A e B); nei log veri nessun errore 409 e nessuna riga
"Esecuzione programmata saltata" (L-01, L-07). **Sforzo**: nessuno.

**1. Percorso**
1. Quattro ingressi, un solo `Esecutore` per processo (`servizio.py:103-106`): programmatore (`programmatore.py:68`), dashboard
   (`rotte.py:191-194`, rotta `async`), CLI tramite `/api/esegui` (`servizio.py:59-66`, `async`), bot (`bot.py:201-207`).
2. `Esecutore.avvia` (`esecutore.py:119-128`): controllo di `self.avanzamento` e prenotazione senza `await`, quindi atomici nel
   ciclo; chi perde riceve `GiaInCorso`.
3. `programmatore.py:63-70`: `_ultimo_controllo` si aggiorna **prima** di avviare (`:64`); su `GiaInCorso` scrive una riga INFO e non riprova.
4. Il recupero dopo l'avvio conta "qualsiasi esecuzione" partita dalla scadenza (`dati/esecuzioni.py:39-41`), anche manuale o
   fallita (`ESE-01`).
5. Pulizia giornaliera (`programmatore.py:51-56`) nello stesso ciclo: nessun `await` tra una modifica e il suo commit, quindi nessuna
   corsa con un'esecuzione in corso (letto).
Componenti: quattro canali ↔ esecutore ↔ righe di `esecuzioni` ↔ log.

**2. Ipotesi** (nessuna è un difetto)
- a) Manuale in corso all'orario: la programmata si salta (P4-11 A: 1 sola esecuzione, `dashboard`; la manuale copre la finestra).
- b) Manuale fallita dopo la scadenza (es. 8 novembre, 3 esecuzioni fallite in 2 minuti per Claude Code non collegato): il
  recupero al riavvio non scatta. È il testo di `ESE-01` ("di qualunque tipo").
- c) `gradiens esegui` con il servizio spento (`cli.py:126-132`): se il servizio appena nato ha avviato un recupero, il `POST`
  dà 409 e il comando esce con codice 1 senza seguire quella in corso. Non provato (serve il servizio vero).

**3. Esperimenti**. P4-11 A e B (fatti, `Programmatore` ed `Esecutore` veri). L-01 e L-07: 0 righe "saltata", 0 risposte 409.

**4. Causa**: nessun difetto. **5. Correzione**: nessuna. Facoltativa: far comparire la programmata saltata nel resoconto o a livello
WARNING nel log. Test già presenti: `tests/esecuzione/test_programmatore.py:111` (`GiaInCorso`); T-49 (stessa esecuzione dai quattro canali).

### Scheda 11. I-2: bot Telegram e `/pausa`, `/riprendi`

**Gravità**: bassa-media. **Stato**: tre comportamenti **dimostrati** (P4-11 B e C; lettura di `bot.py:122` e `servizio.py:84-86`),
nessuno osservato in uso: `/pausa`, `/riprendi`, `/ultima` e `/aggiorna` non compaiono mai nei log (L-07). **Sforzo** (stima): S.

**1. Percorso**
1. Bot: `avvia` usa `start_polling(drop_pending_updates=True)` (`bot.py:122`); i gestori sono filtrati sulla chat (`:112-116`);
   `/pausa` e `/riprendi` passano da `_imposta_pausa` (`:229-239`) a `impostazioni.imposta_pausa` (sessione propria e commit,
   `impostazioni.py:50-53`).
2. Programmatore: `controlla` legge `programmazione_in_pausa` a ogni controllo (`programmatore.py:57`, `:66`); in pausa non
   avvia e non recupera (`ESE-01`, `TG-10`), ma aggiorna `_ultimo_controllo` (`:64`).
3. Dashboard: il modulo "Esecuzione" invia **tutti** i campi, anche "Programmazione automatica" (`rotte_impostazioni.py:242-249`), e
   `salva_esecuzione` li scrive tutti (`impostazioni.py:30-47`).
4. `/stato` usa `Programmatore.prossima` (`programmatore.py:38-46`: `None` se in pausa).
Componenti: bot (polling, stesso ciclo) ↔ database (`impostazioni`) ↔ programmatore (task) ↔ dashboard (rotte).

**2. Casi, in ordine di probabilità d'uso**
- a) **Comandi mandati a PC spento** (letto): `drop_pending_updates=True` li butta all'accensione. E anche senza quel parametro il
  recupero partirebbe prima: `ciclo_di_vita` avvia il bot e subito il programmatore (`servizio.py:84-86`) e il primo
  `controlla` gira nel ciclo prima che il primo `getUpdates` risponda (ordine letto nel codice, tempi non misurati). Quindi
  `/pausa` mandato la sera a PC spento non impedisce il recupero del mattino.
- b) **Pausa a cavallo dell'orario** (P4-11 B): `/pausa` alle 06:59:50 e `/riprendi` alle 07:00:50: nessuna esecuzione quel
  giorno, e `/riprendi` non recupera (il recupero esiste solo all'avvio). Previsto da `ESE-01` ("con la programmazione in
  pausa non si recupera niente"): l'utente potrebbe aspettarsi il contrario.
- c) **Durante un'esecuzione** (letto): `/pausa` non tocca quella in corso; `/stato` ne mostra l'avanzamento; `/aggiorna` risponde
  "Esecuzione già in corso." (anche per sempre se S-06 ha lasciato `avanzamento` impostato).
- d) **Modulo caricato prima di `/pausa`** (P4-11 C): salvarlo, anche solo cambiando la soglia, rimette "Programmazione automatica"
  come l'aveva mostrato e **toglie la pausa in silenzio**. Il modulo vive poco (è nella finestra delle Impostazioni): probabilità bassa.

**3. Esperimenti**. P4-11 B e C (fatti). Da raccogliere (A-4): le prove gratuite su Telegram (`/ultima`, `/pausa`, `/stato`,
`/riprendi`, `/stato`) e la prova di `/pausa` mandato a PC spento.

**4. Causa**: a e b sono comportamenti previsti o voluti, **da confermare** (domanda 6); d è dimostrata.

**5. Correzione proposta**
- a, b: nessuna modifica di logica se l'utente conferma. Si dice nella risposta di `/pausa` e `/riprendi` quando riprende
  ("Prossima esecuzione: domani alle 07:00", da `self._prossima()`) e nell'Aiuto che i comandi mandati a PC spento non valgono
  (S, mezz'ora: `bot.py:229-239`, `messaggi.py`; `TG-10`: due frasi in più).
- a-bis: non scartare gli aggiornamenti vecchi per `/pausa` e `/riprendi` e far aspettare il primo controllo: M, con il rischio di
  eseguire comandi vecchi (un `/aggiorna` di ieri). Non raccomandata.
- d: il modulo non riscrive la pausa se non l'ha cambiata (campo nascosto con il valore mostrato, oppure una rotta propria per
  l'interruttore). Frontend, `rotte_impostazioni.py:242-249`; quando si tocca quel codice (R-09).
- **Requisito**: `TG-10`, `ESE-01`. **ADR**: nessuno. **Windows e Linux**: nessuna differenza. **Dipende da**: domanda 6; d dal frontend.
- **Test da scrivere prima**: `test_pausa_e_riprendi_a_cavallo_dell_orario_non_avviano_e_non_recuperano` (`tests/esecuzione/test_programmatore.py`,
  orologio iniettato come P4-11 B: fissa il comportamento previsto); `test_salvare_il_modulo_delle_impostazioni_non_toglie_la_pausa_messa_da_telegram`
  (`tests/dashboard/test_rotte.py`: oggi fissa l'errore, commento "vedi I-2 d"); T-32 e T-33 per i gestori (nel gruppo "quando capita", decisione 35).

### Scheda 12. I-3: aggiornamento con il pannello aperto e con un'esecuzione in corso

**Gravità**: media. **Stato**: tre punti **dimostrati** con un servizio simulato (P4-10) o con il codice; il ramo Windows (file in
uso) **da indagare**. **Sforzo** (stima): S-M.

**1. Percorso** (pannello "Aggiorna", `pannello.py:141-151`; CLI, `cli.py:178-186`)
1. `aggiornamento.aggiorna` (`aggiornamento.py:27-68`), in un thread del pannello: `git status`, `git fetch`, `git rev-list` (`:34-43`).
2. Se l'ultima esecuzione, letta da `/api/stato`, è `in_corso`: rifiuta (`:46-48`).
3. Se il servizio è acceso: `richiedi_spegnimento` e `_attendi(leggi_stato is None)` fino a 20 s (`:50-54`): cioè "la porta non risponde".
4. `git merge --ff-only` e `uv sync`, timeout 600 s ciascuno (`:55-62`).
5. `finally`: `_avvia_staccato` e attesa di 20 s che `leggi_stato` risponda; **il risultato non si controlla** (`:63-67`); poi
   "Gradiens è aggiornato" (`:68`).
6. Il pannello ha un thread che legge lo stato ogni 3 s e disabilita Accendi, Spegni e Aggiorna durante l'attesa (`pannello.py:104-119`).
Componenti: pannello (Tkinter, thread) ↔ CLI ↔ servizio (uvicorn) ↔ git ↔ uv ↔ file del `.venv` ↔ (Windows) blocco dei file.

**2. Punti, in ordine di probabilità**
- a) **Nessuno controlla che il servizio riparta** (dimostrato, P4-10 n. 1): 20,1 s di attesa e "Gradiens è aggiornato" senza avviso, anche se
  la migrazione ha fallito (scheda 5) o la porta è occupata. Il pannello mostra "spento"; la CLI stampa il successo.
- b) **"Spento" vuol dire porta chiusa, non processo finito** (dimostrato, P4-10 n. 2 e L-02): `uv sync` parte con il vecchio processo
  ancora vivo, fino a 4,9 s nei log veri. Su Linux è innocuo; su Windows il vecchio servizio tiene i suoi `.pyd`.
- c) **Ambiente del servizio riavviato** (ipotesi della mappa A6, non provata): `_avvia_staccato` lancia `Popen` senza `env`
  (`avvio_sistema.py:20-32`): il servizio eredita l'ambiente del pannello o del terminale, non l'`Environment=GRADIENS_CLAUDE`
  dell'unità systemd (su questa macchina è attiva, con linger). Se il `PATH` della sessione grafica non contiene `~/.local/bin`,
  `claude` non si trova e ogni esecuzione fallisce con "Claude Code non è installato o non è nel PATH".
- d) **Pannello aperto su Windows** (da indagare): il pannello gira con `.venv\Scripts\pythonw.exe` (`avvio_sistema.py:267-272`) e
  ha caricato `pydantic_core` (P4-16, l'unico pacchetto compilato). Se `uv sync` deve sostituirlo (versione nuova nel lock) o
  cambiare Python, Windows rifiuta il file in uso. Il lock non cambia dal 7 novembre (`git log -- uv.lock`), quindi
  finora non si è visto.
- e) **`uv run gradiens aggiorna`** (CLAUDE.md suggerisce `uv run gradiens …`): un `uv sync` annidato dentro `uv run` non si blocca
  (P4-15). Su Windows `gradiens.exe` resta in uso finché il comando gira e `uv sync` può non riuscire a reinstallare il
  progetto. Non provato.
- f) **Esecuzione in corso**: il controllo si fida di `ultima_esecuzione.stato` del database, che si può far mentire in due modi:
  S-11 (un secondo processo scrive "interrotta", scheda 6) e S-06 (resta "in corso" per sempre: l'aggiornamento è bloccato
  fino al riavvio). La corsa "una programmata parte tra il controllo e lo spegnimento" ha una finestra di millisecondi
  (`:46-52`): ne uscirebbe un'esecuzione "interrotta", che si riprende (`ESE-12`). Trascurabile (S-38).

**3. Esperimenti**. P4-10, P4-15, P4-16 (fatti). Da raccogliere: A-6 (prove su Windows) e A-7 (ambiente del servizio riavviato dal
pannello su Linux).

**4. Causa**: a, b dimostrate; c, d, e da indagare (mancano A-6 e A-7).

**5. Correzione proposta**
- a: dopo la riaccensione, se il servizio non risponde entro 20 s, `ErroreAggiornamento("Gradiens non è ripartito: guarda i log in …")`;
  anche dopo un `uv sync` fallito. S, `aggiornamento.py:63-68`. Resta spento e lo dice; tornare indietro con `git reset`
  non basta perché il database può essere già migrato (domanda 8).
- b: correzione C della scheda 6 (spegnere tutto prima di chiudere la porta) e una pausa di 1 s prima di `git merge` e
  `uv sync`, portabile. Dove: `servizio.py:48-56`, `aggiornamento.py:50-54`.
- c: `_avvia_staccato` passa un `GRADIENS_CLAUDE` già risolto, oppure `claude` si cerca anche in `~/.local/bin` come `eseguibile` fa
  per git e uv (`avvio_sistema.py:366-372`); S, `llm/claude_code.py:29-37`. Dopo A-7.
- d: se la prova su Windows fallisce, l'aggiornamento dal pannello lancia un processo separato che aspetta la chiusura del
  pannello, aggiorna e riapre il pannello (M); oppure il pannello avvisa di chiuderlo e usare `gradiens aggiorna`. Dopo A-6.
- **Requisito**: `AMB-05`, `CLI-01`. **ADR**: 0007 e 0009 invariati. **Windows e Linux**: b, d, e solo Windows; a, c, f entrambi.
  **Dipende da**: scheda 6 (C); nessun R-nn (R-06 rende pubbliche `_avvia_staccato` e `_attendi`: nessun conflitto).
- **Test da scrivere prima** (`tests/app/test_aggiornamento.py`): `test_aggiorna_segnala_se_il_servizio_non_riparte` (`leggi_stato` resta
  `None` dopo `_avvia_staccato`, `_attendi` che restituisce `False` come la vera dopo 20 s): oggi fissa il messaggio di successo
  (commento "vedi I-3 a"); nel test esistente `_attendi` è sostituita da `lambda condizione: True` (`:30`), quindi quel ramo non si
  vede mai. `test_aggiorna_aspetta_la_fine_del_vecchio_processo_prima_di_sincronizzare` (servizio simulato come in P4-10 n. 2).

### Scheda 13. I-4: la rete arriva dopo l'avvio

> **Dopo la rilettura**: la correzione B aiuta solo se il servizio si riavvia lo stesso giorno, perché il recupero gira solo al primo controllo dopo l'avvio (`esecuzione/programmatore.py:59-61`); senza riavvio il giorno si perde comunque. Nel log dell'8 novembre il bot era in polling: la rete è arrivata tra 315 e 598 secondi dopo l'avvio, non "mai" (rafforza l'attesa a 15 minuti).

**Gravità**: media, frequenza bassa. **Stato**: meccanismo **dimostrato** (P4-11 D e lettura); nei log il bot ha avuto la rete oltre 4
minuti dopo l'avvio in 3 avvii su 16 (contando anche quello del 13 novembre alle 19:56, con lo stesso criterio) (L-05). **Sforzo** (stima): S.

**1. Percorso**
1. Servizio all'accensione: `ciclo_di_vita` avvia il bot (senza rete fallisce, `_app` resta `None`, `bot.py:123-132`) e poi il
   programmatore, il cui primo `controlla` fa il recupero (`programmatore.py:59-61`) e avvia `esecutore.avvia("programmazione")`.
2. `_pipeline`: `pronto()` (`claude auth status`) e `_attendi_rete`: `rete_disponibile` risolve un nome (solo DNS) ogni 5 s per al massimo
   300 s (`esecutore.py:92-102`, `:169-177`); poi `RuntimeError("Nessuna connessione a internet…")` e stato `fallita`.
3. `finally` → `al_termine` = `bot.invia_esecuzione` (`bot.py:167-178`): se il bot non è collegato ritorna **in silenzio**
   (`:170-171`). `ESE-13` chiede la segnalazione su Telegram.
4. Il recupero: `avviate_dal` conta l'esecuzione fallita (`dati/esecuzioni.py:39-41`, `ESE-01` "di qualunque tipo"): al riavvio
   successivo dello stesso giorno nessun recupero.
5. Il bot riprova a 5, 10, 20, 40, 60 s (`bot.py:145-156`). robots.txt irraggiungibile per la rete non si ricorda (`rete.py:106-110`).
6. La rete controllata è solo il DNS (S-25): un portale captive o un DNS che risponde con un HTTP che no, passano.
Componenti: servizio all'accensione ↔ rete ↔ bot ↔ programmatore ↔ esecutore ↔ Telegram.

**2. Ipotesi in ordine di probabilità**
- **H1 (dimostrata nel meccanismo)**: rete oltre 300 s: recupero fallito, nessun recupero fino a domani, avviso su Telegram perso.
  Dati: l'8 novembre alle 10:08 il bot non si è collegato per almeno 315 s (poi il log tace: probabile sospensione); l'11
  novembre alle 06:41 si è collegato dopo 255-315 s. Il boot dell'8 novembre è quello dell'esecuzione 4, che ha motivato
  l'attesa di 5 minuti: con 300 s sarebbe fallita lo stesso.
- **H2**: i ritardi tipici sono corti: circa 15 s in 9 avvii su 16 (tentativi a 5, 10, 15 s), 5 s in 1, 35-45 s in 2.
- **H3**: oltre alla rete, il recupero serve solo se si accende dopo l'orario: nei log una volta (9 novembre 07:04, rete a 15 s).

**3. Esperimenti**. P4-11 D (fatto, con l'attesa ridotta a 1 s e DNS finto): fallita con "Nessuna connessione a internet…"; riavvio con la
rete: nessun recupero; con il filtro di prova il recupero parte e si completa. Da raccogliere (A-3): le righe "Avvio del bot
Telegram non riuscito" con l'ora, per vedere quanto tardi arriva la rete a ogni accensione.

**4. Causa**: dimostrata; la frequenza reale è bassa.

**5. Correzione proposta**
- **A (raccomandata)**: attesa della rete a 15 minuti (`ATTESA_RETE = 900`, `esecutore.py:92`, 1 riga). Un'esecuzione in attesa
  blocca quelle manuali (`GiaInCorso`) per al massimo 15 minuti; la fase "attesa della rete" si vede nel pannello e in `/stato`.
- **B (con A)**: il recupero non conta le esecuzioni fallite per mancanza di rete: `avviate_dal` le esclude (P4-11 D). Serve una
  costante per quel motivo (nel vocabolario di R-02a) o uno stato proprio. `ESE-01`: "di qualunque tipo" ha un'eccezione.
- C: il bot ricorda gli avvisi non inviati (esecuzioni concluse a bot spento) e li manda alla connessione. S-M; non urgente.
- D: controllare la rete con una richiesta HTTP vera e non solo il DNS (S-25). Non ora.
- **Requisito**: `ESE-01`, `ESE-13`. **ADR**: nessuno. **Windows e Linux**: nessuna differenza di codice (su Windows la rete
  all'accensione potrebbe tardare di più: non misurato). **Dipende da**: R-02a è comodo per la costante, non necessario;
  decisione: domanda 5.
- **Test da scrivere prima**: `test_il_recupero_riparte_dopo_un_esecuzione_fallita_per_mancanza_di_rete`
  (`tests/esecuzione/test_programmatore.py`: riga `esecuzioni` `fallita` con il motivo di rete scritta con `esecuzioni.termina`,
  `Programmatore` con orologio iniettato): oggi fissa "nessun recupero" (commento "vedi I-4"); per l'attesa
  `test_aspetta_la_rete_fino_a_quindici_minuti` con `time.monotonic` e `asyncio.sleep` sostituiti (accanto a
  `tests/esecuzione/test_esecutore.py:425`).

### Scheda 14. I-5: cache e robots.txt in memoria dopo un riavvio

> **Dopo la rilettura**: dimenticare subito anche il verdetto 429 aumenterebbe le richieste a un sito che ha chiesto di rallentare (`WEB-18`): la correzione A va limitata ai 5xx.

**Gravità**: bassa. **Stato**: **dimostrata** (P4-12). **Sforzo** (stima): S.

**1. Percorso**
1. `fonti/siti/rete.py:30-33`: tre dizionari di modulo (`_robots`, `_prossima`, `_cache`) condivisi da tutti i `Navigatore` del processo e
   persi a ogni riavvio (spegni-avvia, `aggiorna`, accensione).
2. `_regole` (`:100-117`): robots.txt riletto dopo 3600 s; 4xx = tutto permesso; **5xx o 429 = tutto vietato, ricordato un'ora** (`:114-116`).
3. `_scarica` (`:137-169`): richieste condizionate (ETag, Last-Modified) solo per feed e sitemap; un 304 restituisce la pagina salvata.
4. `_attendi_turno` (`:171-181`): 1 s per host (o il Crawl-delay fino a 10 s).

**2. Effetti del riavvio** (P4-12)
- a) robots.txt si rilegge comunque a ogni esecuzione giornaliera: il riavvio non cambia le richieste (`[robots.txt, feed 200]`,
  `[robots.txt, feed 304]`, `[robots.txt, feed 200]`).
- b) Si perdono ETag e Last-Modified: 1.570 byte contro 0. Solo byte, non richieste.
- c) **Un divieto passeggero (503) dura un'ora e sparisce solo con un riavvio**: due esecuzioni a 20 minuti, la seconda non fa nemmeno
  la richiesta e dà "guasto"; con un riavvio in mezzo funziona. Sono due guasti per `WEB-24` (il terzo rigenera il profilo,
  S-34). Capita solo con due esecuzioni a meno di un'ora (una a mano subito dopo quella programmata).
- d) Le pause si azzerano: dopo il riavvio la prima richiesta a ogni host parte subito. Innocuo.

**3. Esperimenti**. P4-12 (fatto). Da raccogliere: niente.

**4. Causa**: c dimostrata, a bassa probabilità; il resto sono effetti attesi, non difetti.

**5. Correzione proposta**
- **A (raccomandata)**: il verdetto "5xx o 429" non si ricorda oltre il `Navigatore` (o per 5 minuti): `rete.py:114-116` (S; scraping-engineer).
- B: cache su disco con richieste condizionali (proposta 6a-10): risparmia byte, non richieste. Non vale ora.
- **Requisito**: `WEB-18`, `WEB-24`. **ADR**: nessuno. **Windows e Linux**: nessuna differenza. **Dipende da**: nessun R-nn.
- **Test da scrivere prima**: T-46 (parte robots 503 e 429, `tests/fonti/siti/test_rete.py`, nuovo) e
  `test_un_robots_txt_503_non_vieta_la_seconda_esecuzione_a_venti_minuti` (fixture `rete_pulita`, `time.monotonic` sostituito).

### Scheda 15. C-1: prove su Windows non fatte (da `piano-fase-4.md`)

**Gravità**: da indagare. **Stato**: manca la prova. **Sforzo**: nessuno finché non si prova.

Il piano dice che il 12 novembre su Windows non sono stati provati: `esegui` completo (quota), `aggiorna` (vedi scheda 12), la
registrazione dell'avvio all'accensione (UAC) e la creazione delle icone; restano da provare anche il ripiego dalla sessione 0, l'accensione senza
accesso e `ACC-09`; dalla fase 2 restano la codifica dell'uscita di `schtasks` (S-29) e il layout di `claude.cmd`.

**1. Percorso**: attività pianificata (`avvio_sistema.py:193-260`: script PowerShell con S4U e trigger `-AtStartup`;
`_come_amministratore` `:229-238`; sessione 0); icone (`:262-310`: PowerShell e `WScript.Shell` creano `.lnk` che lancia `pythonw.exe -m
gradiens pannello`); `cli.py:124-151` (`esegui`); `llm/claude_code.py:29-37` e `avvio_sistema.py:35-40` (da `claude.cmd` a `claude.exe`).
**2. Ipotesi**: nessuna da ordinare, sono prove da fare a mano. **3. Esperimenti**: nessuno possibile qui; l'elenco è in A-6.
**4. Causa**: non applicabile. **5. Correzione**: dopo le prove. Test già presenti: `tests/app/test_avvio_sistema.py` (CI Windows, con
`schtasks` finto).

---

## Il resto, senza schede

**Giudizio su S-30, S-31 e S-36**: non li considero gravi, quindi stanno nella tabella dei sospetti minori. Dati: nelle esecuzioni 9 e
10 le notizie dei siti "senza contenuto" sono 1 su 189 e 0 su 84 (e le uniche viste erano pagine che non erano articoli); nei log
non c'è nessun errore di rete in `completa` né un "Elaborazione fallita" in 8 giorni (L-07). Una nota su S-30: la sua correzione
(non segnare vista una notizia il cui contenuto è mancato per la rete) deve andare **insieme** alla regola "coperto fino a"
della decisione 34, altrimenti la notizia non riprovata trattiene il sito.

### Già deciso dall'utente (una riga ciascuno)

| Codice | Che cosa | Dove è deciso | Stato |
|---|---|---|---|
| S-34 | la rigenerazione sostituisce un profilo buono con uno senza strategie | decisione 21 (si tiene il profilo vecchio; si sostituisce solo se si trova una strategia) | da implementare (T-14; A-02 B.1) |
| voci di altri domini nei feed | le voci su altri domini si accettano tutte | decisione 18 (fuori, salvo siti collegati attivi) | da implementare (T-19) |
| date dalla sola sitemap | un articolo vecchio con `lastmod` recente sembra nuovo (1 su 15) | decisione 16: si lascia così | chiusa |
| S-20 | date future accettate da feed e sitemap | decisione 16: resta il rifiuto delle date future | da implementare (T-21) |
| S-03 | "rate limit" trattato come quota esaurita | decisione 27: si lascia così | chiusa |
| tetti di hwupgrade | 40 pagine e 100 articoli; tetto prima del registro delle viste | ADR 0011 e proposta 6a-3 | in attesa dell'ADR |
| S-16 | il POST parziale delle Impostazioni mette in pausa e spegne le esclusioni | non è un bug (casella non spuntata = non inviata; già fissato da test) | chiusa |
| S-10 | PC sospeso all'orario: esecuzione non recuperata | previsto da `ESE-01` (recupero solo all'avvio); resta da correggere il docstring `programmatore.py:4-6` | chiusa |
| S-22 | robots.txt 5xx o 429 vieta il sito | previsto (RFC 9309); la parte "ricordato un'ora" è la scheda 14 | chiusa |
| S-35 | date incerte oltre il tetto di pagine passano come nuove | previsto da `ESE-03`; il costo è nell'ADR 0011 e in 6a-3 | chiusa |
| S-19 | copia di sicurezza fallita impedisce l'avvio | probabilmente voluto (meglio non partire che migrare senza copia); l'errore di rotazione è nella scheda 5 (C) | chiusa |
| S-17 | `GRADIENS_CLAUDE` nel `.env` ignorato | disallineamento di documentazione (nessun documento lo promette per quella variabile) | da correggere nei documenti |
| quota con categorie arXiv molto attive | con categorie come `cs.AI` il pre-filtro costa molte chiamate (`piano-fase-4.md`, "Quota") | ADR 0010 e decisioni 8 e 9 (pre-filtro fino al tetto; tetto 30) | da implementare |

### Sospetti minori (si correggono quando si tocca quel codice)

| Codice | Descrizione | Dove | Vedi |
|---|---|---|---|
| S-13 | il cuore da Telegram inverte il valore del database, non quello del bottone; con `reply_markup` `None` solleva dopo aver scritto | `telegram/bot.py:244-261` | doc. 02, T-34 |
| S-14 | `/api/spegni` e `X-Forwarded-For` dietro un proxy locale (non provato) | `app/servizio.py:50-51` | doc. 02; pesa nella 6c |
| S-15 | `HX-Current-URL` uguale a `/configurazione` con una sezione fuori dai passi dà 500 | `dashboard/rotte_impostazioni.py:47-48` | doc. 02, T-31 |
| S-23 | il timeout di httpx è per operazione, non totale (3,9 s con timeout 0,5) | `fonti/siti/rete.py:145` | doc. 02, T-46 |
| S-24 | sitemap o feed enormi interpretati nel ciclo di eventi (2,0 s per 50.000 voci) | `fonti/siti/strategie/sitemap.py:26` | doc. 02, T-47; innesco di S-37 (scheda 6, H3) |
| S-25 | una risposta 200 non valida di arXiv o YouTube dà 0 risultati e stato "ok"; la rete si controlla solo con il DNS | `fonti/arxiv/__init__.py:59-65`, `fonti/youtube/__init__.py:111`, `esecutore.py:96-102` | doc. 02, T-22, T-48; scheda 13 (D) |
| S-26 | arXiv: una voce scartata ferma la paginazione | `fonti/arxiv/__init__.py:65` | doc. 02, T-48 |
| S-27 | soglia 0 con punteggio 0: notizia "mostrata" ma invisibile | `esecutore.py:439`, `:452` | doc. 02, T-28 |
| S-28 | `cli._riepilogo` indicizza chiavi che le metriche vecchie non hanno | `app/cli.py:109-112` | doc. 02, T-30 |
| S-29 | uscita di `schtasks` letta come UTF-8 (percorso con accenti) | `app/avvio_sistema.py:106` | doc. 02, T-38; prova A-6 |
| S-30 | errore di rete in `completa` = "errore di estrazione" definitivo | `fonti/siti/estrazione.py:55-57`, `esecutore.py:304-309` | doc. 02, T-12; con la decisione 34 |
| S-31 | `completa` non ricontrolla la finestra | `fonti/siti/estrazione.py:61-62` | doc. 02, T-17 |
| S-33 | timeout e nuovo tentativo raddoppiano durata e quota (fino a 600 s) | `llm/claude_code.py:81-83` | doc. 02, T-29 |
| S-36 | una valutazione fallita fa ripassare la notizia da pre-filtro e valutazione a ogni esecuzione | `esecutore.py:312-315` | doc. 02, T-04; proposta 6b-12; mai osservata (L-07) |
| S-37 | la prima richiesta di `gradiens esegui` non è protetta; un servizio occupato sembra spento | `app/cli.py:128`, `:17-24` | scheda 6 (B) |
| S-38 | `aggiorna`: spegnimento in un momento sbagliato (finestra di millisecondi) | `app/aggiornamento.py:46-52` | scheda 12 (f) |
| S-39 | il motivo di un'esecuzione fallita non si accorcia nel messaggio Telegram (limite 4.096) | `telegram/messaggi.py:13`, `bot.py:177-178` | doc. 02, T-35 |
| sezioni proposte | le sezioni proposte dall'analisi di un sito sono a volte poco utili (conferenze, partner, piè di pagina) | `fonti/siti/pagine.py:83-97` | qualità della ricerca: proposte 6a; mappa C4 |
| ACC-15 | manca l'avvertimento di Claude Code non collegato (sezione Modelli LLM) | `piano-fase-4.md` (fetta 7e) | rimandato con la 7a |
| stati dei siti | lo stato di un sito nel resoconto si collega alle notizie nuove dal nome della fonte: due siti dello stesso dominio mostrano il totale di entrambi | `esecutore.py:267-272` | `piano-fase-4.md` (fetta 4b); scheda A-03 |

I sospetti S-01, S-02, S-04, S-05, S-06, S-07, S-08, S-09, S-11, S-12, S-18, S-21, S-32 hanno la loro scheda (1-9). S-02, S-04 e S-07
stanno nella scheda 4; S-08 nella 3.

---

## Che cosa deve raccogliere l'utente

Elenco unico e ordinato. Tutto è gratuito (nessuna quota LLM) tranne dove è scritto. Dalla cartella di Gradiens, con `uv`.
Nessun dato raccolto va incollato nei documenti: restano in `.gradiens/misure/` (esclusa da git, decisione 14).

**A-1. Salvare oggi il feed del canale YouTube** (una richiesta). Il feed mostra solo gli ultimi 15 video: i 7 video esclusi
escono quando il canale ne pubblica altri 15, forse in pochi giorni. Serve a S-01 (ipotesi H3 e prove con l'LLM).
1. L'identificativo del canale (uguale su Linux e Windows; comincia con `UC`):
   `uv run python -c "import sqlite3; print(sqlite3.connect('file:.gradiens/gradiens.db?mode=ro', uri=True).execute('select id from canali_youtube').fetchall())"`
2. Linux: `mkdir -p .gradiens/misure && curl -o .gradiens/misure/feed-canale-2026-11-14.xml "https://www.youtube.com/feeds/videos.xml?channel_id=UC..."`
3. Windows (PowerShell): `New-Item -ItemType Directory -Force .gradiens\misure | Out-Null; Invoke-WebRequest "https://www.youtube.com/feeds/videos.xml?channel_id=UC..." -OutFile .gradiens\misure\feed-canale-2026-11-14.xml`
4. Annotare data e ora del salvataggio.

**A-2. Guardare a mano le notizie escluse dei siti.** Nella dashboard, pagina di un'esecuzione (la 9 del 10 novembre e la 10
dell'11), elenco delle escluse (titolo e link): sono 23 e 11 per i siti. Annotare quante **non** erano sponsorizzate o
offerte. Serve a sapere se il verdetto sbagliato di S-01 riguarda solo YouTube.

**A-3. Log dopo qualche giorno di uso normale.** I log ruotano a 1 MB per 3 copie: conviene copiarli oggi e ogni 2-3 giorni in
`.gradiens/misure/log-AAAA-MM-GG/` (Linux: `mkdir -p .gradiens/misure && cp -r .gradiens/log .gradiens/misure/log-2026-11-14`; Windows:
`New-Item -ItemType Directory -Force .gradiens\misure | Out-Null; Copy-Item -Recurse .gradiens\log .gradiens\misure\log-2026-11-14`). Righe da cercare:
- Linux: `grep -c "locked" .gradiens/log/gradiens.log*`; `grep -c "address already in use" .gradiens/log/gradiens.log*`;
  `grep -c "Conflict" .gradiens/log/gradiens.log*`; `grep "Avvio del bot Telegram non riuscito" .gradiens/log/gradiens.log* | tail -n 20`;
  `grep "Esecuzione programmata saltata" .gradiens/log/gradiens.log*`; `grep "Esecuzione .* fallita" .gradiens/log/gradiens.log*`.
- Windows (PowerShell): `Select-String -Path .gradiens\log\gradiens.log* -Pattern "locked" | Measure-Object | Select-Object -ExpandProperty Count`
  (stesso comando con `"address already in use"` e `"Conflict"`); `Select-String -Path .gradiens\log\gradiens.log* -Pattern "Avvio del bot Telegram non riuscito" | Select-Object -Last 20`;
  `Select-String -Path .gradiens\log\gradiens.log* -Pattern "Esecuzione programmata saltata"`.
- Annotare per ogni riga trovata: l'ora e che cosa si stava facendo (uno strumento sul database aperto? un `spegni` e `avvia` appena fatti?).

**A-4. Prove su Telegram** (gratuite; **non** mandare `/aggiorna`, che avvia un'esecuzione intera). Ora la programmazione è
**in pausa** (D-01): alla fine rimetterla come la vuoi. Nell'ordine, dal telefono: `/ultima` (deve rimandare il messaggio
dell'ultima esecuzione conclusa), `/stato` (deve dire "programmazione in pausa"), `/riprendi`, `/stato` (deve mostrare la
prossima esecuzione), `/pausa`. Annotare ogni risposta diversa dall'attesa; le righe `Telegram: /ultima`, `/pausa`… devono
comparire nel log. Prova a PC spento: `uv run gradiens spegni`, mandare `/riprendi` da Telegram, `uv run gradiens avvia`,
guardare in Impostazioni, Esecuzione, se "Programmazione automatica" è cambiata (previsione: no, il comando è perso); poi
rimettere la pausa.

**A-5. Il `Conflict` del 12 novembre alle 14:21.** Rispondere: a quell'ora era acceso Gradiens (o un'altra prova con lo stesso
token) sul PC Windows? Nessun comando.

**A-6. Prove su Windows** (al PC Windows, PowerShell, dalla cartella di Gradiens). Annotare per ognuna esito e testo completo di
un eventuale errore.
1. **File in uso con il pannello aperto**: `.\.venv\Scripts\pythonw.exe -m gradiens pannello` (lasciarlo aperto); in un altro
   PowerShell `uv sync --reinstall-package pydantic-core`. Atteso se il problema esiste: "Accesso negato (os error 5)". Poi
   chiudere il pannello e rilanciare `uv sync`.
2. **`gradiens.exe` in uso**: aprire il pannello con `uv run gradiens pannello` e, da un altro PowerShell, `uv sync --reinstall-package gradiens`.
3. **`gradiens aggiorna` su una copia usa e getta** (non tocca l'installazione vera): `git clone <indirizzo del repository> C:\prova-gradiens`;
   `cd C:\prova-gradiens`; `uv sync`; `git reset --hard HEAD~1`; `$env:GRADIENS_PORTA = "8799"`; `uv run gradiens avvia`;
   `uv run gradiens aggiorna`. Annotare i messaggi, i secondi di attesa e se compare "Gradiens è aggiornato" con il servizio
   spento. Poi `uv run gradiens spegni` e cancellare la cartella.
4. **Avvio all'accensione (UAC)**: Impostazioni, Avvio, attivare. Annotare se compare la conferma di Windows, se l'attivazione
   riesce, lo stato che la sezione mostra; riavviare il PC e, senza aprire niente, dopo l'accesso `uv run gradiens stato`
   (è acceso da prima? da che ora?).
5. **Icone**: Impostazioni, Avvio, icone sul desktop e nel menu. Annotare se compaiono, se il collegamento apre il pannello
   senza finestra nera, se l'icona è giusta.
6. **`uv run gradiens esegui` completo** (**costa quota**: un'esecuzione intera; quando vuoi). Annotare l'output finale e
   copiare da `.gradiens\log\gradiens.log` le righe `Esecuzione N …` (senza titoli).
7. **Codifica di `schtasks`** (S-29): `schtasks /Query /TN Gradiens /XML` (tutto l'output) e `chcp`; se il nome utente ha accenti,
   annotare se la sezione Avvio dice "un'altra cartella".
8. **`bind` sulla stessa porta** (scheda 6, A): salvare queste righe in `$env:TEMP\bind.py` e lanciare, dalla cartella
   di Gradiens, `.\.venv\Scripts\python.exe $env:TEMP\bind.py`; annotare le due righe stampate (previsione: senza `SO_REUSEADDR` rifiutato, con
   `SO_REUSEADDR` riuscito).
   ```
   import socket
   a = socket.socket(); a.bind(("127.0.0.1", 0)); a.listen(5); porta = a.getsockname()[1]
   for reuse in (False, True):
       b = socket.socket()
       if reuse: b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
       try: b.bind(("127.0.0.1", porta)); print("SO_REUSEADDR", reuse, "-> bind riuscito")
       except OSError as e: print("SO_REUSEADDR", reuse, "-> rifiutato", e.errno)
   ```

**A-7. Ambiente del servizio riavviato dal pannello (Linux)**. Aprire il pannello dall'icona del menu (non da un terminale),
premere Spegni e poi Accendi; poi in un terminale:
`tr '\0' '\n' < /proc/$(pgrep -f "gradiens avvia" | head -1)/environ | grep -E '^(PATH|GRADIENS_CLAUDE)='` e `which claude`.
Annotare se la cartella di `claude` (`~/.local/bin`) compare nel `PATH` del servizio. Il `PATH` non è un segreto.

---

## Domande per l'utente

Solo scelte che dipendono da te. Ognuna con la risposta consigliata.

1. **S-01: l'esclusione "sponsorizzati e offerte" smette di valere per i video?** I video segnalati passano alla
   valutazione; per arXiv e per i siti resta com'è (dopo la rilettura: estesa ad arXiv farebbe entrare nel tetto i paper
   segnalati). *Consiglio: sì.* `WEB-22` parla di articoli dei siti; la correzione non dipende dalla causa del verdetto
   e rimette i video nel flusso. Costo: ogni video in più passa dalla valutazione (stima della 6b: 7-29 mila token).
2. **S-21 e ADR 0011: "coperto fino a" con un margine di rilettura pari al ritardo misurato del feed di quel sito?**
   (Dopo la rilettura: un margine fisso di 2 giorni, con la finestra di 3, annullerebbe la raccolta incrementale.)
   *Consiglio: sì, mai oltre la finestra.* Senza margine un feed in ritardo di qualche ora perde articoli senza segnali;
   il margine costa la rilettura di quelle ore (e della sitemap, dove c'è).
3. **S-01: autorizzare circa 85.000 token di prove con l'LLM per capire perché i video venivano segnalati?** *Consiglio: no ora.*
   La correzione funziona a prescindere; basta salvare oggi il feed (A-1) e far registrare i sommari degli esclusi alla
   prossima esecuzione. Se vuoi sapere la causa, la prova da 7.500 token (1 video + 1 articolo, 3 volte) è la più utile.
4. **S-32: oltre al redirect, controllare anche i nomi DNS che puntano alla rete di casa?** *Consiglio: no ora.* Il redirect è
   la falla pratica (una GET in chiaro); il controllo dei nomi costa di più e può far fallire siti legittimi (VPN, Tailscale).
   Sì se si fa la 6c (dashboard da internet).
5. **Rete tardiva: attesa a 15 minuti e il recupero non conta le esecuzioni fallite per mancanza di rete?** *Consiglio: sì a
   entrambe.* Nei log, 3 avvii su 16 (contando anche quello del 13 novembre alle 19:56, con lo stesso criterio) hanno avuto la rete dopo oltre 4 minuti; con più di 5 minuti il giorno si perde. `ESE-01` ("di
   qualunque tipo") avrebbe un'eccezione.
6. **Pausa: i comandi `/pausa` e `/riprendi` mandati a PC spento devono valere all'accensione, e `/riprendi` dopo l'orario deve
   avviare l'esecuzione mancata?** *Consiglio: no a entrambe*, scrivendolo nella risposta del bot e nell'Aiuto. I comandi vecchi
   sono rischiosi (un `/aggiorna` di ieri) e `ESE-01` dice già che in pausa non si recupera niente.
7. **S-18: ripristino automatico dalla copia se una migrazione fallisce?** *Consiglio: no.* Basta che la copia pulita non
   venga mai sovrascritta e che l'errore dica quale copia usare; un ripristino automatico può cancellare dati scritti nel
   frattempo. (La transazione con `BEGIN` esplicito provata in questa fase fa perdere dati e va riprogettata.)
8. **`gradiens aggiorna`: se il servizio non riparte, resta spento e lo dice?** *Consiglio: sì.* Tornare alla versione
   precedente non basta se il database è già migrato; un messaggio chiaro con il percorso dei log è la cosa più utile.

---

## Registro delle prove fatte in questa fase

Cartella delle prove: `scratchpad/fase4/` nella cartella temporanea della sessione (si svuota al riavvio: l'esito sta qui).
Comando tipo, dalla radice del progetto: `PYTHONDONTWRITEBYTECODE=1 uv run --frozen python -I <script>`. Nessuna prova ha
chiamato un LLM, usato la rete di internet, letto il `.env` o scritto in `.gradiens/` o nel progetto: database temporanei,
fonti e provider finti, server locali su 127.0.0.1. Dati veri letti solo in sola lettura (`mode=ro`): database, copie in
`.gradiens/backup/` e log in `.gradiens/log/` (dai log non si riportano nomi di canali, titoli o chat).

- **P4-01** (`p4_01_blocchi.py`): l'`Esecutore` vero con fonti e provider finti, con i numeri delle esecuzioni vere (da
  `esecuzioni.metriche`): esec. 1 = 62 paper + 2 video + 1 articolo; esec. 8 = 0 + 1 + 1; esec. 9 = 677 + 3 + 189; esec. 10 =
  412 + 3 + 84. Esito: esec. 1: 3 blocchi, i 2 video stanno nell'ultimo (5 voci: 2 paper, 2 video, 1 articolo), id 2 e 3;
  esec. 8: 1 blocco da 2 voci (1 video + 1 articolo), id 0; esec. 9: 29 blocchi, i 3 video nel blocco n. 23 (17 paper + 3
  video + 10 articoli), id 17-19; esec. 10: 17 blocchi, i 3 video nel blocco n. 14 (22 paper + 3 video + 5 articoli), id 22-24.
- **L-01** (lettura di `.gradiens/log/gradiens.log` e dei suoi 3 file ruotati, 54.155 righe, dal 6 novembre 23:15 al 14
  novembre 03:08; script in memoria, righe con dati personali non riportate): 56 avvii del servizio, 41 spegnimenti
  chiesti dalla CLI; nessuna riga con "locked"; nessun errore 500/403/409 nel log degli accessi (1.983 risposte 200, 49
  304, 21 404, 1 204); 3 esecuzioni fallite (tutte "Claude Code non è collegato a un account", 8 novembre); 379 errori
  di polling di Telegram (350 per "name resolution", il resto: 10 "Bad Gateway", 9 "Conflict", 5 "handshake", 5 "ReadError").
- **L-02** (stesso log): tempo tra "Spegnimento richiesto dalla CLI" e "Gradiens spento" in 41 spegnimenti: minimo 0,11
  s, mediana 0,50 s, massimo 4,91 s; in 12 casi su 41 tra 3,3 e 4,9 s (in 11 dei 12 casi lunghi il bot era acceso e il
  tempo passa prima della riga "Application is stopping", cioè mentre si ferma il polling). Un nuovo "Started server process"
  compare prima della fine del vecchio in 9 casi su 41 (sempre 1 s dopo la richiesta di spegnimento).
- **L-03** (stesso log): gli 8 errori `telegram.error.Conflict` "terminated by other getUpdates request" dei giorni 7 e 8
  novembre (e uno il 12) sono tutti nel processo che si sta spegnendo, mentre il nuovo processo ha già avviato il suo bot
  (8 casi su 9 di L-02); uno, il 12 novembre alle 14:21, è un errore di polling di un processo acceso da ore, senza
  nessun'altra richiesta nel log e senza un secondo servizio sullo stesso PC.
- **L-04** (stesso log): una volta (6 novembre 23:15:20) un secondo servizio ha scritto "Application startup complete" e
  subito dopo "error while attempting to bind on address ('127.0.0.1', 8765): address already in use".
- **L-05** (stesso log): dall'avvio del servizio all'apertura della porta passano al massimo 1,19 s (55 avvii, mediana 0,18
  s). Avvii con il primo tentativo del bot fallito per mancanza di rete: 21; dal 7 novembre alle 15:37 in poi (prima i
  processi si sovrappongono nel file e i tempi non sono affidabili) il bot si collega di solito dopo circa 15 s (tentativi a
  0, 5 e 15 s), in 5, 35 e 45 s in tre casi, in 315,6 s l'11 novembre (tentativi falliti a 255 s, il successivo riuscito),
  mai entro 315 s l'8 novembre alle 10:08 (poi il log tace per 3 ore: probabile sospensione del PC) e dopo ore in due avvii
  del 13 novembre con il PC sospeso. Quel boot dell'8 novembre è quello della esecuzione 4 (recupero senza rete, durata 1,4 s).
- **L-06** (stesso log, finestra delle esecuzioni 9 e 10, ore del PC = UTC + 1): durante i 7 min 25 s dell'esec. 9 la
  dashboard ha interrogato l'avanzamento 243 volte ogni 2,0 s (massimo intervallo 2,69 s); durante i 4 min 10 s dell'esec.
  10 ogni 4,0 s (massimo 5,0 s): il ciclo di eventi non è mai stato fermo più di circa 1 s.
- **D-01** (database e copie in sola lettura): `impostazioni.programmazione_in_pausa` = 1 in tutte le copie dall'8
  novembre 14:21 in poi (messo dalla dashboard: il log mostra 2 `POST /impostazioni/esecuzione` alle 14:11 dell'8 e nessun
  comando `/pausa`): il programmatore ha avviato solo 2 esecuzioni vere (la 3 il 7 e la 4 l'8 novembre), nessuna dopo l'8.
  Orario 07:00; finestra 1 giorno fino al 10 novembre e 3 giorni dall'11 (le esec. 9 e 10 probabilmente con 3); 3 interessi
  senza Raffinamento; nessuna proposta. L'impronta della tabella `interessi` è identica nelle 7 copie giornaliere dall'8 al
  14 novembre e nel database di oggi: il prompt di sistema del pre-filtro conteneva gli stessi interessi nelle esec. 8, 9, 10
  e oggi.
- **D-02** (copie in `.gradiens/backup/`, sola lettura): i due short mostrati nell'esecuzione 1 non sono più nel database
  (cancellati dalla pulizia dei 7 giorni) ma stanno ancora nelle copie giornaliere fino al 13 novembre: descrizioni di 224
  e 248 caratteri, entrambe di 2 righe (la prima di 175 e 199 caratteri con 3 e 2 hashtag), **la seconda riga è identica
  nei due short (48 caratteri)**, nessun link, nessuna parola "corso".
- **P4-02** (`p4_02_feed_in_ritardo.py`, `fonti.siti.raccogli` vero con `httpx.MockTransport`): sito finto con articoli di età
  (a R0) 2, 8, 20, 30, 50, 80, 120 ore; il feed li mostra 36 ore dopo la pubblicazione (come il feed di redhotcyber misurato
  il 12 novembre), la news sitemap subito; 4 esecuzioni a distanza di 24 ore, finestra 3 giorni. **Oggi** (ogni esecuzione
  rilegge la finestra): R0 trova [50], R1 [20, 30], R2 [2, 8]: tutti raccolti, con 44-56 ore di ritardo, stato "ok", nessun
  guasto, la sitemap non si legge fino a R3. **ADR 0011 come scritto** (`dal = max(R - 3 giorni, coperto_fino_a)`, con
  `coperto_fino_a` = ora della raccolta precedente): R0 trova [50], poi R1, R2, R3 non trovano niente (stato "nessun
  articolo nuovo", nessun guasto, la sitemap viene letta ma le sue voci sono più vecchie di `dal`): gli articoli di età 2,
  8, 20 e 30 ore non vengono mai raccolti. Con la sola sitemap (date esatte) invece R0 li trova tutti.
- **P4-03** (`p4_03_database_bloccato.py`, `Esecutore` vero, 60 paper arXiv con tetto 40, provider finto con latenza 0,2 s e al
  massimo 3 chiamate insieme; un thread con una connessione `sqlite3` propria prende un blocco a 1 s dall'inizio; un
  "battito" ogni 0,05 s misura il ciclo di eventi). A) blocco di scrittura (`BEGIN IMMEDIATE`) per 3 s: esecuzione
  "completata", 40 notizie salvate, ciclo fermo al massimo 3,02 s, `avanzamento` torna `None`. B) scrittura per 11 s:
  `OperationalError: database is locked` esce da `attendi` (`esecutore.py:163`, `termina`), il ciclo resta fermo fino a 4,98 s
  per volta, nel database l'esecuzione resta `in_corso`, 9 notizie salvate, `avanzamento` resta impostato (fase valutazione,
  40 di 40) e `avvia()` risponde `GiaInCorso`. C) transazione di lettura aperta per 11 s: come B (ciclo fermo 4,98 s, motivo
  salvato "unhandled errors in a TaskGroup (3 sub-exceptions)", `termina` solleva ancora `database is locked`,
  `avanzamento` impostato, `GiaInCorso`). D) come B con la correzione proposta (sottoclasse di prova: `avanzamento = None`
  in un `finally` annidato, `termina` riprovato 3 volte a distanza di 0,5 s, motivo costruito dalle eccezioni foglia):
  stato `fallita`, motivo "OperationalError: (sqlite3.OperationalError) database is locked…", `avanzamento` `None`, nessuna
  eccezione fuori da `attendi`, durata 12,1 s. Il ciclo di eventi resta fermo fino a 4,98 s anche in D: la correzione non
  risolve il blocco del ciclo.
- **P4-04** (`p4_04_ora_solare.py`, `Programmatore.controlla` vero con `TZ=Europe/Rome`, database temporaneo, tempo UTC
  avanzato di 30 s per volta e orologio locale senza fuso come `datetime.now()`, esecutore finto che scrive una riga vera in
  `esecuzioni`): con orario 02:30 il 25 ottobre 2026 (ora solare) il programmatore vero avvia **2 volte** (02:30:00 CEST e
  02:30:00 CET); il 29 marzo 2026 (ora legale) 1 volta (alle 03:00 CEST); con orario 07:00 una volta in entrambi i giorni.
  Con la correzione di prova (a ogni scadenza si controlla `esecuzioni.avviate_dal(scadenza in UTC)`, oggi fatto solo al
  primo controllo dopo l'avvio) le partenze sono 1, 1, 1, 1 negli stessi casi.
- **P4-05** (`p4_05_robots_redirect.py`, due server `asyncio` veri su 127.0.0.1 con porte libere, nessuna rete esterna;
  A = "il sito", risponde 302 a `/robots.txt` verso B, B = "il dispositivo di casa", registra le richieste;
  `Navigatore.leggi` vero, che non controlla l'indirizzo iniziale): **codice di oggi**: B riceve `GET /riavvia-il-router
  HTTP/1.1` e la pagina si legge (200). **Correzione di prova** (sottoclasse che segue a mano i redirect di robots.txt e
  controlla `indirizzo_pubblico` a ogni salto, come `leggi` fa per le pagine): B non riceve niente, esito 0 (errore di
  rete). Controllo collegato: `ip6-localhost` si risolve in `::1` su questa macchina e `normalizza` lo accetta
  (`https://ip6-localhost:8765/api/stato`), `localhost` invece è rifiutato: i nomi che puntano a indirizzi di casa
  passano il controllo (non coperto dalla correzione del redirect).
- **P4-06** (`p4_06_risposte_e_motivi.py`, `Esecutore` vero, 6 paper arXiv, `BLOCCO_PREFILTRO` = 3 cioè 2 blocchi, provider
  finto che altera una risposta; ogni caso in tre varianti: codice di oggi, (a) `_tutti` di prova che dà la precedenza alla
  quota e spacchetta l'errore singolo, (a)+(b) più un controllo di forma applicato alla risposta di ogni provider: chiavi
  obbligatorie e tipo dei contenitori, `ErroreLLM` se non tornano). Esiti, nell'ordine "stato, viste, salvate, errori":
  - pre-filtro `{}`: oggi completata, 6 viste, 3 salvate, 3 notizie scartate **e segnate viste**; con (b) completata, 3
    viste, 3 salvate, 3 errori (il blocco si riprova alla prossima);
  - `pertinenti: null`: oggi fallita, motivo "unhandled errors in a TaskGroup (1 sub-exception)", 0 viste, 0 salvate (anche il
    blocco buono); con (a) fallita con motivo "'NoneType' object is not iterable"; con (a)+(b) completata, 3 viste, 3 salvate,
    3 errori;
  - `pertinenti: "tutti"`: come `{}` (3 notizie perse e segnate viste); con (b) 3 errori;
  - `punteggi: ["x"]`: oggi fallita, "(6 sub-exceptions)", 0 salvate; con (a) motivo "'str' object has no attribute 'get'";
    con (b) completata con 6 errori;
  - `riassunto: null`: oggi completata e salvato il testo `"None"` per 6 notizie; con (b) 6 errori e nessuna salvata;
  - una quota e un `RuntimeError` in due blocchi: oggi fallita con motivo " (2 sub-exceptions)"; con (a) interrotta con
    il motivo della quota.
- **P4-07** (`p4_07_migrazione.py`, database temporaneo portato alla 0011 con le migrazioni vere, un sito dentro; una 0012 di
  prova in una copia della cartella delle migrazioni: due `add_column` su `siti` come quelle dell'ADR 0011 e poi
  un'eccezione). **`database.migra` vero**: dopo il primo avvio fallito la colonna `coperto_fino_a` esiste, `alembic_version`
  è ancora 0011, 1 copia `-migrazione` (pulita, senza la colonna); il secondo, terzo e quarto avvio falliscono con "duplicate
  column name: coperto_fino_a" e ognuno scrive una nuova copia: dopo il 2º le copie sono 2, dopo il 3º sono 3 (1 pulita),
  **dopo il 4º sono 3 e nessuna è pulita** (la rotazione a 3 copie ha cancellato quella fatta prima del primo guasto). Con
  due avvii nello stesso secondo (il nome della copia ha la precisione del secondo) resta 1 sola copia e **non è pulita**: la
  seconda sovrascrive la prima. **Migrazione con `BEGIN` esplicito** (motore con `isolation_level = None` e un `BEGIN` nel
  gancio `begin`, come descrive la documentazione di SQLAlchemy per il DDL transazionale di `pysqlite`): dopo l'errore la
  colonna non esiste, `alembic_version` è 0011, e un secondo tentativo fallisce con lo stesso errore della migrazione, non con
  "duplicate column"; con la migrazione corretta le colonne si aggiungono, la riga di `siti` c'è e `PRAGMA
  foreign_key_check` è vuoto.
- **P4-08, non fatta** (due servizi veri sulla stessa cartella dati e porta): il divieto di lanciare `gradiens avvia` vale
  anche per `python -m gradiens avvia`, quindi non ho avviato nessun processo del servizio (il sistema di permessi ha
  bloccato il tentativo e non l'ho ripetuto in altro modo). Per S-11 restano: P16 (fase 2, due `crea_app` in processo),
  il log vero L-04, il sorgente di uvicorn 0.54.0 letto (`server.py:115-118` e `:57-68`: la startup del lifespan, cioè bot e
  programmatore, avviene PRIMA della creazione del socket; se la porta è occupata `sys.exit(STARTUP_FAILURE)`, e
  `config.py:81` dice `STARTUP_FAILURE = 3`; `server.py:281-311`: `shutdown` chiude per prima cosa i socket di ascolto e
  lancia il `shutdown` del lifespan solo alla fine) e P4-08b.
- **P4-08b** (`p4_08b_leggi_stato_muto.py`, un server di prova su 127.0.0.1 che accetta la connessione e non risponde mai;
  non è un servizio di Gradiens): `cli.leggi_stato` restituisce `None` dopo 2,0 s e `pannello.descrivi(None)` dà "Gradiens è
  spento". Un servizio con il ciclo di eventi fermo più di 2 s sembra quindi spento sia alla CLI sia al pannello.
- **P4-10** (`p4_10_aggiorna.py`, `aggiornamento.aggiorna` vero con repository git temporanei, `uv` finto, `_avvia_staccato`
  sostituita da una riga di registro, e un "vecchio servizio" simulato: un piccolo server di prova su socket che imita
  `/api/stato` e `/api/spegni`; nessun processo di Gradiens). 1) Il servizio non ripartirebbe dopo l'aggiornamento: `aggiorna`
  aspetta 20,1 s e restituisce "Gradiens è aggiornato (1 modifiche nuove)." senza errore né avviso. 2) Il vecchio processo
  chiude la porta a +0,1 s ed esce a +4,6 s (le durate osservate nei log veri): `uv sync` parte a +0,1 s con il vecchio
  processo ancora vivo (verificato con `Popen.poll()`).
- **P4-12** (`p4_12_cache_robots.py`, `fonti.siti.raccogli` vero con `httpx.MockTransport`; un riavvio = azzerare `_robots`,
  `_cache`, `_prossima`). 1) Feed con ETag e 11 voci: 1ª esecuzione richieste `[robots.txt, feed 200]`, 1.570 byte; 2ª
  nello stesso processo (robots.txt scaduto dopo un'ora) `[robots.txt, feed 304]`, 0 byte; 3ª dopo un riavvio `[robots.txt,
  feed 200]`, 1.570 byte: il riavvio costa solo i byte, non richieste. 2) robots.txt che risponde 503 due volte (guasto
  passeggero) e poi torna normale, due esecuzioni a 20 minuti: **senza riavvio** la 1ª esecuzione dà "nessuna strategia
  funzionante" con guasto, la 2ª **non fa nessuna richiesta** (il divieto è in memoria per 60 minuti) e dà lo stesso esito con
  guasto; **con un riavvio in mezzo** la 2ª dà "ok", senza guasto.
- **P4-11** (`p4_11_programmatore.py`, `Programmatore` ed `Esecutore` veri, fonti e provider finti, orologio sotto controllo).
  A) esecuzione manuale in corso alle 07:00: il programmatore scrive solo "Esecuzione programmata saltata: un'altra è già in
  corso" (livello INFO) e, finita la manuale, non riprova; nel database 1 sola esecuzione, `dashboard`. B) `/pausa` alle
  06:59:50 e `/riprendi` alle 07:00:50: nessuna esecuzione quel giorno. C) modulo "Esecuzione" delle Impostazioni caricato prima
  di `/pausa` e salvato dopo (con la soglia cambiata, casella "Programmazione automatica" come l'aveva mostrata): la pausa
  messa da Telegram risulta tolta, senza avviso. D) accensione alle 08:00 senza rete (attesa massima ridotta a 1 s): esecuzione
  `fallita`, "Nessuna connessione a internet: controlla la rete e riprova."; un riavvio del servizio alle 08:10 con la rete
  tornata **non fa nessun recupero** (`avviate_dal` conta l'esecuzione fallita); con una correzione di prova (il recupero non
  conta le esecuzioni fallite per mancanza di rete) il recupero parte e si completa.
- **D-03** (metriche delle esecuzioni 3, 9 e 10 in sola lettura, campo `dettaglio` degli `stati` dei siti): redhotcyber ha
  usato "sitemap" con il guasto "feed fermo" nell'esec. 3 (finestra di 1 giorno), "feed, sitemap" nelle esec. 9 e 10 (23 e 22
  articoli trovati, 21 e 2 nuovi): **nelle due esecuzioni vere recenti la cascata non si è fermata al feed**; l'arresto
  al feed di redhotcyber con 3 giorni è la misura offline della 6a (12 novembre). freecodecamp: "sitemap" con "feed fermo"
  (es. 9), "feed" (es. 10). `finestra_giorni` nel codice vale 7 di base (`dati/modelli.py:29`), 3 nel database dell'utente.
- **P4-09** (`p4_09_bot_doppio.py`, `BotGradiens` vero con `Application` finta, nessuna rete: `initialize` attende 50 ms,
  `start_polling` 10 ms; si conta quante `Application` restano in polling dopo **un solo** `ferma()`). Oggi: `avvia()` +
  `_riprova()` insieme: 2 create, **1 ancora in polling** dopo `ferma()`; `avvia()` + `avvia()`: 2 create, 1 ancora in polling
  (quella a cui `self._app` non punta più). Con un `asyncio.Lock` attorno ad `avvia` e `_riprova` (correzione di prova): 1
  creata e 0 in polling; due `avvia()` in fila: 2 create una dopo l'altra, 0 in polling.
- **L-07** (stesso log di L-01, conteggio di righe): "nuovo tentativo" 0, "Elaborazione fallita" 0, "Pre-filtro fallito" 0,
  "Rigenerazione del profilo" 0, "Passo degli argomenti" 0, "Proposta non generata" 0, "Copia giornaliera" 0, "Controllo
  della programmazione" 0, "Messaggio Telegram dell'esecuzione … non inviato" 0; gli unici avvisi dell'esecutore sono 2
  "Raccolta … fallita" (8 novembre, risoluzione dei nomi). Comandi Telegram nel log: `/help` 7, `/stato` 1, un `cuore:`;
  **mai** `/ultima`, `/pausa`, `/riprendi`, `/aggiorna`.
- **P4-08c** (`p4_08c_eccezioni.py`, socket di prova su 127.0.0.1): `httpx.get(..., timeout=2)` verso una porta chiusa solleva
  `ConnectError`, verso un server che accetta e non risponde solleva `ReadTimeout`: le due situazioni si possono distinguere.
- **P4-13** (`p4_13_sponsorizzati_per_tipo.py`, `Esecutore` vero e una sottoclasse con la correzione proposta per S-01; un blocco
  con 1 paper, 1 video e 1 articolo di un sito, l'LLM finto li segnala tutti e tre come sponsorizzati e nessuno come
  pertinente). **Oggi**: nessuna notizia salvata, `escluse` 1 per arXiv, 1 per YouTube, 1 per i siti, 3 indirizzi nel
  registro delle viste, 0 valutazioni. **Corretto** (l'esclusione vale solo per i `sito`; gli altri segnalati passano alla
  valutazione): salvate le notizie `arxiv` e `video`, `escluse` 0 per arXiv e YouTube e 1 per i siti, 3 indirizzi nel
  registro, 2 valutazioni. La modifica sono 4 righe dentro `filtra`.
- **P4-14** (`p4_14_bind.py`, socket su 127.0.0.1): su Linux un secondo `bind` sulla porta di un socket in ascolto è
  rifiutato (`OSError`, errno 98) sia senza sia con `SO_REUSEADDR`. Su Windows non provato: lì `SO_REUSEADDR` permette il
  doppio `bind`, quindi un `bind` anticipato non deve impostarlo (da verificare con un test che gira nella CI Windows).
- **P4-15** (progetto di prova in `scratchpad/fase4/uvprova/`, senza dipendenze, `uv sync --offline`): un `uv sync` lanciato
  dentro `uv run` sullo stesso ambiente non si blocca (esce con codice 0 in 0,0 s). Non prova niente su Windows.
- **P4-16** (import di `gradiens.app.pannello` con il Python del progetto): i moduli compilati caricati dal pannello vengono
  da un solo pacchetto, `pydantic_core`; gli altri pacchetti importati sono `httpx`, `pydantic`, `pydantic_settings` (solo
  Python). Su Windows il file corrispondente sarebbe un `.pyd` in uso finché il pannello è aperto.
- **L-08** (lettura del sorgente di python-telegram-bot 22.8 in `.venv`, `telegram/ext/_utils/networkloop.py:150-200` e
  `_updater.py:314-418`): il polling usa `max_retries=-1` e, per un `TelegramError` che non sia `InvalidToken`, `RetryAfter`
  o `TimedOut`, chiama `on_err_cb`, aspetta (da 1 a 30 s) e **riprova**: un `Conflict` non ferma il polling. Allo `stop()` l'`Updater`
  chiama `get_updates` un'ultima volta e, se fallisce, scrive l'errore nel log e prosegue.
- **P4-05b** (`p4_05b_redirect_legittimo.py`, `httpx.MockTransport`): la correzione di prova di S-32 segue un redirect
  legittimo di robots.txt (`https://e.org/robots.txt` verso `https://www.e.org/robots.txt`) e applica le sue regole
  (`/pubblico` consentito, `/privato/x` vietato).
