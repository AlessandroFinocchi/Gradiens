# 6a — Algoritmo di ricerca delle notizie sui siti

Data: 12-13 novembre 2026. Stato: **bozza da discutere con l'utente**.

> **Decisioni dell'utente (13 novembre 2026)**, numeri 12 e 15-22 di [decisioni.md](decisioni.md): **niente misura della generalizzazione** (6a-1 e sezione 3 non pianificate: gli effetti restano stime, la verifica si fa con i test su file salvati e sulle esecuzioni vere); `lastmod` resta data certa (di 6a-2 resta solo il rifiuto delle date future); raccolta incrementale accettata ([ADR 0011](../adr/0011-raccolta-incrementale-dei-siti.md)); voci di altri domini fuori salvo siti collegati; LLM nel profilo su richiesta e per ultimo; niente regola sui titoli per le offerte; si tiene il profilo vecchio se il sito non risponde; traduzioni escluse per default; la quota liberata dalla 6b va ai siti senza tetto di notizie per sito. Il testo sotto è la bozza su cui sono state prese le decisioni e non è stato riscritto: l'ordine della sezione 5 va letto senza il banco di misura.

Proposta della fase 6 descritta in [README.md](README.md). Obiettivo dell'utente: trovare bene le notizie
anche su siti nuovi simili ai 13 di esempio, e spendere meno (pagine, byte, token). Il funzionamento di
oggi è descritto in [mappa-moduli.md](../architettura/mappa-moduli.md), sezione C2: qui si rimanda a quella
sezione e non la si ripete. I riferimenti al codice sono relativi a `src/gradiens/`, al commit `3868260`.

Le cifre vengono da tre fonti, sempre indicate:
- **passaggio diagnostico** del 12 novembre 2026 sui 13 siti veri (decisione 7 di [decisioni.md](decisioni.md)),
  descritto nella sezione 2a. I suoi dati grezzi sono andati persi il 13 novembre: questo documento ne è
  l'unica traccia;
- **database** `.gradiens/gradiens.db`, letto in sola lettura (profili, metriche delle esecuzioni 9 e 10,
  notizie, registro delle notizie viste);
- **lettura del codice**.

Dove una cifra è una stima o un'affermazione è un'ipotesi, il testo lo dice e spiega il ragionamento.

---

## Riepilogo

### Cosa si è scoperto

1. **La cascata perde articoli soprattutto per due difetti precisi.**
   - ACN: il feed ufficiale **è linkato** dalla pagina della sezione, ma l'analisi lo scarta. Per una sezione
     un feed vale solo se almeno metà delle voci sta nel percorso o è linkata dalla pagina
     (`fonti/siti/strategie/feed.py:69-71`); qui sono 0 e 15 su 50. In 7 giorni `raccogli` trova 19
     candidate (2 non sono articoli) contro 43 articoli nell'unione delle strategie.
   - redhotcyber: il feed `/feed/gn` è **in ritardo di un giorno e mezzo**. La sua ultima voce è dell'11/11 alle
     06:35 UTC e l'API WordPress ha 19 articoli più recenti. Il feed però "copre" la finestra perché ha voci
     vecchie, e la cascata si ferma lì (`fonti/siti/__init__.py:107`). Con la finestra di 3 giorni usata oggi
     dall'app, rigiocata offline sulle stesse risposte, trova 9 articoli su 30 (unione di tutte le strategie).
2. **Una data presa solo da `lastmod` è sbagliata in circa 1 caso su 15.** Si è potuta controllare ogni voce a
   redhotcyber e gamesbeat (con l'API WordPress), a freecodecamp e a chipsandcheese (con feed e pagine). Su 102
   candidate datate solo da `lastmod`, 7 sono articoli vecchi (dal 2021 all'agosto 2026) modificati di recente,
   che oggi diventano notizie nuove. A freecodecamp lo sono tutte e 3 le voci che la sitemap aggiunge al feed.
   Quando l'articolo non è stato modificato, `lastmod` coincide con la pubblicazione entro 10 minuti in 35
   confronti su 35.
3. **Molte letture non portano articoli.** Una raccolta di 7 giorni sui 13 siti costa 147 richieste (18 per
   robots.txt) e 25,5 MB.
   - hwupgrade: 36 delle 40 pagine servono a cercare la data di link della home senza data. Solo 8 sono
     notizie della forma dei feed; 18 sono schede di download, 4 guide, 2 gallerie, 4 articoli lunghi. 24 pagine
     risultano fuori dalla finestra.
   - nature: 18 delle 19 letture di sitemap (circa 7,5 MB) non danno candidate; tutte le 45 vengono dalla news
     sitemap.
   - thehackernews: 8 letture di sitemap su 9 senza candidate.
4. **hwupgrade non si può coprire con le regole di oggi.** I feed coprono circa 10 ore (50 voci dalle 08:11
   alle 18:17 UTC del 12/11), la home elenca 115 link senza data, non c'è una sitemap XML. Il sito pubblica
   circa 50-65 articoli al giorno (stima grossolana, dagli id degli indirizzi e dal feed); la raccolta di 7
   giorni ne trova 76, di cui 15 con data incerta. L'id negli indirizzi **non** basta a ordinare per data: nel
   database, su 28 notizie di hwupgrade, 39 coppie su 378 hanno id e data in ordine opposto.
5. **I segnali che mancano sono soprattutto deterministici.** Nelle 71 pagine di elenco registrate non c'era
   nessun JSON-LD `ItemList` o `Article` e nessun `__NEXT_DATA__`. Servirebbero invece segnali che oggi non si
   usano: l'intestazione `Link: rel="https://api.w.org/"` (WordPress anche su ilsoftware), la forma degli
   indirizzi delle notizie ricavata dai feed (per scegliere a quali link dedicare le pagine), le news sitemap,
   il registro delle notizie viste. Un LLM alla creazione del profilo servirebbe solo nei casi residui, con un
   input stimato di 160-6.400 token (albero dei link ridotto) contro 9.000-118.000 dell'HTML intero (stime:
   caratteri divisi per 2,35, il rapporto misurato dalla 6b su JSON in italiano).

### Raccordo con il consumo di token (6b)

La ricerca sui siti oggi non usa token. Ma ogni articolo in più che trova costa quota dopo: secondo il modello
della 6b (`06b-consumo-di-token.md`, sezione 2; cifre arrotondate, documento in aggiornamento) una notizia
nuova di sito costa circa **2.600 token**. Di questi, circa 220 vanno al pre-filtro; il resto sono valutazione
(per il 42% che lo supera) e argomenti. Le proposte che trovano più articoli (6a-3, 6a-4, 6a-5, 6a-6, 6a-9)
aggiungerebbero, insieme, circa 60-110 mila token per esecuzione (stima per scheda nella sezione 4). È una
parte del risparmio di circa 226 mila token per esecuzione che la 6b attribuisce a 6b-2. Le proposte che
tolgono candidate inutili (6a-2, 6a-13) ne risparmiano poche migliaia. Non ci sono conflitti con la 6b, ma la
quota liberata va divisa: è la domanda 10.

### Cosa si raccomanda

Prima un banco di misura minimo con le risposte registrate in `.gradiens/` (la registrazione del 12/11 è
andata persa perché stava in una cartella temporanea), e la protezione del profilo buono. Poi le correzioni
piccole: feed di sezione, news sitemap sempre, `lastmod` da confermare, sitemap mirate. Poi il registro delle
viste dentro la fonte, l'HTML più preciso e la raccolta incrementale. L'LLM alla creazione del profilo per
ultimo, su richiesta e con un tetto. L'interfaccia comune delle strategie resta com'è
(`fonti/siti/strategie/__init__.py:1-15`); dove serve un comportamento nuovo si aggiunge un modulo o un
attributo facoltativo.

### Tabella delle proposte

| Codice | Problema in breve | Raccomandazione | Effetto atteso (stime salvo dove detto) | Sforzo | Rischio |
|---|---|---|---|---|---|
| 6a-1 | Nessun modo di misurare una modifica senza nuove richieste | Banco di misura: registrazione larga in `.gradiens/banco/`, rigioco offline, confronto | Prerequisito; un confronto costa 0 richieste se la variante resta nell'insieme registrato | M | basso |
| 6a-2 | `lastmod` vale come data certa; date future accettate | `lastmod` confermato da URL, news, feed, API o pagina; date future rifiutate | -7 falsi nuovi a settimana sui siti misurati (circa -18 mila token a settimana) | S + M | medio (contratto) |
| 6a-3 | La fonte non conosce il registro delle viste | Parametro facoltativo `viste`, tetto e date solo sulle non viste, registro degli scartati per data | Pagine dei visti risparmiate (6 su 36 a hwupgrade il 12/11); più notizie nuove oltre il tetto | M | medio (contratto) |
| 6a-4 | Feed di una sezione scartato se le voci sono fuori percorso (ACN) | Accettare il feed specifico linkato dalla pagina della sezione | ACN: da 17 a 38 articoli in 7 giorni (+21), 5 trovati solo dall'HTML persi; -9 richieste; circa +8 mila token al giorno | S | basso |
| 6a-5 | Un feed in ritardo "copre" e ferma la cascata (redhotcyber) | Opzione B: modulo nuovo che legge sempre news sitemap o API | redhotcyber, 3 giorni: da 9 a circa 21-28 articoli; +1 richiesta; circa +13-18 mila token al giorno | S-M | basso |
| 6a-6 | Ogni esecuzione rifà tutta la finestra; tetti fissi | Raccolta incrementale con "coperto fino a" salvato a fine esecuzione; piano e tetti adattivi | Richieste da circa 130 (base a 3 giorni, dedotta) a 40-60 (stima grossolana); hwupgrade +40-80 mila token per esecuzione | L | medio (schema) |
| 6a-7 | Sitemap lette alla cieca (indici, figlie vecchie) | Figlie per numero, news sitemap prima, niente indici enormi senza date | Byte: nature circa -7,5 MB; richieste quasi invariate dove il tetto è pieno; thehackernews fino a -8 | S-M | basso |
| 6a-8 | Piattaforme riconosciute male, API WordPress senza pagine | Più segnali (intestazioni, `api.w.org`); API paginata; strategie nuove solo se misurate | Generalizzazione ai WordPress con CDN; resto da misurare | S + M | basso |
| 6a-9 | HTML: non articoli, pagine per la data spese male | `non_articolo` più severo; forma degli indirizzi dei feed come priorità per le pagine | Meno non articoli; le pagine per la data vanno prima alle notizie | M | medio |
| 6a-10 | Cache solo in memoria | Cache su disco dei feed e delle sitemap con richieste condizionali | Circa -3,8 MB alla prima esecuzione dopo un riavvio; richieste invariate | S-M | basso |
| 6a-11 | Profilo che diventa vuoto; niente anteprima, differenze, sezioni | Protezione del profilo subito; differenze, anteprima e sezioni dopo | Fino a 3 esecuzioni senza raccolta evitate; `WEB-02`, `WEB-03`, `WEB-25` | S + M | basso |
| 6a-12 | Euristiche che falliscono senza aiuto | LLM solo alla creazione del profilo, su richiesta, con albero dei link ridotto | 2-9 mila token per sito, una volta | M | medio |
| 6a-13 | Candidate inutili al pre-filtro | Voci di terzi domini fuori; regola facoltativa sui titoli | Poche migliaia di token per esecuzione | S-M | medio |

---

## 1. Com'è oggi

Il dettaglio è in mappa-moduli.md, sezioni C2(a)-(i). In sintesi, con i punti che contano per le proposte:

- **Profilo del sito** (C2 a): creato una volta da `analizza` (`fonti/siti/__init__.py:46-66`), senza LLM, con
  al massimo 40 pagine. Contiene feed, sitemap, sezioni, esclusioni, piattaforma, strategie e i tetti di 40
  pagine e 100 articoli (`fonti/siti/profilo.py:33-34`). Nessuno dei 13 profili ha modifiche dell'utente.
- **Cascata** (C2 b): feed → sitemap → API WordPress → HTML nell'ordine di `STRATEGIE`
  (`fonti/siti/strategie/__init__.py:15`). Si combinano le strategie eseguite, ma la cascata si ferma alla
  prima che "copre" la finestra (`fonti/siti/__init__.py:107`). "Copre" vuol dire cose diverse:
  - feed: **ogni** feed del profilo ha almeno una voce più vecchia di `dal` (`strategie/feed.py:104-105`,
    `all`);
  - sitemap: almeno una voce più vecchia di `dal`, oppure **una figlia qualunque** di un indice con un
    `lastmod` vecchio, anche se quella figlia non viene letta (`strategie/sitemap.py:101`, `:110-111`);
  - API WordPress: meno di 100 voci (`strategie/wordpress.py:55`).

  Un feed che copre senza candidate non ferma la cascata (condizione della riga 107); le righe 98-102
  segnalano il feed fermo quando una strategia successiva trova date certe.
- **Date** (C2 c): feed (`published`, poi `updated`), sitemap (news, poi data nell'indirizzo, poi `lastmod`),
  `date_gmt` dell'API, data vicino al link nell'HTML. Le date incerte si cercano dopo il taglio a 100 articoli,
  prima nell'indirizzo e poi leggendo la pagina (`fonti/siti/__init__.py:142-156`).
- **Tetti** (C2 d): un solo contatore di pagine per raccolta, condiviso da strategie e date incerte;
  robots.txt fuori dal conto; **ogni passaggio di redirect consuma una lettura** (`fonti/siti/rete.py:121-126`).
- **Rete** (C2 e): robots.txt, pause per host, cache e regole solo in memoria (`fonti/siti/rete.py:30-33`).
- **Rigenerazione** (C2 f): dopo 3 guasti di fila, nuova analisi completa. Se il sito non risponde, il nuovo
  profilo è senza strategie e il vecchio va in `profilo_precedente` (`dati/siti.py:58`). Il profilo vuoto è a
  sua volta un guasto (`fonti/siti/__init__.py:82-84`), quindi dopo altre 3 esecuzioni si rianalizza. Il
  profilo buono si perde del tutto solo se il sito resta irraggiungibile per 6 esecuzioni. La rete del PC
  assente all'avvio è già gestita (`esecuzione/esecutore.py:169-177`). Il danno tipico è un ritardo: fino a 3
  esecuzioni senza raccolta dopo che il sito è tornato.
- **LLM** (C2 h): mai nella scoperta né nell'estrazione. I siti pesano sull'LLM solo tramite le candidate
  mandate al pre-filtro (titolo e sommario fino a 1.500 caratteri, `esecuzione/prompt.py:12`, `:47-49`) e
  tramite le valutazioni. La ricerca sui siti oggi costa **0 token**.

**Cosa manca rispetto al PRD** (verificato nel codice, vedi C2 a, f):
- `WEB-02`: nessuna anteprima degli articoli all'aggiunta (`dashboard/rotte_impostazioni.py:168-176`).
- `WEB-03`: le sezioni non si vedono e non si modificano (`dashboard/templates/impostazioni/siti.html:36-41`).
- `WEB-04`: l'LLM che riconosce l'elenco quando le euristiche falliscono non esiste (resta il commento
  `shortcut` di `fonti/siti/__init__.py:60`).
- `WEB-25`: `profilo_precedente` si scrive (`dati/siti.py:58`) ma nessuno lo mostra.
- `WEB-15`: l'ordine delle fonti della data è diverso da quello scritto (C2 c, ultimo paragrafo).

---

## 2. I 13 siti per tipo

### 2a. Il passaggio diagnostico

**Quando**: 12 novembre 2026, dalle 20:48:36 alle 20:58:11 ora italiana. La prova su evilsocket.net è durata
dalle 20:48:36 alle 20:48:39, il passaggio completo dalle 20:48:57 alle 20:53:34, l'integrazione del campione
di date dalle 20:57:56 alle 20:58:11. Le richieste occupano quindi circa 5 minuti.

**Come** (script fuori dal progetto, nella cartella temporanea della sessione di analisi):
- un trasporto httpx sotto il client dell'app **conta ogni richiesta vera** e **registra ogni risposta su
  disco**. Rifiuta, senza farla, ogni richiesta oltre 60 per sito o 600 in totale, e ogni richiesta a host
  diversi dal dominio del sito e da quelli già nel profilo. Una URL già registrata non si richiede più: i passi
  successivi la rileggono dal disco, senza rete e senza pausa;
- tutte le richieste passano da `Navigatore` (robots.txt, pause per host, redirect controllati) e dalle
  strategie dell'app; il trasporto aggiunge una pausa di cortesia di almeno 1 secondo per host;
- profili letti dal database in sola lettura; finestra di 7 giorni (`dal` = ora del passaggio meno 7 giorni);
- nessuna chiamata LLM, nessuna scrittura nel progetto.

Le ore delle date degli articoli e quelle salvate nel database sono in UTC, come nel codice
(`fonti/siti/date.py:1`, `dati/notizie.py:15-17`); le ore del passaggio sono ora italiana (UTC+1).

**Passi per sito**, in quest'ordine per avere almeno (1) e (2) anche sui siti grandi. Ogni passo parte "come
in un processo nuovo", con robots.txt e cache dell'app azzerati:
1. ogni strategia del profilo **da sola**: feed, poi sitemap, poi API WordPress (anche per ilsoftware, per
   vedere robots.txt);
2. `raccogli` **così com'è**, con le strategie che il profilo prevede;
3. HTML da solo (pagina indicata e sezioni del profilo), anche dove il profilo non lo usa, con un budget;
4. ACN: il feed ufficiale indicato dalla verifica del 2/11 (stesso host del sito);
5. un campione di pagine di articoli per confrontare le date (fino a 5 per sito, se restava margine).

Poi, **offline** (zero richieste):
- analisi di feed, sitemap, pagine e robots.txt registrati;
- unione e sovrapposizioni, confronto delle date;
- la stessa raccolta **rigiocata con la finestra di 3 giorni** usata oggi dall'app
  (`finestra_giorni = 3` nel database).

**Integrazione**: lo script sceglieva il campione di date partendo dalle voci delle news sitemap, che hanno già
una data affidabile. Corretto il criterio, si sono lette 17 pagine di articoli datati solo da `lastmod`
(ilsoftware 5, redhotcyber 5, gamesbeat 5, freecodecamp 2). Nessuna richiesta è stata ripetuta. In tutto: 4
richieste nella prova, 260 nel passaggio completo, 17 nell'integrazione.

**Richieste vere** (contate dal trasporto):

| Sito | Richieste | Note |
|---|---|---|
| nature.com | 60 | tetto del sito raggiunto: 8 pagine del campione non lette, 2 pagine HTML oltre il budget del passo |
| hwupgrade.it | 48 | |
| gamesbeat.com | 42 | |
| ilsoftware.it | 30 | API WordPress: 0 richieste, vietata da robots.txt |
| redhotcyber.com | 27 | |
| thehackernews.com | 20 | |
| acn.gov.it | 17 | |
| freecodecamp.org | 12 | |
| 3blue1brown.com | 8 | |
| chipsandcheese.com | 6 | |
| evilsocket.net | 4 | la prova |
| projectdiscovery.io | 4 | |
| e3rehab.com | 3 | |
| **Totale** | **281** | 50,1 MB scaricati; 10 richieste rifiutate dai tetti, 0 per host non ammesso, 0 errori di rete, nessun 5xx |

**Limiti**:
- una sola sera: frequenze di pubblicazione e ritardi dei feed possono cambiare da un giorno all'altro;
- le intestazioni `Set-Cookie` non sono state conservate, quindi il client non ha tenuto cookie. Su nature ogni
  pagina HTML è passata da 4 richieste: un 303 verso `idp.nature.com`, due 302, poi la pagina con
  `?error=cookies_not_supported`. Sono 4 letture del tetto per pagina (`rete.py:121-126`): da qui le 20 letture
  HTML di nature. Il client dell'app conserva i cookie per tutta l'esecuzione (httpx lo fa per default), quindi
  nell'app il costo potrebbe essere minore: **non verificato**;
- nature: nessuna data dalla pagina (tetto del sito); HTML da solo parziale (budget del passo);
- `analizza` non è stata rieseguita: i profili sono quelli creati fra il 6 e il 10 novembre. Le verifiche
  sull'analisi (feed di ACN, piattaforma di ilsoftware) sono state fatte offline sulle pagine registrate;
- la "verità" è l'unione delle strategie più i controlli puntuali, quindi è circolare (vedi 3b);
- il registro delle viste è fermo all'esecuzione 10, finita l'11/11 alle 06:06 UTC (07:06 ora italiana): la
  quota di "già viste" è più bassa di quella di un'esecuzione giornaliera.

**I dati grezzi non esistono più.** Script, risposte registrate (circa 50 MB) e JSON dei risultati stavano
nella cartella temporanea della sessione di analisi. Sono andati persi con il riavvio del PC del 13 novembre
2026. **Questo documento è l'unica traccia rimasta della misura**: le tabelle di questa sezione e della 2b
riportano tutte le cifre di sintesi. Le cifre sono state controllate sui file grezzi il 12 novembre; dopo il
riavvio si sono potuti ricontrollare solo codice, database (in sola lettura) e test. La lezione vale per lo
strumento di misura (6a-1): le registrazioni devono stare in `.gradiens/`, che sopravvive ai riavvii.

### 2b. I 13 siti

Finestra di 7 giorni. Definizioni usate nelle tabelle:
- "Da sola": candidate con data certa trovate da una strategia senza le altre (indirizzi distinti);
- "Unione": indirizzi distinti con data certa trovati da almeno una strategia, più le date incerte dell'HTML
  risolte con pagine già lette. Contiene anche voci da `lastmod` non confermate, traduzioni e date future;
- le richieste di `raccogli` comprendono quelle a robots.txt.

| Sito | Tipo (etichette) | Profilo | Feed da solo | Sitemap da sola | API WP | HTML da solo | `raccogli`: candidate (incerte) · strategie · richieste · MB | Unione · non trovate da `raccogli` |
|---|---|---|---|---|---|---|---|---|
| hwupgrade.it | feed parziale ad alto volume; elenchi senza data; senza sitemap XML; feed di gruppo | feed, html | 50, arco 10 h, non copre | – (robots: solo `sitemap1.txt`) | – | 1 + 114 incerte | 76 (15) · feed, html · 43 · 5,2 | non misurabile (stima: 350-450 pubblicati in 7 giorni) |
| nature.com | feed parziale; news sitemap; paywall; cookie; indici enormi | feed, sitemap, html | 75, arco 3 giorni, date al giorno | 45 (tutte news) | – | 79 + 5 incerte (parziale) | 82 (5) · feed, sitemap, html · 42 · 8,7; tetto 40 raggiunto | 82 · 5 (oltre il tetto) |
| thehackernews.com | feed parziale su altro dominio (feedburner); news sitemap; Blogger | feed, sitemap, html | 50, arco 3,3 giorni | 64 (news) | – | 17 + 24 incerte | 64 · feed, sitemap · 12 · 0,6 | 65 · 1 (data al giorno al bordo) |
| ilsoftware.it | WordPress con API vietata; news sitemap; elenchi senza data | feed, sitemap, html | 10, arco 9 h | 90 (38 news + 52 `lastmod`) | vietata (0 richieste) | 3 + 450 incerte | 90 · feed, sitemap · 9 · 1,9 | 93 · 3 (una con data futura) |
| redhotcyber.com | WordPress con API; feed in ritardo; news sitemap; versioni in inglese | feed, sitemap, wordpress, html | 10, ultima voce 11/11 06:35 UTC | 51 (21 news + 30 `lastmod`, 3 falsi nuovi) | 56 (`X-WP-Total` 65) | 15 + 35 incerte; fra le candidate 5 PDF e un link `cdn-cgi` datato 2027 | 51 · feed, sitemap · 8 · 2,1 | 60 · 9 (5 traduzioni `/en/`, 3 in italiano solo dall'API, il link `cdn-cgi`) |
| gamesbeat.com | WordPress con API; feed corto; sitemap con `lastmod` | feed, sitemap, wordpress, html | 10, arco 6,5 h | 63 (`lastmod`, 1 falso nuovo) | 62 (`X-WP-Total` 71) | 70 distinte (+8 al bordo) | 63 · feed, sitemap · 6 · 0,8 | 71 · 8 (date al giorno prima di `dal`) |
| acn.gov.it/portale/csirt-italia | sezione; portale istituzionale; feed ufficiale non nel profilo; elenchi con date | html | – (feed ufficiale: 38, non ordinato) | – | – | 16 + 3 incerte | 19 (2) · html · 11 · 1,2 | 43 · 26 |
| freecodecamp.org/news | sezione; feed completo; sitemap enorme con `lastmod` | feed, sitemap, html | 4, copre | 7 (3 falsi nuovi) | – | 4 | 4 · feed · 2 · 0,3 | 7 · 3 (tutti falsi nuovi) |
| chipsandcheese.com | Substack con dominio proprio; home senza elenco (pagina di iscrizione); feed a contenuto intero | feed, sitemap | 2, copre (1,6 MB) | 2 | – | 0 | 2 · feed · 2 · 1,6 | 2 · 0 |
| projectdiscovery.io/research | sezione; Next.js reso dal server; solo HTML | html | – | – | – | 0 (2 incerte, vecchie) | 0 · html · 4 · 0,8 | 0 |
| e3rehab.com/articles | sezione; WordPress; poco frequente | feed, html | 0, copre (1,3 MB) | – | – | 0 | 0 · feed, html · 3 · 1,4 | 0 |
| 3blue1brown.com | feed su altro dominio (Substack); contenuti in JavaScript | feed | 0, copre | – | – | 0 | 0 · feed · 2 · 0,1 | 0 |
| evilsocket.net | blog personale Hexo; poco frequente; sitemap rigenerata | feed, sitemap, html | 0, copre (0,5 MB) | 0 (`lastmod` ignorato) | – | 0 | 0 · feed, sitemap · 3 · 0,7 | 0 |
| **Totale** | | | | | | | **451 candidate · 147 richieste · 25,5 MB** | |

**Ogni strategia da sola** (7 giorni). "Certe" sono le candidate con data certa; fra parentesi gli indirizzi
distinti, quando più feed o sitemap ripetono le stesse voci. "Pagine" sono le letture del `Navigatore`,
robots.txt escluso. "Copre" vuol dire che la strategia ha visto voci più vecchie della finestra.

| Sito | Feed | Sitemap | API WordPress | HTML | Altro |
|---|---|---|---|---|---|
| hwupgrade.it | 70 certe (50) · non copre · 3 pagine | – | – | 1 certa + 114 incerte · copre · 1 pagina | – |
| nature.com | 75 · non copre · 1 | 45 · non copre · 19 | – | 79 + 5 incerte · copre · 32 (budget del passo) | – |
| thehackernews.com | 50 · non copre · 1 | 64 · copre · 9 | – | 17 + 24 incerte · copre · 3 | – |
| ilsoftware.it | 10 · non copre · 1 | 166 (90) · copre · 7 | vietata da robots.txt · 0 | 3 + 450 incerte · non copre · 12 | – |
| redhotcyber.com | 10 · non copre · 1 | 74 (51) · copre · 6 | 56 · copre · 1 | 15 + 35 incerte · copre · 9 | – |
| gamesbeat.com | 10 · non copre · 1 | 87 (63) · copre · 4 | 62 · copre · 1 | 209 (70) + 1 incerta · copre · 25 | – |
| acn.gov.it | – | – | – | 16 + 3 incerte · copre · 5 | feed ufficiale: 38 · copre · 1 |
| freecodecamp.org | 4 · copre · 1 | 7 · copre · 2 | – | 4 · copre · 1 | – |
| chipsandcheese.com | 2 · copre · 1 | 2 · copre · 1 | – | 0 · non copre · 1 | – |
| projectdiscovery.io | – | – | – | 0 + 2 incerte · copre · 2 | – |
| e3rehab.com | 0 · copre · 1 | – | – | 0 · copre · 1 | – |
| 3blue1brown.com | 0 · copre · 1 | – | – | 0 · copre · 5 | – |
| evilsocket.net | 0 · copre · 1 | 0 · copre · 1 | – | 0 · copre · 1 | – |

**`raccogli` così com'è, per fase** (7 giorni; richieste logiche, robots.txt compreso). "Già viste" sono le
candidate che erano già nel registro delle viste, fermo all'esecuzione 10.

| Sito | Richieste | robots.txt | feed | sitemap | HTML | pagine per la data | Pagine (tetto 40) | MB | Candidate | Già viste |
|---|---|---|---|---|---|---|---|---|---|---|
| hwupgrade.it | 43 | 3 | 3 | – | 1 | 36 | 40 | 5,2 | 76 | 19 |
| nature.com | 42 | 2 | 1 | 19 | 20 | 0 | 40 | 8,7 | 82 | 14 |
| thehackernews.com | 12 | 2 | 1 | 9 | – | – | 10 | 0,6 | 64 | 28 |
| acn.gov.it | 11 | 2 | – | – | 5 | 4 | 9 | 1,2 | 19 | 5 |
| ilsoftware.it | 9 | 1 | 1 | 7 | – | – | 8 | 1,9 | 90 | 36 |
| redhotcyber.com | 8 | 1 | 1 | 6 | – | – | 7 | 2,1 | 51 | 30 |
| gamesbeat.com | 6 | 1 | 1 | 4 | – | – | 5 | 0,8 | 63 | 30 |
| projectdiscovery.io | 4 | 1 | – | – | 2 | 1 | 3 | 0,8 | 0 | 0 |
| e3rehab.com | 3 | 1 | 1 | – | 1 | – | 2 | 1,4 | 0 | 0 |
| evilsocket.net | 3 | 1 | 1 | 1 | – | – | 2 | 0,7 | 0 | 0 |
| chipsandcheese.com | 2 | 1 | 1 | – | – | – | 1 | 1,6 | 2 | 1 |
| freecodecamp.org | 2 | 1 | 1 | – | – | – | 1 | 0,3 | 4 | 2 |
| 3blue1brown.com | 2 | 1 | 1 | – | – | – | 1 | 0,1 | 0 | 0 |
| **Totale** | **147** | **18** | | | | | | **25,5** | **451** | **165** |

**Finestra di 3 giorni** (quella usata oggi dall'app), rigiocata offline sulle stesse risposte, alla stessa ora
del passaggio. "Unione" sono le candidate con data certa delle strategie da sole che cadono nei 3 giorni. "Non
trovate" sono le voci dell'unione assenti da `raccogli`: una candidata certa di `raccogli` può mancare
dall'unione, quando è una data incerta dell'HTML risolta leggendo la pagina.

| Sito | `raccogli` (di cui certe) | Unione | In comune | Non trovate | Perché |
|---|---|---|---|---|---|
| redhotcyber.com | 9 (9) | 30 | 9 | 21 | il feed in ritardo copre e ferma la cascata |
| acn.gov.it | 18 (16) | 31 | 15 | 16 | feed ufficiale non nel profilo |
| ilsoftware.it | 52 (52) | 55 | 52 | 3 | solo HTML: 1 data futura, 2 da verificare |
| freecodecamp.org | 2 (2) | 4 | 2 | 2 | entrambe falsi nuovi da `lastmod` (verificati): nessuna perdita vera |
| gamesbeat.com | 46 (46) | 48 | 46 | 2 | date al giorno dell'HTML al bordo della finestra |
| nature.com | 82 (77) | 79 | 77 | 2 | HTML oltre il tetto di 40 pagine |
| thehackernews.com | 43 (43) | 44 | 43 | 1 | data al giorno dell'HTML al bordo |
| hwupgrade.it | 72 (57) | 51 | 51 | 0 | unione non rappresentativa (home senza date) |
| chipsandcheese.com | 2 (2) | 2 | 2 | 0 | |
| e3rehab, evilsocket, 3blue1brown, projectdiscovery | 0 | 0 | 0 | 0 | |

Nel rigioco a 3 giorni si fermano al feed thehackernews, redhotcyber, freecodecamp, chipsandcheese,
3blue1brown, e3rehab ed evilsocket (questi ultimi due dopo il controllo del feed fermo). ilsoftware e gamesbeat
arrivano alla sitemap; nature, hwupgrade, ACN e projectdiscovery all'HTML. Il rigioco non ha contato le
richieste. Con i costi per fase della tabella a 7 giorni, la base a 3 giorni è di circa **130 richieste**
(deduzione, non un conteggio).

**Date: da dove vengono e quanto sono affidabili** (confronti sugli stessi indirizzi):

| Sito | Fonte della data usata | Controllo | Esito |
|---|---|---|---|
| hwupgrade | feed (`pubDate` al minuto); pagine: solo il giorno (nessun `article:published_time` né JSON-LD) | 4 pagine | stesso giorno del feed |
| nature | feed RSS 1.0 con `dc:date` al giorno (feedparser lo mette in `updated`); news sitemap | – | pagine non lette (tetto) |
| thehackernews | feed, news sitemap | 5 pagine | scarto sotto il minuto fra feed, news e pagina |
| ilsoftware | news sitemap; `lastmod` | 5 pagine `lastmod` + 5 news | `lastmod` = pubblicazione in 5 casi su 5 |
| redhotcyber | news sitemap; `lastmod` | API (tutte le 30 `lastmod`), 8 voci del feed, 5 pagine | **3 falsi nuovi** (articoli del 2021 modificati fra il 6 e l'8/11) |
| gamesbeat | `lastmod` | API (tutte le 63), 10 voci del feed, 5 pagine | **1 falso nuovo** (articolo del 19/08) |
| freecodecamp | `lastmod` | 4 voci del feed, 3 pagine | **3 falsi nuovi su 3** voci in più rispetto al feed (marzo, aprile, luglio) |
| chipsandcheese | `lastmod` | 2 voci del feed | corretti |
| ACN | testo dell'elenco (al giorno); feed non ordinato | – | – |
| evilsocket | sitemap rigenerata: lo stesso `lastmod` su almeno metà delle 696 voci | – | `lastmod` ignorato correttamente (`fonti/siti/strategie/sitemap.py:36-39`) |

L'HTML ha accettato due date **future**: ilsoftware (`2026-12-09`, una data scritta nel testo dell'elenco) e
redhotcyber (`2027-05-19`, vicino al link `cdn-cgi/l/email-protection`). `nella_finestra` non rifiuta le
date future (`fonti/siti/date.py:90-94`); solo le date numeriche hanno un controllo (`date.py:85`).

**Peso sul pre-filtro** (stima con 2,35 caratteri per token): titolo e sommario delle 451 candidate di
`raccogli` fanno circa 47.000 token di contenuto, circa 104 per candidata, senza il carico fisso delle
chiamate. Il modello della 6b (sezione 2) conta circa 220 token per notizia di sito nel pre-filtro, quota fissa
compresa. 165 candidate su 451 erano già nel registro e non arrivano al pre-filtro. 228 candidate su 451 sono
senza sommario, perché vengono da sitemap e HTML: ilsoftware 80 su 90, gamesbeat 53 su 63, redhotcyber 41 su
51, ACN 19 su 19.

### 2c. Cosa funziona e cosa no, per tipo

**Feed completo, sito poco frequente** (evilsocket, e3rehab, 3blue1brown, chipsandcheese, freecodecamp)
- Funziona: il feed copre 7 giorni e basta. Le altre strategie non aggiungono articoli veri; a freecodecamp
  aggiungono solo i 3 falsi nuovi (fatto misurato).
- Non funziona:
  - dopo un feed che copre senza candidate la cascata continua, solo per controllare che il feed non sia
    fermo (condizione della riga 107 di `fonti/siti/__init__.py`): +1 richiesta a evilsocket ed e3rehab;
  - i feed a contenuto intero pesano a ogni esecuzione, anche senza novità: chipsandcheese 1.644 KB, e3rehab
    1.306 KB, evilsocket 532 KB. Tutti e tre hanno `ETag`, e3rehab ed evilsocket anche `Last-Modified`. La
    cache in memoria (`fonti/siti/rete.py:30-33`) li riduce a un 304 finché il servizio resta acceso; dopo un
    riavvio si riscaricano interi. Quanto spesso si riavvii il servizio non è verificato.

**Feed parziale, sito ad alto volume** (hwupgrade, nature, thehackernews, ilsoftware, gamesbeat, redhotcyber)
- I feed coprono da 6,5 ore (gamesbeat, 10 voci) a 3,3 giorni (thehackernews, 50 voci): mai 7 giorni, e in tre
  casi su sei nemmeno 24 ore. Serve una seconda fonte con le date.
- Funziona dove c'è una news sitemap o una sitemap con `lastmod`: a thehackernews, ilsoftware, gamesbeat e
  redhotcyber, in 7 giorni, la sitemap copre e trova da 51 a 90 articoli con 4-9 richieste.
- Non funziona:
  - **feed in ritardo** (redhotcyber): un feed "copre" se ha una voce più vecchia di `dal`
    (`strategie/feed.py:99-105`), senza guardare se è aggiornato. Con 3 giorni la cascata si ferma al feed:
    9 articoli contro 30 nell'unione (misura offline);
  - **figlie degli indici scelte per `lastmod`** (`strategie/sitemap.py:102-104`): nei siti WordPress il
    `lastmod` di una figlia cambia anche quando si modifica un articolo vecchio. Si leggono così sitemap vecchie
    da 0,3-1,2 MB che danno 0-2 candidate: redhotcyber `rhc-post-sitemap1` e `2`, gamesbeat `post-sitemap.xml`,
    ilsoftware `post-sitemap.xml` e `focus-sitemap.xml`. A redhotcyber e gamesbeat danno proprio i 4 falsi
    nuovi. A parità di `lastmod` vince l'ordine dell'indice: ilsoftware legge `focus-sitemap.xml`, la più
    vecchia e senza candidate, e non `focus-sitemap7.xml`;
  - **indici senza date**: nature `sitemap.xml` (5,5 MB, 40.745 figlie senza `lastmod`) e thehackernews
    `sitemap.xml` (23 figlie). Si leggono le ultime 5 figlie dell'elenco (`sitemap.py:103`): a nature le sitemap
    di `nature-index` (una da 50.000 voci), a thehackernews pagine di articoli vecchi. Zero candidate in
    entrambi i casi;
  - **hwupgrade**: senza sitemap XML e con la home senza date, ogni link della home costa una pagina.
    - Il tetto di 100 articoli taglia prima della ricerca delle date, quindi entrano 49 incerte e 15 restano
      incerte (`fonti/siti/__init__.py:109-112`, `:142-156`).
    - Dei 115 link della home: 71 notizie con id, 18 schede di download, 9 articoli lunghi (`_index.html`), 17
      altri (guide, gallerie, pagine).
    - Le 36 pagine lette per la data: 8 notizie della forma dei feed (6 nella finestra, 2 fuori), 4 articoli
      lunghi (nella finestra), 18 schede di download (fuori), 4 guide e 2 gallerie (4 fuori, 2 senza data). In
      totale 10 nella finestra, 24 fuori, 2 senza data.
    - Il problema dei tetti del piano della fase 4 è confermato, ma alzarli non basta: per 7 giorni
      servirebbero centinaia di pagine (stima);
  - **feed di gruppo** (hwupgrade): la sera del 12/11, 2 voci su 50 di `rss_hwup.xml` erano di
    `fotografidigitali.it`; nel registro delle viste ce n'è 1. Entrano perché le voci dei feed non si filtrano per
    perimetro (`feed.py:83-105`, C4 della mappa). Il feed `rss_download.xml` è fermo dal gennaio 2024 ma si legge
    a ogni esecuzione.

**WordPress con API** (redhotcyber, gamesbeat; e3rehab come sezione; ilsoftware con API vietata)
- Funziona: l'API dà in una richiesta date di pubblicazione esatte, sommario e totale (`X-WP-Total`: 65 e 71
  articoli dalla sera del 4/11). È la migliore verità economica: da sola ha mostrato i 4 falsi nuovi da
  `lastmod`.
- Non funziona:
  - nella cascata non arriva mai, perché la sitemap copre prima (`fonti/siti/__init__.py:107`);
  - senza paginazione (`strategie/wordpress.py:45`), oltre 100 articoli si passa all'HTML;
  - a redhotcyber l'API restituisce anche le traduzioni `/en/post/` (5 in 7 giorni), che le sitemap lette non
    elencano.
- ilsoftware: la piattaforma non è riconosciuta perché la home non contiene né `/wp-content/` né
  `/wp-includes/` né un `meta generator` (`pagine.py:50-58`). Ha però l'intestazione
  `Link: <https://www.ilsoftware.it/wp-json/>; rel="https://api.w.org/"` e la stringa `wp-json` nella pagina
  (verificato). L'API è vietata da robots.txt (`Disallow: /wp-json/`), quindi riconoscere WordPress non cambia
  la raccolta di ilsoftware: serve per gli altri WordPress con temi o CDN che non espongono `/wp-content/`.

**Solo HTML** (ACN, projectdiscovery)
- ACN: il feed ufficiale **c'è ed è linkato** dalla pagina della sezione; `analizza` lo legge e lo scarta.
  - La regola (`strategie/feed.py:69-71`, `len(della_sezione) * 2 >= len(voci)`) chiede che almeno metà delle
    voci stia nel percorso o sia linkata dalla pagina. Qui sono 0 nel percorso e 15 linkate su 50 (30%).
  - Anche al contrario la sovrapposizione è parziale: la pagina ha 49 link da articolo (anche vecchi), 15 dei
    quali nel feed.
  - La regola serve proprio a e3rehab: il suo feed di tutto il sito è accettato perché le voci sono linkate
    dalla sezione (`tests/fonti/siti/test_siti.py:95-96`). Qui invece scarta il canale ufficiale che `WEB-20`
    cita come esempio.
  - Il feed ha 38 voci nei 7 giorni, non in ordine di data, su `/portale/w/…`. L'HTML trova 16 candidate più 3
    incerte, con 2 non articoli: un'immagine `process.png/<UUID>` e `misp-feed-index`, entrambe accettate da
    `sembra_articolo` (verificato con il codice il 13/11).
  - robots.txt risponde 403, quindi tutto è permesso (RFC 9309); le pagine rispondono 200.
- projectdiscovery: l'HTML funziona (nessun articolo nuovo, 4 richieste). La pagina è fatta con Next.js ma non
  contiene `__NEXT_DATA__` (verificato): i dati incorporati non aiuterebbero.

**Pesante in JavaScript** (chipsandcheese, 3blue1brown): la home non dà link utili (chipsandcheese: 0 link
interni), ma il feed risolve. Nessuno dei 13 siti richiede un browser.

**Con paywall o cookie** (nature): feed e sitemap rispondono puliti. Le pagine HTML passano dal giro di
redirect su `idp.nature.com` (sezione 2a). Il paywall si riconosce in `completa` (mappa C2 g), fuori dalla
ricerca.

**Sezioni proposte e link non articoli**: redhotcyber ha come sezioni sei pagine di conferenze e i partner.
Leggendole, l'HTML trova:
- 5 PDF, accettati da `sembra_articolo` (verificato con il codice il 13/11);
- `cdn-cgi/l/email-protection`, che `sembra_articolo` rifiuta. Entra comunque, perché l'HTML accetta qualunque
  link con una data vicina (`strategie/html.py:35-38`, `vicino or testuale`), anche se futura.

Oggi non fanno danni solo perché la sitemap copre prima e l'HTML non parte. Confermata l'ipotesi C2(b) della
mappa: con una sitemap che copre, le sezioni non si usano (redhotcyber, gamesbeat, ilsoftware, thehackernews).

**robots.txt in memoria**: 18 richieste per esecuzione, pochi KB. Con esecuzioni ogni 24 ore una cache di 24
ore (il massimo di RFC 9309) non ne eviterebbe quasi nessuna.

---

## 3. Come misurare la generalizzazione

Serve a giudicare ogni modifica futura con numeri, senza nuove richieste ai siti a ogni prova.

### 3a. Siti "simili ma nuovi" (da concordare)

Candidati proposti a memoria, **senza nessuna richiesta**: tutto è **da verificare** (piattaforma, feed,
protezioni). La scelta finale è dell'utente; ne bastano 15-20. Note sui candidati (ipotesi):
- 18 (cisa.gov) e 23 (netflixtechblog.com, su Medium) sono spesso protetti contro i client automatici: servono
  a misurare lo stato "accesso bloccato";
- 9, 10 e 11 pubblicano così poco che in 7 giorni probabilmente non danno articoli: misurano solo "nessun
  articolo nuovo" e il costo;
- il blog del 14 potrebbe essersi spostato su un altro indirizzo.

| # | Indirizzo da inserire | Tipo atteso (da verificare) | Simile a | Perché |
|---|---|---|---|---|
| 1 | https://www.science.org/ | rivista scientifica, paywall, possibile protezione anti-bot | nature.com | alto volume, paywall, molte sezioni |
| 2 | https://www.quantamagazine.org/ | divulgazione scientifica, WordPress | nature.com, 3blue1brown | articoli lunghi, poche uscite al giorno |
| 3 | https://arstechnica.com/ | testata tecnologica in inglese, WordPress | gamesbeat | alto volume, feed corto |
| 4 | https://www.tomshw.it/ | testata tecnologica italiana | hwupgrade | alto volume, offerte fra le notizie |
| 5 | https://www.punto-informatico.it/ | testata tecnologica italiana, WordPress | ilsoftware | news sitemap probabile, offerte |
| 6 | https://www.bleepingcomputer.com/ | cybersecurity in inglese, piattaforma propria | thehackernews | alto volume, possibile protezione |
| 7 | https://www.cybersecurity360.it/ | cybersecurity italiana, WordPress | redhotcyber | italiano, sezioni tematiche |
| 8 | https://securityaffairs.com/ | blog di cybersecurity, WordPress | redhotcyber, thehackernews | molte uscite al giorno |
| 9 | https://krebsonsecurity.com/ | blog personale, WordPress | evilsocket | poco frequente |
| 10 | https://jvns.ca/ | blog tecnico personale, Hugo | evilsocket | sito statico, `index.xml` |
| 11 | https://danluu.com/ | blog personale minimale | evilsocket, e3rehab | poche uscite, HTML semplice |
| 12 | https://www.servethehome.com/ | hardware, WordPress | chipsandcheese | articoli tecnici lunghi |
| 13 | https://lcamtuf.substack.com/ | Substack | chipsandcheese | piattaforma Substack |
| 14 | https://googleprojectzero.blogspot.com/ | Blogger, ricerca aziendale | thehackernews, projectdiscovery | piattaforma Blogger |
| 15 | https://research.checkpoint.com/ | blog aziendale di ricerca, WordPress | projectdiscovery.io/research | ricerca di sicurezza |
| 16 | https://blog.cloudflare.com/ | blog aziendale (piattaforma da verificare) | projectdiscovery | blog aziendale tecnico |
| 17 | https://cert-agid.gov.it/ | portale istituzionale italiano (home), WordPress | ACN | avvisi di sicurezza |
| 18 | https://www.cisa.gov/news-events/cybersecurity-advisories | sezione di un portale istituzionale, Drupal | ACN | sezione con articoli fuori percorso |
| 19 | https://www.garanteprivacy.it/ | portale istituzionale italiano (Liferay da verificare) | ACN | Liferay, comunicati |
| 20 | https://realpython.com/ | formazione | freecodecamp | tutorial, feed |
| 21 | https://developer.mozilla.org/en-US/blog/ | sezione di un sito di formazione (piattaforma da verificare) | freecodecamp/news | sezione, JavaScript |
| 22 | https://www.404media.co/ | testata tecnologica su Ghost, paywall parziale | nature.com | piattaforma Ghost, paywall |
| 23 | https://netflixtechblog.com/ | Medium con dominio proprio | blog aziendali | piattaforma Medium |
| 24 | https://vercel.com/blog | sezione, Next.js | projectdiscovery.io/research | Next.js |
| 25 | https://www.ilpost.it/tecnologia/ | sezione di un sito generalista, WordPress | e3rehab.com/articles | sezione di un sito grande |

Le sezioni sono 18, 21, 24 e 25; gli altri sono home.

### 3b. Metriche

**La verità di riferimento non deve dipendere dalle strategie da giudicare.** Oggi l'unione delle strategie
sarebbe circolare. Contiene voci da `lastmod` non confermate, traduzioni e date future: con 6a-2 la copertura
sembrerebbe scendere anche se l'algoritmo migliora. Si propongono tre riferimenti, dal più forte al più debole,
e ogni sito dichiara quale usa:
1. **riferimento indipendente**, dove esiste: l'API completa della piattaforma (WordPress con `X-WP-Total` e
   tutte le pagine), l'archivio per data del sito (per esempio `/2026/11/`), la news sitemap per gli ultimi 2
   giorni. Si legge una volta per campagna, con tutte le pagine;
2. **unione ristretta**: solo le voci la cui data di pubblicazione è confermata dai metadati della pagina
   (`article:published_time`, JSON-LD `datePublished`, o trafilatura). Si leggono le pagine di tutte le voci
   dell'unione, con un tetto per sito; quelle non lette restano "non confermate" e si contano a parte;
3. **campione a mano dalle pagine di elenco**: 20 link a caso dalla home e dalle sezioni, etichettati da una
   persona (articolo sì o no, data dalla pagina). Gli articoli della finestra che l'algoritmo non trova danno
   una stima dei persi, con il suo intervallo. Le etichette (indirizzi e date pubbliche) si versionano in
   `tests/fonti/siti/banco/etichette.json`.

**Cosa resta non misurabile**: i siti senza API, senza archivio per data e con elenchi senza date
(hwupgrade). Per loro la copertura è solo un limite inferiore, e il volume del sito si dichiara come stima.

**Metriche per sito** (calcolate rigiocando le risposte registrate):

| Metrica | Definizione |
|---|---|
| copertura | articoli della finestra trovati / articoli del riferimento (con l'indicazione del riferimento usato) |
| falsi articoli | candidate che il campione a mano o le regole oggettive (file, UUID, `cdn-cgi`) dicono non articoli |
| voci di altri domini | metrica a parte, perché dipende dalla risposta alla domanda 5 |
| falsi nuovi | candidate con data nella finestra ma pubblicazione fuori (riferimento 1 o 2) |
| precisione delle date | scarto fra la data usata e i metadati della pagina, sulle pagine lette per il riferimento 2: quota entro 24 ore e caso peggiore |
| date incerte | candidate rimaste incerte / candidate |
| pagine e byte | richieste (robots.txt a parte) e byte per esecuzione; richieste per articolo nuovo |
| richieste mancanti | indirizzi chiesti nel rigioco e non registrati (vedi 3c): se non sono zero, il confronto è parziale |
| token | creazione del profilo (oggi 0) e raccolta (deve restare 0, `WEB-04`); stima dell'effetto a valle con i costi della 6b |
| tempo | stimato dalle latenze registrate più le pause |

**Aggregazione**: per tipo di sito (le etichette della tabella 2b), con mediana e caso peggiore, più il
totale. Due scenari:
- **prima esecuzione**: finestra di 7 giorni, registro vuoto;
- **a regime**: finestra di 3 giorni, registro con le viste del giorno prima. Servono due registrazioni in
  due giorni consecutivi.

**Soglie per dire che una modifica è accettabile** (proposta):
- nessun tipo di sito perde più di 2 punti di copertura mediana, e nessun sito passa da "ok" a un errore;
- falsi articoli e falsi nuovi non aumentano;
- il 95% delle date certe entro 24 ore dai metadati della pagina;
- a parità di copertura, le richieste per esecuzione non aumentano più del 10%; se aumentano, la copertura
  deve salire almeno di 5 punti sul tipo interessato;
- token di raccolta sempre 0; l'aumento stimato a valle è dichiarato.

### 3c. Lo strumento

Un **banco di misura** con risposte registrate (proposta 6a-1, scheda nella sezione 4). In breve:
- `tests/fonti/siti/banco.py`, uno script di sviluppo come `verifica_reale.py` (non gira con pytest), nella
  cartella dello scraping;
- tre comandi: `registra` (richieste vere con tetti), `rigioca` (solo risposte registrate, con l'orologio fermo
  all'ora della registrazione), `confronta` (due risultati, tabella delle metriche);
- **file in `.gradiens/banco/<AAAA-MM-GG_HHMM>/`**, mai in una cartella temporanea: la registrazione del 12/11 è
  andata persa così (sezione 2a). `.gradiens/` sopravvive ai riavvii ed è fuori da git (`PER-02`, `PER-03`).
  - Il nome della campagna non contiene `:`, che non è valido su Windows; i nomi dei file sono hash
    dell'indirizzo, l'indice è JSON in UTF-8, i corpi sono compressi.
  - Insieme alle risposte si salvano i risultati di sintesi, così una campagna resta leggibile anche senza
    rigiocarla.
  - Una campagna occupa decine di MB (circa 50 MB quella del 12/11): il banco dice quanto spazio usa e permette
    di cancellare le campagne vecchie;
- **registrazione larga**: per poter confrontare varianti senza nuove richieste, la campagna registra più di
  quanto chiede l'algoritmo di oggi. Si registrano tutte le strategie senza fermarsi, tutte le figlie degli
  indici fino a un tetto, l'API WordPress con tutte le pagine, la news sitemap e i feed linkati dalla pagina
  iniziale;
- **indirizzi non registrati nel rigioco**: il trasporto non va in rete, risponde con un errore riconoscibile e
  conta una "richiesta mancante". Il confronto riporta quante ne mancano: se non sono zero, è parziale;
- **siti nuovi**: senza profilo si registra anche `analizza`. Gli host ammessi sono il dominio del sito, gli
  host dei feed e delle sitemap linkati dalla pagina iniziale o dichiarati in robots.txt, e gli host dei
  redirect di questi. Altrimenti feedburner, Substack e Medium resterebbero fuori, e 6a-4, 6a-7, 6a-8, 6a-9 e
  6a-12 non si potrebbero misurare;
- **cookie** conservati nella registrazione, e rigioco con lo stesso client dell'app;
- **costo di una campagna**:
  - il 12/11: 281 richieste per 13 siti, circa 5 minuti di richieste, in media 22 per sito;
  - con 13 + 25 siti e 60 richieste per sito: al massimo 2.280 al giorno, probabilmente 800-900 (stima con la
    media del 12/11, più alta con la registrazione larga);
  - per lo scenario a regime servono due giorni consecutivi: circa 1.600-1.800 richieste (stima).

  Il tetto totale di 600 del passaggio del 12/11 va quindi alzato per la campagna, e ogni campagna va chiesta
  all'utente;
- per non disturbare i siti: il `Navigatore` dell'app (robots.txt, pause), una pausa di cortesia in più, tetti
  rigidi nel trasporto, mai una URL richiesta due volte nella stessa campagna.

---

## 4. Miglioramenti all'algoritmo

**Regole comuni a tutte le schede**:
- tutte tengono l'interfaccia comune delle strategie (`async analizza(nav, profilo, pagina)` e
  `async raccogli(nav, profilo, dal) -> Raccolta`, `fonti/siti/strategie/__init__.py:1-10`) e il registro
  `STRATEGIE`. Un comportamento nuovo è un modulo nuovo o un attributo facoltativo del modulo;
- ogni passo è committabile da solo con i test verdi;
- sforzi: **S** mezza giornata, **M** 1-2 giorni, **L** 3-5 giorni, tutti stime, test e review compresi;
- costi a valle in token: circa 2.600 token per notizia nuova di sito e circa 220 per una candidata che si
  ferma al pre-filtro (6b, sezione 2, cifre arrotondate).

### 6a-1 Banco di misura con risposte registrate

- **Problema**:
  - oggi una modifica si prova solo con le fixture (`tests/fonti/siti/fixture/`, 17 file) o con
    `verifica_reale.py`, che fa richieste vere a ogni giro e riporta solo i conteggi;
  - `verifica-accettazione.md` ha dato `ACC-01` per "Sì" il 7/11 contando gli articoli, senza un riferimento.
    Nel passaggio del 12/11, invece, ACN non trova 26 dei 43 articoli dell'unione in 7 giorni, e redhotcyber
    21 su 30 in 3 giorni.
- **Opzioni**:
  - A. lasciare così: ogni prova costa richieste e non si confrontano due versioni;
  - B. fixture più grandi versionate: ripetibili, ma il contenuto dei siti finirebbe in git e invecchia;
  - C. banco con registrazione larga in `.gradiens/banco/` e rigioco offline (consigliata).
- **Raccomandazione**: C, riscrivendo dentro il progetto il prototipo del 12/11 (sezione 2a), andato perso con
  la cartella temporanea.
- **Effetto atteso**: nessuno sui siti né sui token; rende misurabili le altre proposte. Un confronto costa 0
  richieste solo se la variante chiede indirizzi registrati: per questo serve la registrazione larga, e le
  richieste mancanti vanno contate.
- **Come verificarlo**:
  - la registrazione del 12/11 non esiste più e non si può rigiocare;
  - la prima campagna sui 13 siti deve dare numeri dello stesso ordine della sezione 2b (147 richieste e 451
    candidate in 7 giorni; uguali no, perché i siti cambiano);
  - due rigiochi della stessa campagna devono dare risultati identici, anche dopo un riavvio del PC.
- **Windows e Linux**: `pathlib`, nomi dei file da hash, nome della campagna senza `:`, `encoding="utf-8"`,
  nessun processo esterno. Da provare anche su Windows.
- **Passi**:
  1. `TrasportoRegistrato` (conta, tetti, host ammessi, registra in `.gradiens/banco/`, rigioca, conta le
     richieste mancanti), con test su `httpx.MockTransport`;
  2. comando `registra` per i siti del database o di un file, con registrazione larga e tetti come parametri;
  3. orologio fermo nel rigioco. Non basta sostituire `date.adesso`, perché `strategie/feed.py:10` e
     `strategie/html.py:9` importano `adesso` per nome: o si sostituisce in ogni modulo che lo importa, o (più
     pulito) le strategie lo chiamano come `date.adesso()`. È un piccolo refactoring a parte, con i suoi test;
  4. comando `rigioca`; calcolo delle metriche della sezione 3b; comando `confronta`;
  5. registrazione di `analizza` per i siti nuovi;
  6. etichette a mano in `tests/fonti/siti/banco/etichette.json`.
- **Test**: tetti rispettati anche con redirect e nuovi tentativi; nessuna richiesta in rigioco; richiesta
  mancante contata; stesso risultato in due rigiochi; file leggibili su entrambi i sistemi.
- **Rischi e effetti collaterali**: le registrazioni invecchiano: una campagna serve a confrontare due versioni
  dell'algoritmo, non a dire come va il sito oggi. Lo spazio su disco va tenuto sotto controllo.
- **Requisiti, contratti, schema**: nessuno. Il punto 3 del passo tocca `strategie/` ma non il contratto.
- **Sforzo**: M (passi 1-4), più S per i passi 5 e 6.

### 6a-2 Date: `lastmod` da confermare, niente date future

- **Problema**:
  - una data presa solo da `lastmod` diventa certa (`strategie/sitemap.py:48`, `:114-117`). Sono 7 falsi nuovi
    su 102 controllati (sezione 2b), fino a 3 su 7 candidate della sitemap a freecodecamp. Un falso nuovo
    finisce al pre-filtro, vince l'ordinamento del tetto e può far scattare il guasto "feed fermo"
    (`fonti/siti/__init__.py:100-102`);
  - `nella_finestra` accetta le date future (`date.py:90-94`): 2 casi misurati;
  - `updated` del feed vale come pubblicazione (`strategie/feed.py:36`). A nature tutte le 75 voci hanno solo
    `dc:date`, che feedparser mette in `updated` ed è la data di pubblicazione al giorno: non si può scartarlo
    in blocco.
- **Opzioni**:
  - A. lasciare così;
  - B. `lastmod` sempre "data incerta": ogni candidata da `lastmod` andrebbe a `_date_incerte`. ilsoftware (52),
    gamesbeat (53) e redhotcyber (30) finirebbero al tetto di pagine, con molte "data incerta" in dashboard;
  - C. `lastmod` **da confermare** (consigliata). La data si conferma con il primo segnale disponibile, senza
    pagine:
    - data nell'indirizzo, news sitemap, feed;
    - API WordPress: una richiesta per tutto il sito, oggi non letta perché la sitemap copre prima, quindi +1
      richiesta salvo con 6a-5.

    Solo dopo si legge la pagina dell'articolo, e solo per gli indirizzi non visti (6a-3). Se il profilo
    impara che il `lastmod` del sito è affidabile (ilsoftware: 5 su 5 uguali alla pubblicazione), non si
    spendono pagine;
  - D. data di prima scoperta come limite: utile solo dalla seconda esecuzione (vedi 6a-6).
- **Raccomandazione**: C, più il rifiuto delle date oltre "adesso + 1 giorno" in `nella_finestra`. Un falso
  nuovo riconosciuto come vecchio oggi non entra nel registro: le pagine scartate per data si rileggono a ogni
  esecuzione, finché non si fa anche il registro degli scartati di 6a-3.
- **Effetto atteso**:
  - -7 falsi nuovi a settimana sui siti misurati; ognuno arriva al pre-filtro una volta, quindi circa -18 mila
    token a settimana (stima: 7 × 2.600);
  - pagine: +1 richiesta per l'API dove serve; +1 pagina per ogni articolo nuovo che nessun altro segnale
    conferma.
- **Come verificarlo**: banco, metriche "falsi nuovi", "date incerte" e "pagine per articolo nuovo" per tipo.
- **Windows e Linux**: nessun impatto.
- **Passi** (nell'ordine, ognuno senza effetti visibili sulle date incerte finché il successivo non c'è):
  1. date future rifiutate, con test;
  2. conferma di `lastmod` con indirizzo, news sitemap e feed dentro `raccogli`. Le voci non confermate restano
     come oggi e si contano nel dettaglio;
  3. conferma con l'API WordPress (dopo 6a-5 per non aggiungere richieste);
  4. conferma con la pagina, solo per le non viste (dopo 6a-3);
  5. solo ora le voci ancora non confermate diventano "data incerta";
  6. statistica di affidabilità di `lastmod` per sito. Richiede uno spazio per le statistiche: le colonne di
     6a-6 (una migrazione) oppure una scrittura del profilo durante la raccolta, che oggi non c'è.
- **Test**: articolo vecchio con `lastmod` recente non entra; `lastmod` uguale al feed passa senza pagina; data
  futura scartata; feed con solo `dc:date` resta valido.
- **Rischi e effetti collaterali**: più pagine sui siti senza API né feed lungo; il "feed fermo" va ricalcolato
  solo con date confermate; più "data incerta" visibili se il passo 5 arriva prima dei passi 3 e 4.
- **Requisiti, contratti, schema**:
  - `WEB-15` va precisato: "feed o sitemap" diventa "data di pubblicazione di feed, news sitemap o API;
    `lastmod` solo se confermata";
  - contratto delle fonti (`docs/architettura/struttura.md:54`, "con la data incerta si usa quella di
    scoperta"): se la candidata da confermare porta la data di `lastmod` come valore provvisorio, il contratto
    cambia e va aggiornato. L'alternativa è tenere la data di scoperta e mettere `lastmod` in un campo
    facoltativo nuovo di `Candidata`, che è sempre un cambio di contratto;
  - migrazione: solo per il passo 6, condivisa con 6a-6.
- **Sforzo**: S (passi 1-2), M (passi 3-6).

### 6a-3 Il registro delle viste dentro la fonte

- **Problema**:
  - la fonte non conosce il registro (`fonti/siti/__init__.py:80-130`; il filtro sta in
    `esecuzione/esecutore.py:263-264`). Il tetto di 100 articoli si applica prima del registro, e le date
    incerte si cercano anche sui visti. A hwupgrade 6 delle 36 pagine per la data erano di articoli già nel
    registro (fermo da un giorno e mezzo). In tutto 165 candidate su 451 erano già viste;
  - le pagine fuori finestra non entrano mai nel registro: `_date_incerte` le scarta
    (`fonti/siti/__init__.py:151-153`) e il registro si scrive solo nell'esecutore. Le 24 pagine vecchie di
    hwupgrade (download, guide, gallerie, notizie vecchie) si rileggono quindi a ogni esecuzione;
  - la pagina letta per la data si scarica di nuovo in `completa` (`rete.py:164`, `estrazione.py:50`).
- **Opzioni**:
  - A. lasciare così;
  - B. parametro facoltativo della fonte siti, `raccogli(client, profilo, dal, viste=None)`: `viste` è una
    funzione `list[str] -> set[str]`, che l'esecutore passa come `notizie.gia_viste` legata alla sessione
    (consigliata);
  - C. un insieme già calcolato di tutte le viste (1.447 righe oggi): semplice, ma cresce con il registro;
  - D. due fasi nella fonte ("elenca" economica, "data" costosa) con l'esecutore in mezzo: più pulito, ma
    cambia il contratto di tutte le fonti.

  In più, con qualunque opzione, un **registro degli scartati per data**: gli indirizzi con data di
  pubblicazione verificata fuori finestra si ricordano per 7 giorni, così la loro pagina non si rilegge. Costa
  una tabella piccola (indirizzo, data, quando) o l'uso della tabella `notizie_viste` con un segno: è una
  migrazione.
- **Raccomandazione**: B più il registro degli scartati. Il filtro delle viste si applica **solo** all'ordine
  del tetto e a `_date_incerte`, non alla copertura né al controllo del feed fermo. Il parametro ha un default,
  quindi arXiv e YouTube non cambiano.
- **Effetto atteso**:
  - B da solo evita al più le pagine degli articoli già visti: 6 delle 36 il 12/11. A regime, al più le pagine
    dei 10-12 articoli che erano nella finestra o senza data (stima);
  - con il registro degli scartati spariscono anche le 24 pagine vecchie, dalla seconda esecuzione in poi;
  - token: il tetto conta solo le nuove, quindi a hwupgrade passano più notizie nuove. Ipotesi: qualche decina
    al giorno, circa 26 mila token ogni 10 notizie in più.
- **Come verificarlo**: banco, scenario a regime (due registrazioni consecutive): pagine per articolo nuovo,
  notizie nuove al pre-filtro.
- **Windows e Linux**: nessun impatto.
- **Passi**:
  1. parametro `viste` in `fonti/siti/raccogli`, usato per l'ordine del tetto e per `_date_incerte`, con test
     (scraping);
  2. l'esecutore lo passa (backend, `esecuzione/`);
  3. registro degli scartati per data, con migrazione provata su una copia del database vero;
  4. riuso della pagina in `completa` (vedi effetti collaterali).
- **Test**: un visto non costa pagine; il tetto tiene le nuove; un feed con voci tutte viste non diventa "feed
  fermo"; una pagina scartata per data non si rilegge all'esecuzione dopo.
- **Rischi e effetti collaterali**:
  - se il filtro si applicasse dentro la cascata, un feed con voci tutte già viste sembrerebbe fermo e darebbe
    un falso guasto (`WEB-24`): per questo il filtro resta fuori dalla cascata;
  - lo stato del sito resta calcolato come oggi ("ok" se ci sono candidate nella finestra), per non cambiare
    `WEB-26`;
  - più notizie nuove arrivano al pre-filtro (più token);
  - riuso della pagina: `completa` crea un nuovo `Navigatore` (`estrazione.py:50`). Serve una cache delle
    pagine dell'esecuzione, in `rete.py`, limitata in byte (per esempio 50 MB), non in numero di articoli: le
    pagine lette dipendono da `pagine_massime`, che arriva a 500 (`dashboard/rotte_impostazioni.py:210`).
- **Requisiti, contratti, schema**: contratto delle fonti in `struttura.md` ("Contratti"), da aggiornare
  insieme al codice e da comunicare al backend-engineer; migrazione per il registro degli scartati.
- **Sforzo**: M.

### 6a-4 Feed linkato da una sezione (caso ACN)

- **Problema**: `strategie/feed.py:69-71` scarta il feed di ACN. Delle 50 voci, 15 sono linkate dalla pagina e
  0 stanno nel percorso; la pagina ha 49 link da articolo, 15 dei quali nel feed. In 7 giorni `raccogli` trova
  17 articoli veri (19 candidate meno 2 non articoli) con 11 richieste.
- **Opzioni**:
  - A. lasciare così: l'utente dovrebbe inserire il feed a mano, ma lo stato è "ok" e non lo sa;
  - B. per una sezione, accettare un feed **specifico** linkato dalla pagina (rel=alternate o link)
    (consigliata). Specifico vuol dire che non è il feed generale del sito, cioè non è uno dei percorsi comuni
    alla radice come `/feed/` o `/rss.xml`; inoltre le voci stanno sullo stesso host e almeno 3 sono linkate
    dalla pagina. Per il feed generale e per i percorsi comuni resta la regola di oggi, che a e3rehab accetta
    già il feed;
  - C. abbassare la soglia di oggi (per esempio 25%): fragile, dipende dalla lunghezza del feed e della pagina.
- **Raccomandazione**: B. È coerente con `WEB-09` ("gli articoli che la sezione elenca valgono anche fuori dal
  percorso") e con `WEB-20` (canale ufficiale).
- **Effetto atteso** (deduzione dalle tabelle 2b):
  - con il feed, che copre, la cascata si ferma prima dell'HTML (`fonti/siti/__init__.py:107`). Si ottengono
    le 38 voci del feed contro 17: +21 in 7 giorni;
  - si perdono i 5 articoli dell'unione (43 − 38) trovati solo dall'HTML;
  - richieste da 11 a 2 (robots.txt e feed); niente più immagini fra le candidate;
  - token: +21 a settimana, cioè circa +3 notizie al giorno, circa +8 mila token al giorno (stima);
  - per non perdere i 5 articoli si può tenere l'HTML come controllo periodico (con 6a-6, opzione C).
- **Come verificarlo**: banco su ACN e sulle sezioni nuove (18, 21, 24, 25 della tabella 3a). **Prima** di
  rendere definitiva la modifica, perché il suo rischio si vede proprio su 18 e 25.
- **Windows e Linux**: nessun impatto.
- **Passi**:
  1. test con la pagina e il feed di ACN come fixture;
  2. modifica della regola;
  3. aggiornamento del profilo di ACN. Oggi l'unico modo è la rigenerazione dal bottone
     (`dashboard/rotte_impostazioni.py:217-224`), che rifà l'analisi (fino a 40 pagine). Nessun passo di 6a-11
     aggiorna i profili esistenti da solo: va detto all'utente.
- **Test**: feed specifico linkato dalla sezione, con voci fuori percorso, accettato; feed generale (`/feed/`)
  linkato da una sezione giudicato con la regola di oggi; feed di un altro host scartato.
- **Rischi e effetti collaterali**: un sito che linka da una sezione un feed generale con un indirizzo non
  comune (per esempio `/rss/tutto.xml`) porterebbe articoli di altre sezioni. L'anteprima di 6a-11 aiuterebbe.
- **Requisiti, contratti, schema**: nessuno.
- **Sforzo**: S.

### 6a-5 Copertura vera della cascata (feed in ritardo)

- **Problema**: "copre" guarda solo il fondo della finestra (`strategie/feed.py:99-105`), e la cascata si ferma
  (`fonti/siti/__init__.py:107`). A redhotcyber il feed è fermo all'11/11 06:35 UTC, con 19 articoli più
  recenti nell'API; con 3 giorni si trovano 9 articoli contro 30 nell'unione. Il controllo del feed fermo
  (righe 98-102) scatta solo quando il feed non dà candidate.
- **Opzioni**:
  - A. lasciare così;
  - B. leggere sempre, oltre al feed, la **news sitemap** o l'**API WordPress** quando il sito le ha
    (consigliata). È una richiesta in più, piccola (11-57 KB per le news sitemap misurate), con date esatte;
  - C. "copre" anche in alto: il feed copre solo se la sua voce più recente non è più vecchia della più recente
    di un'altra fonte, o di quanto la frequenza del sito fa attendere (richiede le statistiche di 6a-6);
  - D. combinare sempre tutte le strategie: più pagine dove non serve (nature: 19 sitemap e 20 pagine HTML
    anche nei giorni in cui il feed copre).
- **Come si esprime B con l'interfaccia comune**: "leggere sempre" una parte della strategia sitemap non si
  esprime né con `analizza` e `raccogli` (`strategie/__init__.py:3-7`) né con il ciclo della cascata. Si
  propone:
  - un **modulo nuovo** `strategie/controllo.py`, con le stesse due funzioni: legge news sitemap o API e
    restituisce una `Raccolta`;
  - un **attributo facoltativo** del modulo, `SEMPRE = True`, che il ciclo di `fonti/siti/__init__.py:90-108`
    legge per non fermarsi prima di lui. Va in `STRATEGIE` subito dopo `feed`.

  Le altre strategie non cambiano.
- **Raccomandazione**: B subito, C con 6a-6.
- **Effetto atteso** (stime; il numero esatto non è più ricostruibile dai dati grezzi):
  - redhotcyber, 3 giorni: con la news sitemap (21 voci in 7 giorni, 19 articoli più recenti del feed)
    circa 21-28 articoli invece di 9. Con l'API si arriverebbe vicino ai 30 dell'unione, ma entrerebbero anche
    le traduzioni `/en/` (domanda 9);
  - richieste: +1 solo dove oggi la cascata si ferma al feed (thehackernews, redhotcyber, e nature nei giorni in
    cui il feed copre). A ilsoftware e gamesbeat la sitemap si legge già;
  - token: redhotcyber circa +5-7 notizie al giorno, circa +13-18 mila token al giorno (stima).
- **Come verificarlo**: banco, scenario a regime, copertura dei siti con feed corti o in ritardo.
- **Windows e Linux**: nessun impatto.
- **Passi**:
  1. riconoscere le news sitemap dal contenuto (`news:publication_date`) e segnarle nel profilo, con test;
  2. modulo `controllo` e attributo `SEMPRE`, con test sul ciclo della cascata;
  3. il guasto "feed fermo" diventa anche "feed in ritardo", quando la fonte di controllo ha articoli più
     recenti dell'ultima voce del feed oltre una tolleranza (per esempio 12 ore).
- **Test**: feed con voci vecchie ma senza le ultime → la news sitemap aggiunge gli articoli recenti e segnala il
  ritardo; feed aggiornato → nessun guasto.
- **Rischi e effetti collaterali**: un falso "feed in ritardo" senza tolleranza; con l'API entrano le
  traduzioni.
- **Requisiti, contratti, schema**: `WEB-24` cita "un feed fermo mentre la sitemap mostra articoli più recenti":
  il feed in ritardo ne è un caso. `WEB-10` e `WEB-12` restano rispettati (modulo nuovo). Il contratto delle
  strategie si estende con un attributo facoltativo, da scrivere nel docstring di `strategie/__init__.py`.
  Nessuna migrazione.
- **Sforzo**: S-M.

### 6a-6 Raccolta incrementale, piano di raccolta e tetti adattivi

- **Problema**:
  - ogni esecuzione cerca tutta la finestra da capo e i tetti sono fissi a 40 e 100
    (`fonti/siti/profilo.py:33-34`);
  - con esecuzioni giornaliere basterebbe coprire il tempo dall'ultima raccolta riuscita. I feed corti (6,5-10
    ore) restano insufficienti, ma una news sitemap (2 giorni per le regole di Google) o l'API bastano, e le
    sitemap grandi non servono più;
  - hwupgrade pubblica circa 50-65 articoli al giorno (stima): 40 pagine non bastano a datarne una settimana.
- **Opzioni**:
  - A. lasciare così e alzare i tetti a mano (oggi si può dalla dashboard, `rotte_impostazioni.py:206-214`):
    più pagine anche sui già visti;
  - B. **finestra effettiva**: da "coperto fino a" dell'ultima raccolta riuscita, meno un margine (per esempio 6
    ore), fino a adesso, sempre dentro la finestra di raccolta. Si usa la finestra intera alla prima
    esecuzione, dopo un guasto, dopo un cambio di `finestra_giorni` e dopo una modifica del profilo (feed o
    sezione aggiunti a mano) (consigliata);
  - C. B più un **piano di raccolta** imparato. Per ogni strategia si ricordano gli articoli unici trovati e il
    costo nelle ultime 10 esecuzioni. Una strategia che da 10 esecuzioni non aggiunge niente si salta, salvo un
    controllo ogni 7 esecuzioni: così sui siti poco frequenti resta il controllo del feed fermo. I tetti si
    calcolano come frequenza × intervallo × 2, con un massimo;
  - D. stato del sito "copertura parziale" quando il budget non basta (hwupgrade), invece di "ok" con una nota.
- **Raccomandazione**: B, poi C e D.
- **Quando si salva "coperto fino a"**: **non** al momento della raccolta (`esecuzione/esecutore.py:227`), ma
  solo a fine esecuzione, e solo se tutte le candidate del sito hanno avuto un esito. Se l'esecuzione si
  interrompe (`QuotaEsaurita`) o una valutazione fallisce e "si riprova la volta dopo"
  (`esecutore.py:302-315`), quelle notizie non sono nel registro. Con una finestra effettiva già spostata
  uscirebbero dalla finestra e si perderebbero senza segnale. In alternativa si tiene un elenco di candidate in
  attesa.
- **Effetto atteso** (stime grossolane):
  - richieste per esecuzione, a regime: da circa 130 (base a 3 giorni, dedotta nella sezione 2b) a circa
    40-60. Per ogni sito resterebbero robots.txt, feed e una fonte con date; nature senza le 19 sitemap e le
    20 pagine HTML; hwupgrade con meno pagine per la data solo insieme a 6a-3 e 6a-9;
  - token: gli altri siti trovano gli stessi articoli, prima. hwupgrade, se si coprisse tutto, passerebbe da
    circa 35 notizie nuove per esecuzione (esecuzione 10) a 50-65: circa +40-80 mila token per esecuzione,
    fino a un terzo del risparmio di 6b-2 (stima).
- **Come verificarlo**: banco con due registrazioni in giorni consecutivi: copertura uguale o migliore, pagine e
  byte minori, token a valle stimati.
- **Windows e Linux**: nessun impatto (solo dati nel database).
- **Passi**:
  1. colonne nuove in `siti` (`coperto_fino_a`, `statistiche` in JSON), con migrazione Alembic provata su una
     copia del database vero (`piano-fase-4.md`, nota sulle migrazioni);
  2. `EsitoSito` restituisce fino a dove la raccolta ha coperto; l'esecutore lo salva a fine esecuzione;
  3. `raccogli` usa la finestra effettiva, con i casi di reset;
  4. statistiche per strategia;
  5. piano e tetti adattivi;
  6. stato "copertura parziale".
- **Test**: la seconda esecuzione legge solo il nuovo; un guasto, un cambio di finestra o un feed aggiunto
  riportano alla finestra intera; un'esecuzione interrotta non sposta "coperto fino a"; una strategia inutile
  salta e torna al controllo periodico; migrazione su un database con dati.
- **Rischi e effetti collaterali**: un articolo pubblicato con data retroattiva (prima di "coperto fino a") si
  perde, ma il margine lo limita. Un errore nel calcolo di "coperto fino a" fa perdere articoli in silenzio:
  servono test e la metrica di copertura del banco. Più notizie per hwupgrade vuol dire più quota.
- **Requisiti, contratti, schema**: migrazione di `siti` (backend). Precisazioni di `WEB-19` (tetti adattivi) e
  di `WEB-26` (stato "copertura parziale"). Il contratto "Metriche e resoconto" di `struttura.md` cambia se lo
  stato nuovo va nelle metriche. La definizione di finestra di raccolta (CONTEXT.md) non cambia. Da decidere
  con l'utente (domanda 4).
- **Sforzo**: L.

### 6a-7 Sitemap più mirate

- **Problema**:
  - indici senza date: si leggono le ultime 5 figlie (`strategie/sitemap.py:103-104`). A nature sono 18 letture
    e circa 7,5 MB senza candidate; a thehackernews 8 letture su 9 senza candidate (indice, 5 figlie,
    `expert-insights` e `videos`, secondo il profilo nel database);
  - figlie scelte per `lastmod` (`:102`): si leggono sitemap vecchie che danno 0-2 candidate, e a parità di data
    vince l'ordine dell'indice (sezione 2c);
  - all'analisi un indice vale se non è vuoto (`:73`), quindi nature tiene l'indice da 40.745 figlie;
  - un indice "copre" se una figlia qualunque ha un `lastmod` vecchio, anche mai letta (`:101`).
- **Opzioni**:
  - A. lasciare così;
  - B. all'analisi tenere le news sitemap e le sitemap che hanno voci recenti, scartare gli indici senza date
    con più di, per esempio, 1.000 figlie (consigliata). `analizza` oggi non ha una finestra: si userebbero gli
    ultimi 7 giorni. Per non togliere la sitemap a evilsocket e chipsandcheese, e con lei il controllo del feed
    fermo, si tiene sempre almeno una sitemap quando il profilo ha un feed;
  - C. in raccolta, fra le figlie "di articoli" (`post-sitemapN`, `focus-sitemapN`) leggere quella con il
    numero più alto in ogni famiglia di nomi, non quelle con `lastmod` recente (consigliata). Le altre si
    leggono solo se la finestra non è coperta, e questo richiede di cambiare anche la riga 101: una figlia non
    letta non deve più contare come copertura;
  - D. con 6a-6 e una news sitemap, non leggere l'indice nelle esecuzioni normali.
- **Raccomandazione**: B e C, D con 6a-6.
- **Effetto atteso** (deduzioni, da verificare con il banco):
  - nature: -7,5 MB circa. Ma il tetto di 40 pagine è pieno, quindi le 18 letture si spostano sull'HTML: le
    richieste restano quasi le stesse, mentre byte e copertura migliorano;
  - thehackernews: fino a -8 richieste quando la cascata arriva alla sitemap;
  - redhotcyber, gamesbeat e ilsoftware: -1/-2 sitemap vecchie da 0,3-1,2 MB l'una. I falsi nuovi che portano
    sono già contati in 6a-2, non qui;
  - token: nessun effetto proprio.
- **Come verificarlo**: banco: copertura invariata o migliore, byte minori, richieste per tipo.
- **Windows e Linux**: nessun impatto.
- **Passi**:
  1. scelta delle figlie per numero e famiglia, con test sulla fixture `sitemap_index.xml`;
  2. la riga 101 conta solo le figlie lette;
  3. criterio di analisi;
  4. aggiornamento dei profili esistenti: come in 6a-4, solo con la rigenerazione dal bottone.
- **Test**: indice WordPress con figlia vecchia modificata → si legge la figlia più recente; figlia non letta non
  copre; indice enorme senza date scartato all'analisi; sito con feed che tiene almeno una sitemap.
- **Rischi e effetti collaterali**: siti con figlie divise per tema e non per data; a nature cambia l'equilibrio
  fra sitemap e HTML sotto il tetto.
- **Requisiti, contratti, schema**: nessuno.
- **Sforzo**: S-M.

### 6a-8 Piattaforme: riconoscerle meglio e usarle

- **Problema**: `piattaforma` guarda `meta generator` e tre segni nel testo (`pagine.py:47-59`); ilsoftware non è
  riconosciuto pur avendo l'intestazione `Link: rel="https://api.w.org/"`. Solo WordPress ha una strategia, senza
  paginazione (`strategie/wordpress.py:45`).
- **Opzioni** (le strategie sono moduli nuovi in `STRATEGIE`):
  - A. lasciare così: oggi tra i 13 cambierebbe poco (ilsoftware ha l'API vietata);
  - B. riconoscimento migliore: intestazioni (`Link` con `api.w.org`, `x-powered-by`, `x-generator`),
    `<link rel="https://api.w.org/">`, `wp-json` nel testo, percorsi tipici (`/ghost/`, `/_next/`, `/o/` di
    Liferay, `/feeds/posts/default` di Blogger). Costa 0 richieste, ma `Pagina` non conserva le intestazioni:
    va aggiunto il campo;
  - C. API WordPress paginata con `page` e `X-WP-TotalPages` (`per_page` al massimo 100, documentazione
    ufficiale), e `after` arrotondato al giorno, così l'indirizzo è stabile;
  - D. Blogger: il feed ufficiale `/feeds/posts/default` accetta parametri di quantità e data (da verificare sul
    sito: oggi thehackernews passa da feedburner);
  - E. RSS paginati (`?paged=2` dei feed WordPress, RFC 5005 `rel="next"`, `prev-archive`): nessuno dei feed
    registrati li dichiarava;
  - F. Ghost Content API, archivio di Substack, JSON:API di Drupal: la prima richiede una chiave, le altre non
    sono documentate o sono spesso spente. **Sconsigliate** finché il banco non mostra un sito che ne ha
    bisogno.
- **Raccomandazione**: B e C; il resto solo se il banco con i siti nuovi lo giustifica.
- **Effetto atteso**: generalizzazione ai WordPress con temi o CDN che non espongono `/wp-content/`; con
  l'API, una richiesta ogni 100 articoli. Token: nessun effetto sui 13; sui siti nuovi dipende da quanti
  articoli in più si trovano.
- **Come verificarlo**: banco sulle home WordPress nuove (2, 3, 5, 7, 8, 9, 12, 15, 17 della tabella 3a; il 25 è
  una sezione e in una sezione la strategia WordPress è spenta, `strategie/wordpress.py:36`).
- **Windows e Linux**: nessun impatto.
- **Passi**: 1) intestazioni in `Pagina`; 2) segni nuovi in `piattaforma`, con test; 3) paginazione dell'API;
  4) eventuali strategie nuove, una per volta, ciascuna con test e misura.
- **Test**: ilsoftware riconosciuto come WordPress senza strategia API (vietata); API con 2 pagine.
- **Rischi e effetti collaterali**: una strategia nuova senza misura rischia di restare codice morto.
- **Requisiti, contratti, schema**: nessuno (`WEB-10` e `WEB-12` già li prevedono).
- **Sforzo**: S per B e C; M per ogni piattaforma nuova.

### 6a-9 HTML più preciso: non articoli e pagine per la data spese meglio

- **Problema**:
  - `sembra_articolo` (`indirizzi.py:95-103`) accetta file e UUID (verificato con il codice il 13/11): ACN
    `process.png/<UUID>` e `misp-feed-index`, redhotcyber 5 PDF. Rifiuta invece slug corti;
  - l'HTML accetta qualunque link con una data vicina (`strategie/html.py:35-38`), anche se futura: così entra
    `cdn-cgi/l/email-protection`;
  - hwupgrade: le 36 pagine per la data sono andate per 28 a link che non hanno la forma delle notizie dei
    feed (schede di download, guide, gallerie, articoli lunghi). Le 70 voci dei feed hanno tutte la forma
    `/news/<categoria>/<slug>_<id>.html` (66) o `/news/<slug>_<id>.html` (4);
  - JSON-LD negli elenchi: nessuna delle 71 pagine di elenco registrate ha `ItemList` o `Article`, né
    `__NEXT_DATA__`;
  - l'id negli indirizzi di hwupgrade **non** è ordinato per data. Nel database ci sono 28 notizie di hwupgrade:
    39 coppie su 378 hanno id e data in ordine opposto, 10 di queste con giorni diversi. Per esempio l'id
    161699 è del 10/11 alle 15:11 UTC, mentre gli id da 161720 a 161791 sono dell'8 e del 9/11. Nel registro
    ci sono anche id vecchi (160714, 161497) entrati come nuovi in una finestra di 3 giorni (mappa C2 i).
- **Opzioni**:
  - A. lasciare così;
  - B. rifiuto **in `non_articolo`** (`strategie/html.py:31`, prima della data) di file (estensioni, anche in
    mezzo al percorso), UUID e `cdn-cgi`; date future rifiutate (6a-2) (consigliata);
  - C. **forma degli indirizzi** imparata all'analisi dalle voci di feed e sitemap, che sono articoli sicuri:
    `/news/<categoria>/<slug>_<id>.html` (hwupgrade), `/post/<slug>/` (redhotcyber), `/portale/w/<slug>`
    (ACN). Serve come **priorità** per le pagine per la data: prima i link che la rispettano, poi gli altri.
    Non serve a scartare: a hwupgrade 4 articoli lunghi nella finestra non hanno quella forma (consigliata);
  - D. id crescente come data: **scartata**, smentita dal database. Al più un segnale debole di priorità, che
    però richiederebbe di salvare "ultimo id visto" a ogni raccolta;
  - E. JSON-LD e dati incorporati negli elenchi, come strategia per i siti che li hanno, se il banco con i siti
    nuovi ne trova (0 su 71 pagine il 12/11).
- **Raccomandazione**: B e C.
- **Effetto atteso** (deduzioni):
  - B: meno non articoli al pre-filtro e meno "errore di estrazione". A ACN i 2 non articoli spariscono già con
    6a-4 (l'HTML non parte più), ma la regola vale per tutti i siti;
  - C: il tetto di pagine non diminuisce; le pagine si ridistribuiscono. A hwupgrade, delle 36 di oggi solo 8
    erano notizie della forma dei feed: con la priorità, le pagine andrebbero prima alle altre notizie della home
    (71 con id) e poi al resto;
  - token: più notizie datate e nuove a hwupgrade, conteggio insieme a 6a-6.
- **Come verificarlo**: banco: falsi articoli, date incerte, notizie nuove per pagina a hwupgrade; etichette a
  mano su ACN e hwupgrade.
- **Windows e Linux**: nessun impatto.
- **Passi**: 1) regole nuove in `non_articolo`, con test (immagini, PDF, UUID, `cdn-cgi`); 2) forma degli
  indirizzi nel profilo, un campo nuovo (`Profilo.da_dict` ignora i campi sconosciuti, quindi il JSON resta
  compatibile); 3) priorità in `_date_incerte`.
- **Test**: link di immagini e PDF scartati prima della data; `cdn-cgi` con data vicina scartato; link con la
  forma dei feed letti per primi; link senza la forma non scartati.
- **Rischi e effetti collaterali**: un sito che cambia lo schema degli indirizzi: la forma va rifatta alla
  rigenerazione. Regole troppo severe in `non_articolo` perderebbero articoli veri con nomi strani: i test
  devono coprire i 13 siti.
- **Requisiti, contratti, schema**: nessuna migrazione (il profilo è JSON); nessun contratto toccato.
- **Sforzo**: M.

### 6a-10 Rete: cache persistente e richieste condizionali

- **Problema**:
  - `_cache` e `_robots` stanno in memoria (`rete.py:30-33`). Finché il servizio resta acceso, la cache fa già
    richieste condizionali fra un'esecuzione e l'altra (fino a 500 voci); dopo un riavvio si riparte da zero;
  - i feed grandi dei siti quieti hanno `ETag` o `Last-Modified`: chipsandcheese 1.644 KB, e3rehab 1.306 KB,
    evilsocket 532 KB, freecodecamp 343 KB, in tutto circa 3,8 MB. Non hanno intestazioni di convalida i feed di
    hwupgrade, il feed di ACN e le sitemap di gamesbeat e ilsoftware;
  - l'indirizzo dell'API WordPress cambia a ogni esecuzione (`strategie/wordpress.py:45`).
- **Opzioni**:
  - A. lasciare così;
  - B. cache dei feed e delle sitemap su disco in `.gradiens/cache/siti/` (`PER-02`), con le sole intestazioni di
    convalida e il corpo (consigliata). Nomi da hash, scrittura atomica (`os.replace`, valida su Windows e
    Linux), al massimo qualche decina di MB;
  - C. anche robots.txt su disco per 24 ore (RFC 9309 lo consente): utile solo con più esecuzioni al giorno.
- **Raccomandazione**: B; C facoltativa.
- **Effetto atteso** (deduzione): circa -3,8 MB alla prima esecuzione dopo ogni riavvio del servizio, se i
  server rispondono 304; nessun guadagno se il servizio resta acceso. Le richieste non diminuiscono; i token
  nemmeno.
- **Come verificarlo**: il banco non lo misura (registra risposte 200). Si misura con due esecuzioni vere separate
  da un riavvio, contando i 304: oggi le metriche non contano le pagine, va aggiunto.
- **Windows e Linux**: scrittura su disco con `pathlib` e `os.replace`; scrive un solo processo.
- **Passi**: 1) metriche di pagine, byte e 304 per sito; 2) cache su disco; 3) API WordPress con `after`
  arrotondato al giorno.
- **Test**: cache che sopravvive a un riavvio simulato; un 304 che rilegge il corpo salvato; cartella entro il
  limite.
- **Rischi e effetti collaterali**: un corpo salvato corrotto si scarta e si rilegge.
- **Requisiti, contratti, schema**: `WEB-18` chiede già la cache HTTP. Le metriche nuove toccano il contratto
  "Metriche e resoconto" di `struttura.md` (riga 69), da aggiornare. Nessuna migrazione.
- **Sforzo**: S-M.

### 6a-11 Profilo: protezione, differenze, anteprima, sezioni

- **Problema**:
  - quando un sito non risponde per 3 esecuzioni, il profilo diventa senza strategie (sezione 1). Si
    rianalizza dopo altre 3, quindi dopo il ritorno del sito si perdono fino a 3 esecuzioni di raccolta. Il
    profilo buono si perde del tutto dopo 6 esecuzioni di fila senza risposta;
  - `profilo_precedente` non si mostra (`WEB-25`); manca l'anteprima (`WEB-02`); le sezioni non si vedono né si
    cambiano (`WEB-03`);
  - le sezioni proposte sono spesso inutili (redhotcyber: conferenze e partner).
- **Opzioni**:
  - A. lasciare così;
  - B. **protezione** (consigliata). Se la nuova analisi trova meno strategie della vecchia e la pagina iniziale
    non risponde (errore di rete, 5xx, blocco), si tiene il vecchio profilo e si segnala; si sostituisce solo se
    il sito risponde ma le risorse non ci sono più. Serve che `analizza` o `rigenera` dicano "la pagina iniziale
    non risponde" (un campo nuovo del profilo o un valore restituito). Vale anche per il bottone
    (`dashboard/rotte_impostazioni.py:217-224`);
  - C. **anteprima**: dopo l'analisi, una raccolta e i primi 10 articoli con data e strategia. Oggi sarebbero
    fino a 40 letture con le pause dentro la richiesta di aggiunta, cioè minuti di attesa. Serve un disegno:
    in secondo piano con l'avanzamento, oppure un tetto basso (per esempio 10 pagine, solo feed e sitemap);
  - D. **differenze**: confronto campo per campo fra `profilo_precedente` e `profilo`;
  - E. **sezioni**: elenco con aggiungi e togli (dashboard). Le sezioni proposte solo dal menu principale, non
    dal piè di pagina (`pagine.py:13`, `:91`): questa parte è scraping.
- **Raccomandazione**: B subito (scraping, esecuzione e la rotta del bottone); E per la parte di scraping; C, D
  e la parte di dashboard di E con il frontend-engineer.
- **Effetto atteso**: fino a 3 esecuzioni senza raccolta evitate dopo un'interruzione del sito; conformità a
  `WEB-02`, `WEB-03`, `WEB-25`. Token: nessuno.
- **Come verificarlo**: test; per l'anteprima e le sezioni, banco sui siti nuovi.
- **Windows e Linux**: nessun impatto.
- **Passi**: 1) protezione, con test; 2) sezioni dal solo menu principale, con test; 3) differenze; 4) anteprima
  in secondo piano; 5) sezioni nella dashboard.
- **Test**: rigenerazione con sito irraggiungibile che tiene il vecchio profilo, anche dal bottone; differenze di
  un feed tolto; anteprima che rispetta il suo tetto e non blocca la pagina; sezione aggiunta e tolta che
  sopravvive alla rigenerazione.
- **Rischi e effetti collaterali**: un profilo vecchio davvero rotto resta più a lungo; il guasto resta comunque
  visibile nella Home.
- **Requisiti, contratti, schema**: nessuna migrazione; implementa requisiti esistenti.
- **Sforzo**: S per B; M per il resto.

### 6a-12 LLM solo alla creazione del profilo, con input ridotto

- **Problema**: `WEB-04` permette l'LLM alla creazione del profilo, oggi assente. Dove le euristiche
  falliscono (sezioni scelte male, elenchi non riconosciuti, esclusioni commerciali) l'utente non ha aiuto.
- **A cosa servirebbe davvero**:
  - scegliere fra le sezioni proposte quelle che elencano articoli (non conferenze, partner, glossari);
  - riconoscere la forma degli indirizzi degli articoli quando non ci sono feed né sitemap;
  - proporre esclusioni commerciali.

  **Non** serve per le date. Non serve ai 9 siti su 13 che hanno un feed o una sitemap che coprono 7 giorni
  (tutti tranne hwupgrade, nature, ACN e projectdiscovery). Non serve mai nelle esecuzioni (`WEB-04`,
  `WEB-05`).
- **Input minimo**: l'albero dei link ridotto, cioè i link interni della pagina raggruppati per forma
  dell'indirizzo, con il numero di link, se stanno nel menu e due testi di esempio. Sulle 12 pagine iniziali
  registrate (nature esclusa) erano da 375 a 15.036 caratteri. Diviso per 2,35 fa circa 160-6.400 token, contro
  9.000-118.000 dell'HTML intero. È una **stima**: 2,35 caratteri per token è il rapporto misurato dalla 6b su
  JSON in italiano, non su HTML né su testo inglese.
- **Costo per sito** (stima): circa 1.300 token di carico fisso, 160-6.400 di input e 500-700 di uscita, cioè 2-9
  mila token, una volta all'aggiunta o alla rigenerazione. È meno di una chiamata di pre-filtro (circa 14 mila
  in ingresso nell'esecuzione 10: 239.085 su 17 chiamate).
- **Opzioni**:
  - A. niente LLM (oggi);
  - B. LLM automatico quando le euristiche non trovano strategie o trovano meno di 3 articoli;
  - C. LLM **su richiesta** dell'utente ("Chiedi aiuto all'LLM" nel profilo), con un tetto di token per sito
    (consigliata);
  - D. LLM sempre all'analisi: costo inutile sui 9 siti che non ne hanno bisogno.
- **Raccomandazione**: C, dopo 6a-4, 6a-7 e 6a-9. Solo tramite l'interfaccia dei provider (ADR 0006,
  `llm/base.py`), con il ruolo di elaborazione e uno schema JSON di risposta. La risposta è un dato esterno: si
  accettano solo indirizzi presenti nell'albero e nel perimetro.
- **Effetto atteso**: generalizzazione sui siti "solo HTML" difficili; 2-9 mila token per sito, una volta
  (stima).
- **Come verificarlo**: banco sui siti nuovi senza feed né sitemap; copertura con e senza il suggerimento; token
  veri della chiamata.
- **Windows e Linux**: nessun impatto (il provider è già portabile).
- **Passi**: 1) funzione pura "albero dei link ridotto", con test; 2) prompt e schema; 3) chiamata dal profilo
  su richiesta; 4) differenze mostrate prima di applicare.
- **Test**: con il provider finto (`llm/finto.py`), una risposta con indirizzi fuori perimetro si scarta.
- **Rischi e effetti collaterali**: quota (decisione 6: solo abbonamento); suggerimenti sbagliati, per questo
  l'utente approva.
- **Requisiti, contratti, schema**: nessuna migrazione; un ADR sul ruolo dell'LLM nel profilo, dopo la
  decisione.
- **Sforzo**: M.

### 6a-13 Meno candidate inutili al pre-filtro (raccordo con la 6b)

- **Problema**: arrivano al pre-filtro:
  - voci di terzi domini (hwupgrade: 2 di `fotografidigitali.it` nel feed la sera del 12/11, 1 nel registro);
  - non articoli (ACN 2);
  - falsi nuovi (6a-2);
  - candidate senza sommario (228 su 451);
  - offerte che il pre-filtro deve riconoscere (20 nell'esecuzione 9, 11 nella 10).
- **Opzioni**:
  - A. lasciare così: il pre-filtro le scarta, a circa 220 token l'una;
  - B. filtro sulle voci dei feed (consigliata). Il filtro del perimetro da solo scarterebbe tutte le voci di
    3blue1brown: il feed sta su `3blue1brown.substack.com` e il perimetro è `3blue1brown.com`. La regola
    proposta è quindi più stretta:
    - si tengono le voci del perimetro e quelle sull'host del feed stesso (Substack, feedburner, Medium);
    - si scartano le voci di **terzi** domini, e il dominio si propone come sito collegato (`WEB-07`).

    Contraddice l'interpretazione attuale di `WEB-08` (`fonti/siti/profilo.py:25`): decide l'utente (domanda 5);
  - C. sommari: per i siti WordPress l'API dà l'estratto di tutti gli articoli con una richiesta; altrove la
    descrizione della pagina costa una pagina per articolo nuovo. Va valutato con la 6b: un sommario migliora il
    pre-filtro ma allunga il prompt;
  - D. **regola facoltativa sui titoli** per le offerte. Sui titoli delle esecuzioni 9 e 10 (verificato sul
    database il 13/11):
    - con le parole `€`, "sconto", "offerta", "coupon", "Black Friday", "prezzo", "AliExpress", "Amazon" prende
      26 delle 31 offerte riconosciute dall'LLM;
    - con le radici (scont-, offert-, prezz-) ne prende 27;
    - aggiungendo "euro" dopo un numero e "Singles' Day" ne prende 28;
    - in tutti i casi sbaglia 2 delle 116 notizie di siti mostrate da quelle esecuzioni (1,7%).

    Il campione è piccolo, stagionale (Singles' Day) e non comprende le notizie scartate dal pre-filtro: il
    database non ne conserva il titolo.
- **Raccomandazione**: B se l'utente conferma l'interpretazione; D solo come esclusione del profilo proposta
  all'analisi e disattivabile, da decidere insieme alla 6b.
- **Effetto atteso** (stime): B, circa 1-2 candidate in meno per esecuzione; D, circa 13-14 offerte per
  esecuzione tolte prima del pre-filtro, circa -3 mila token per esecuzione. Le offerte oggi non arrivano alla
  valutazione, quindi si risparmia solo il pre-filtro.
- **Come verificarlo**: banco (metrica "voci di altri domini") e metriche delle esecuzioni (scartate e
  sponsorizzate).
- **Windows e Linux**: nessun impatto.
- **Passi**: 1) filtro dei terzi domini sui feed, con test che includono 3blue1brown e hwupgrade; 2) estratti
  dall'API; 3) regola sui titoli, se approvata.
- **Test**: voce di un terzo dominio scartata e dominio proposto; voce sull'host del feed Substack tenuta; titolo
  di offerta escluso solo con la regola attiva.
- **Rischi e effetti collaterali**: la regola sui titoli scarta notizie vere (2 su 116 nel campione); il filtro
  dei terzi domini toglie articoli che l'utente forse voleva (si recuperano attivando il sito collegato).
- **Requisiti, contratti, schema**: `WEB-08` (interpretazione); `WEB-21` e `WEB-22` (regola sui titoli).
  Nessuna migrazione.
- **Sforzo**: S-M.

---

## 5. Ordine consigliato e dipendenze

| Ordine | Proposta | Perché qui | Dipende da |
|---|---|---|---|
| 1 | 6a-1 banco, passi 1-4 | serve a verificare quasi tutte le altre, compreso il rischio di 6a-4 | decisione dell'utente sulla campagna (domande 1-2) |
| 2 | 6a-11 B protezione del profilo | piccola, indipendente, si verifica con i test | – |
| 3 | 6a-4 feed di sezione | +21 articoli ACN in 7 giorni | banco sui siti 18 e 25 prima di renderla definitiva |
| 4 | 6a-5 modulo di controllo (news sitemap o API) | redhotcyber da 9 a circa 21-28 articoli in 3 giorni | – |
| 5 | 6a-2 date, passi 1-2 | date future e conferma senza pagine | – |
| 6 | 6a-7 sitemap mirate | byte, figlie giuste | – |
| 7 | 6a-3 registro nella fonte e degli scartati | niente pagine sui visti e sui vecchi | backend-engineer (contratto, migrazione) |
| 8 | 6a-2 date, passi 3-5 | conferma con API e pagina | 6a-5, 6a-3 |
| 9 | 6a-9 HTML più preciso | non articoli, pagine per la data | banco per misurarlo |
| 10 | 6a-6 raccolta incrementale | il guadagno più grande su pagine e tetti | banco, 6a-3, migrazione, domanda 4 |
| 11 | 6a-2 date, passo 6 | `lastmod` affidabile per sito | colonne di 6a-6 |
| 12 | 6a-13 candidate inutili | raccordo con la 6b | domanda 5 (`WEB-08`), domanda 7 (titoli) |
| 13 | 6a-11 C, D, E | anteprima, differenze, sezioni | frontend-engineer |
| 14 | 6a-8 piattaforme | generalizzazione ai siti nuovi | banco con i siti nuovi |
| 15 | 6a-10 cache su disco | solo byte dopo un riavvio | metriche delle pagine |
| 16 | 6a-12 LLM nel profilo | solo per i casi residui | 6a-4, 6a-7, 6a-9; domanda 6 |

**Cosa si può verificare senza il banco**: con i test a fixture salvati si verifica il **meccanismo** di ogni
modifica (regola di ACN, modulo di controllo, date future, scelta delle figlie, protezione del profilo). Non si
verifica l'**effetto** su copertura, pagine e generalizzazione, né i rischi sui siti diversi dai 13. Per questo
il banco viene prima. Se l'utente preferisce partire subito, 6a-11 B, 6a-9 B e il passo 1 di 6a-2 sono sicuri
anche senza banco.

---

## 6. Domande per l'utente

Da fare una alla volta. Per ognuna, la risposta consigliata.

1. **Quali siti nuovi usiamo per misurare?** Consiglio: 15-20 dei 25 della tabella 3a, scelti per coprire tutte
   le piattaforme, e sapendo che 18 e 23 potrebbero essere bloccati e 9-11 pubblicano poco. Perché: senza siti
   mai visti non si misura la generalizzazione, solo l'adattamento ai 13.
2. **Posso fare una campagna di registrazione?** Sarebbero al massimo 60 richieste per sito, in due giorni
   consecutivi, circa 1.600-1.800 richieste in tutto per 38 siti (stima): il tetto totale di 600 del passaggio
   del 12/11 andrebbe alzato, per esempio a 2.000 per campagna. Consiglio: sì, una volta, con le registrazioni in
   `.gradiens/banco/`. Perché: dopo, ogni confronto fra versioni costa zero richieste.
3. **Una data presa solo da `lastmod` deve essere "da confermare"?** Consiglio: sì, con la conferma da
   indirizzo, news sitemap, feed o API, e la pagina solo per gli articoli nuovi. Perché: 7 falsi nuovi su 102
   misurati, con un costo basso.
4. **Va bene la raccolta incrementale?** Ogni esecuzione cercherebbe dall'ultima raccolta riuscita, sempre
   dentro la finestra, con uno stato nuovo "copertura parziale" e una migrazione della tabella `siti`.
   Consiglio: sì. Perché: è l'unico modo di seguire hwupgrade. Le richieste scenderebbero da circa 130 a 40-60
   per esecuzione, ma è una stima grossolana: la base a 3 giorni è dedotta, non contata.
5. **Un feed può portare articoli di terzi domini** (hwupgrade → fotografidigitali.it)? Consiglio: no, salvo che
   l'utente attivi quel dominio fra i siti collegati, proposto in automatico; le voci sull'host del feed stesso
   (Substack, feedburner) restano. Perché: `WEB-08` dice che il feed non allarga il perimetro, ma 3blue1brown
   vive su Substack.
6. **L'LLM può aiutare alla creazione del profilo**, su richiesta, con un tetto per sito (per esempio 10.000
   token)? Consiglio: sì, ma dopo le euristiche e solo su richiesta. Perché: costa meno di una chiamata di
   pre-filtro (stima), serve solo ai siti difficili e resta fuori dalle esecuzioni.
7. **Una regola facoltativa sui titoli per le offerte**, proposta all'analisi e disattivabile? Consiglio: da
   decidere insieme alla 6b. Perché: sui dati di due esecuzioni prende l'84-90% delle offerte, a seconda delle
   parole, ma sbaglia l'1,7% delle notizie vere mostrate, su un campione piccolo e stagionale.
8. **Se un sito non risponde e la nuova analisi non trova niente, si tiene il vecchio profilo?** Consiglio: sì,
   segnalando il problema. Perché: oggi, dopo il ritorno del sito, si perdono fino a 3 esecuzioni di raccolta,
   e dopo 6 esecuzioni di fila senza risposta il profilo buono sparisce.
9. **Le traduzioni dello stesso sito** (redhotcyber `/en/post/`) sono notizie da raccogliere? Consiglio: no per
   default, con un'esclusione proposta all'analisi. Perché: sono doppioni in un'altra lingua, costano
   pre-filtro ed entrerebbero con l'API (6a-5).
10. **Quanta della quota liberata dalla 6b si può spendere per trovare più articoli dei siti?** Insieme 6a-4,
    6a-5 e 6a-6 aggiungerebbero circa 60-110 mila token per esecuzione (stima), su circa 226 mila liberati da
    6b-2. Consiglio: sì, con un tetto di notizie nuove per sito per esecuzione (i tetti adattivi di 6a-6).
    Perché: la scoperta, non la quota, è oggi il limite dei siti, ma hwupgrade da solo potrebbe prendersi un
    terzo del risparmio.

---

## 7. Fonti esterne

Consultate il 12 novembre 2026, solo documentazione ufficiale:
- Protocollo delle sitemap: https://www.sitemaps.org/protocol.html (significato di `lastmod`, "data
  dell'ultima modifica della pagina"; 50.000 voci e 50 MB per file; `lastmod` di un indice riferito al file).
- News sitemap di Google: https://developers.google.com/search/docs/crawling-indexing/sitemaps/news-sitemap
  (solo articoli degli ultimi due giorni; fino a 1.000 voci; `news:publication_date` è la prima pubblicazione).
- API REST di WordPress, paginazione: https://developer.wordpress.org/rest-api/using-the-rest-api/pagination/
  (`per_page` al massimo 100; `page`, `offset`; intestazioni `X-WP-Total` e `X-WP-TotalPages`).
- RFC 5005, feed paginati e archiviati: https://www.rfc-editor.org/rfc/rfc5005.html.
- RFC 9309, robots.txt: https://www.rfc-editor.org/rfc/rfc9309.html (cache al massimo 24 ore; 4xx = tutto
  permesso; 5xx o irraggiungibile = tutto vietato; almeno 5 redirect).

---

## Nota sulla mappa dei moduli

Il passaggio diagnostico conferma alcune ipotesi della mappa:
- le 40 pagine di hwupgrade sono 3 feed, 1 HTML e 36 pagine per la data;
- quando la sitemap copre, le sezioni non si usano;
- `lastmod` produce falsi nuovi.

Un'ipotesi è **smentita**. In C2(i) la mappa ipotizza che il feed di ACN "non è linkato dalla pagina della
sezione e non sta nei percorsi comuni". Invece è linkato, e viene scartato dalla regola della metà
(`feed.py:69-71`).

Una precisazione al punto 4 delle "dieci cose": hwupgrade non è l'unico sito che arriva al tetto delle 40
pagine. Ci arriva anche nature, con 7 giorni e anche con 3 giorni nel rigioco del 12/11 sera. Non dipende dalla
durata della finestra, ma dal fatto che quel giorno il feed copra. Il feed di nature ha date al giorno, e
`nella_finestra` considera dentro la finestra tutto il giorno di `dal`. Quindi il feed copre solo se la sua
voce più vecchia è di un giorno precedente a quello di `dal`. Nelle esecuzioni 9 e 10 copriva, e nature si è
fermata al feed.
