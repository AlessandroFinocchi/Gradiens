# Decisioni dell'intervista sui miglioramenti

Registro delle risposte dell'utente durante il lavoro di analisi e proposta descritto in
[README.md](README.md), e durante la sua implementazione (15-17 novembre 2026). Ogni voce ha un numero e una
data. Le decisioni importanti hanno anche un ADR in `docs/adr/` (0010-0013, tutti implementati al 17 novembre 2026).

**Numeri**: si sovrappongono a quelli di [decisioni-intervista.md](../requisiti/decisioni-intervista.md) (1-60).
Nel codice e nei test "decisione N" senza altro rimanda a questo registro; quelle dell'intervista sui requisiti si
scrivono "decisione N dei requisiti".

## Intervista iniziale (12 novembre 2026)

1. **Priorità** (12 nov 2026): i due problemi che pesano di più sono la **quota LLM** (poche
   notizie esplorate a parità di quota) e la **ricerca delle notizie sui siti** (articoli persi,
   date, tetti, siti nuovi). Affidabilità e accesso da fuori casa vengono dopo.
   *Conseguenza*: già nella fase 1 la mappa va più a fondo sulle chiamate LLM di un'esecuzione e
   sulla cascata di strategie dei siti; le proposte 6b e 6a sono le più importanti della fase 6.
2. **Macchina di riferimento** (12 nov 2026): il Gradiens usato ogni giorno gira su **questa
   macchina Linux** (Debian 13), non sul PC Windows di casa indicato dall'ADR 0001 e da `AMB-01`.
   *Conseguenza*: database e log in `.gradiens/` di questa cartella sono dati veri e sono la base
   delle misure (token, copertura dei siti, bug). Il ramo Windows resta da verificare con prove
   chieste all'utente. La differenza rispetto all'ADR 0001 è annotata qui e va ripresa nella
   proposta 6c (chi usa Gradiens e da dove): per ora non cambia nessun ADR.
3. **Quanto possono essere invasive le proposte** (12 nov 2026): **libertà ampia**. Vanno bene
   anche riscritture di moduli interi, dipendenze nuove e modifiche allo schema del database, se
   il guadagno su quota o sui siti è grande. Restano fermi i vincoli di CLAUDE.md: provider LLM
   intercambiabili (ADR 0006), strategie dei siti come moduli intercambiabili, dati solo in
   `.gradiens/` e `.env`, Windows e Linux.
   *Conseguenza*: ogni proposta indica comunque rischio di regressione e passi committabili da
   soli; dove esiste, si affianca l'opzione ambiziosa a quella prudente.

Nessuna di queste tre risposte è una decisione di architettura: non hanno un ADR.

## Ordine delle fasi e fase 6 (12 novembre 2026)

4. **Ordine delle fasi** (12 nov 2026): dopo la fase 1 si fanno prima le proposte **6b** (consumo
   di token) e **6a** (ricerca sui siti), poi le fasi 2, 3, 4, 5 e infine la 6c.
5. **Misura con chiamate vere a Claude Code** (12 nov 2026): **sì**. Al massimo 8 chiamate brevi
   con Haiku (stima: meno di 40.000 token in tutto), con le stesse opzioni dell'app, per misurare
   carico fisso, cache e costo dello schema JSON. Vale solo per questa misura: ogni altro consumo
   di quota va chiesto di nuovo.
6. **Leve ammesse per la 6b** (12 nov 2026): **solo l'abbonamento**. Niente modelli locali
   (questo portatile non ha una GPU dedicata; Ollama e LM Studio non sono installati) e niente
   API a pagamento. Si pianificano solo le leve dentro Claude Code e quelle senza LLM (ordine dei
   passi, blocchi, input ridotto, niente ripetizioni, deduplicazione, euristiche). Modelli
   locali, embedding e API a consumo si descrivono con il risparmio stimato ma non si pianificano.
   *Nota*: non cambia l'architettura. I provider restano intercambiabili (ADR 0006, `LLM-03`):
   è una scelta su cosa pianificare ora, quindi non ha un ADR.
7. **Passaggio diagnostico sui 13 siti veri per la 6a** (12 nov 2026): **sì, una volta**. Uno
   script fuori dal progetto usa il codice di raccolta dell'app (robots.txt rispettato, pause per
   sito), con un tetto di 60 richieste per sito e circa 600 in tutto, senza chiamate LLM. Vale
   solo per questo passaggio: altre richieste in massa ai siti vanno chieste di nuovo.

## Decisioni sulla proposta 6b (13 novembre 2026)

8. **`ARX-02` cambia** (13 nov 2026, domanda D1 della 6b): **sì**. I paper arXiv passano dal
   pre-filtro dal più recente, a blocchi, finché i promossi riempiono il tetto; gli altri entrano
   nel registro delle notizie già viste. Proposta 6b-2 accettata.
   ADR: [0010](../adr/0010-prefiltro-arxiv-fino-al-tetto.md), implementato il 15 nov 2026 con `ARX-02` aggiornato.
9. **Tetto arXiv** (13 nov 2026, D2): **30** dopo la modifica di `ARX-02` (oggi 10); si valuta se
   salire a 50 dopo una settimana di metriche vere. Il risparmio stimato ne sosterrebbe circa 50.
10. **Misure con chiamate vere** (13 nov 2026, D3): autorizzate **M1-M6, a tempi separati**.
    M1-M2 (circa 15.000 token: contesto aggiunto da Claude Code, cache a 5 minuti); M3-M6 (circa
    310-415.000 token: lotti, effort basso, tetto per pertinenza, sommario corto), da fare in un
    momento in cui la quota non serve all'utente: prima di ogni gruppo si concorda il momento.
    M7 (peso di cache e ragionamento sulla quota) **non** è autorizzata. I risultati si salvano
    subito in `docs/` (i dati della misura del 12 nov sono andati persi con un riavvio).
11. **Perdita accettabile** (13 nov 2026, D4): nel pre-filtro al massimo il **2%** di notizie
    pertinenti perse; nella valutazione al massimo il **5%** di notizie che cambiano lato rispetto
    alla soglia, e nessun errore di fatto in 5 riassunti riletti a mano. Sopra queste soglie una
    modifica che risparmia token non si fa.
12. **Quota liberata** (13 nov 2026, D5 della 6b e domanda 10 della 6a): la quota che resta dopo il
    tetto 30 (circa 130.000 token per esecuzione, stima) si spende per trovare più articoli dai
    siti (proposte 6a), **senza un tetto di notizie nuove per sito**. Restano i tetti di pagine e
    di articoli per sito di `WEB-19`. *Rischio accettato*: un sito ad alto volume (hwupgrade) può
    consumare gran parte della quota nei giorni pieni.
13. **Video YouTube esclusi** (13 nov 2026, D6): i 7 video delle esecuzioni 8, 9 e 10, tutti
    esclusi dal pre-filtro come "sponsorizzato o offerta", erano video che l'utente **voleva
    ricevere**. È un difetto: oggi YouTube non produce nessuna notizia. Va nella fase 4 con
    priorità alta (ipotesi: la descrizione del video contiene link di sponsor e affiliazioni).
    *Conseguenza per la 6b*: corretto il difetto, i video costeranno quota (stima della 6b: 7-29
    mila token per video), da togliere dal margine della decisione 12.
14. **Script di misura** (13 nov 2026, D7): in **`scripts/misura/`**, versionati, fuori da `src/`
    e da `tests/`; risultati in `.gradiens/misure/`, esclusi da git (`PER-02`). Da aggiungere a
    `struttura.md` quando la cartella viene creata.

## Decisioni sulla proposta 6a (13 novembre 2026)

15. **Niente misura della generalizzazione** (13 nov 2026, domande 1 e 2): l'utente ha cambiato
    idea: **non si misura più quanto l'algoritmo generalizza**. Niente banco di misura, niente
    campagna di registrazione, niente insieme di siti nuovi. La proposta 6a-1 e la sezione 3 della
    6a restano come documentazione, non pianificate. *Conseguenza*: le modifiche ai siti si
    verificano con i test su file salvati (il meccanismo) e guardando le esecuzioni vere; gli
    effetti scritti nella 6a restano stime.
16. **Date da `lastmod`** (13 nov 2026, domanda 3): **lasciare così**. Una data presa solo
    dall'ultima modifica della sitemap resta una data certa. *Rischio accettato*: circa 1 articolo
    su 15 tra quelli datati solo dalla sitemap è un articolo vecchio che arriva come nuovo. Della
    proposta 6a-2 resta solo il rifiuto delle date future (non era oggetto della domanda).
17. **Raccolta incrementale** (13 nov 2026, domanda 4): **sì**. Proposta 6a-6 accettata, con la
    migrazione della tabella `siti` e lo stato "copertura parziale".
    ADR: [0011](../adr/0011-raccolta-incrementale-dei-siti.md), implementato il 17 nov 2026.
18. **Voci di altri domini nei feed** (13 nov 2026, domanda 5): **fuori**, salvo che il dominio sia
    attivato tra i siti collegati del profilo; restano valide le voci sull'host del feed stesso
    (Substack, feedburner). Chiarisce `WEB-08`; il codice oggi accetta tutte le voci.
19. **LLM nel profilo del sito** (13 nov 2026, domanda 6): **sì, su richiesta e per ultimo**. Un
    bottone alla creazione o rigenerazione del profilo, con un tetto di 10.000 token per sito,
    tramite l'interfaccia dei provider (ADR 0006), mai durante le esecuzioni (`WEB-04`). Si
    implementa dopo le correzioni deterministiche. Proposta 6a-12 accettata.
20. **Regola sui titoli per le offerte** (13 nov 2026, domanda 7): **no**. Le offerte restano al
    pre-filtro. Quella parte della proposta 6a-13 è scartata.
21. **Profilo di un sito che non risponde** (13 nov 2026, domanda 8): **si tiene il profilo
    vecchio** e si segnala il problema; la rigenerazione sostituisce il profilo solo se trova
    almeno una strategia che funziona. Precisa `WEB-24` e `WEB-25`. Proposta 6a-11 B accettata.
22. **Traduzioni dello stesso sito** (13 nov 2026, domanda 9): **escluse per default**, con
    un'esclusione proposta all'analisi e modificabile dal profilo.

## Decisioni sulla fase 2, test e copertura (13 novembre 2026)

23. **`pytest-cov`** (13 nov 2026, domanda 1): **sì, senza soglia minima**. Si aggiunge come
    dipendenza di sviluppo quando si passa al codice, con il rapporto di copertura in CI su Windows
    e Linux; prima va verificato che `coverage` supporti Python 3.14.
24. **Test che fissano un comportamento sbagliato** (13 nov 2026, domanda 3): restano **verdi con
    un commento** "vedi S-nn"; quando il bug si corregge, il test si ribalta nello stesso commit.
    Niente `xfail`.
25. **Chiamata vera per il difetto dei video YouTube** (13 nov 2026, domanda 4): **sì, nella fase
    4**: una richiesta al feed del canale e una chiamata di pre-filtro con Haiku (stima: circa
    5.000 token). Vale solo per questa prova; il risultato si salva subito in `docs/`, senza dati
    personali.
26. **Test prima del codice** (13 nov 2026, domanda 8): **i primi 10** (T-01…T-10) prima del primo
    commit di codice per ADR 0010 e 0011; gli altri del gruppo A insieme alle modifiche; il gruppo
    B solo quando si decide un refactoring.
27. **"Rate limit" trattato come quota esaurita** (13 nov 2026, sospetto S-03): **lasciare così**.
    Qualsiasi segnale di limite interrompe l'esecuzione, che riprende alla successiva. S-03 non è
    un bug e non passa alla fase 4.

Domande della fase 2 **non ancora fatte** (minori; tra parentesi il consiglio del documento, non una
decisione): tre prove sul PC Windows (sì); cartelle `tests/accettazione/` e `docs/test/` previste da
`struttura.md` ma mai create (non crearle e correggere `struttura.md`); isolare `HOME` in
`tests/conftest.py` (sì: è una scelta tecnica, non dipende dall'utente).

## Decisioni sulla fase 3, revisione architetturale (14 novembre 2026)

28. **Refactoring prima delle modifiche già decise** (14 nov 2026, domanda 2 del documento): **i
    cinque passi** R-02a, R-01, R-03, R-04, R-02b (vocabolario comune; metriche, pre-filtro e
    tetto, raccolta e politica dei siti in moduli propri; stati dei siti nel modello della
    dashboard). Gli altri sei passi si fanno solo quando si tocca quel codice.
    *Stato al 17 nov 2026*: fatto solo R-02a. R-01, R-03, R-04 e R-02b non sono stati fatti, e le modifiche che
    dovevano precedere (ADR 0010, ADR 0011, decisione 21) sono già nel codice: cosa farne è da decidere di nuovo.
29. **Proposta 6b-1, metriche di token dettagliate** (14 nov 2026, domanda 1): **no, per ora**.
    Le metriche restano quelle di oggi. *Conseguenza*: l'effetto del nuovo pre-filtro arXiv (ADR
    0010) e delle altre leve si giudica solo dai totali; il passo R-01 si fa comunque, come base
    degli altri.
30. **Test T-11…T-14** (14 nov 2026, domanda 3): **non si anticipano**; restano "insieme alle
    modifiche", come nella decisione 26. *Rischio accettato*: i passi R-03 e R-04 spostano rami
    che oggi nessun test esegue (errori imprevisti di un sito, rigenerazione fallita, blocchi con
    errori misti).
31. **Proprietari** (14 nov 2026, domanda 4): `fonti/__init__.py` (contratto delle fonti)
    all'**architetto**, `tests/conftest.py` al **tester**. Da scrivere in `struttura.md`.
32. **Modifiche che attraversano più proprietari** (14 nov 2026, domanda 5): si preparano come
    passi separati e in fila, uno per proprietario, ognuno con i test verdi. **I commit li fa solo
    l'utente**, come già stabilito in CLAUDE.md: quando e come committare i passi lo decide lui.
33. **Dove vive l'LLM del profilo del sito** (14 nov 2026, domanda 6, proposta P-1): in un
    **modulo del backend**; `fonti/siti` fornisce solo funzioni senza LLM; il tetto di token si
    applica prima della chiamata e si controlla dopo, senza allargare l'interfaccia dei provider.
    ADR: [0012](../adr/0012-llm-del-profilo-del-sito-nel-backend.md), implementato il 17 nov 2026.
34. **Regola di "coperto fino a"** (14 nov 2026, domanda 7, proposta P-2): a fine esecuzione
    avanza fino alla notizia più vecchia del sito rimasta senza esito. Aggiunta all'ADR
    [0011](../adr/0011-raccolta-incrementale-dei-siti.md). Se le esecuzioni vere mostrano siti
    trattenuti a lungo, si passa all'elenco di notizie in attesa nel database.
35. **`avvio_sistema.py`, bot e servizio** (14 nov 2026, domanda 8): **restano come sono**; i test
    T-32, T-33 e T-36…T-40 passano al gruppo "quando capita".

Non chiesta: la proposta P-3 (le metriche salvate cambiano solo per aggiunta) resta una proposta.

## Decisioni sulla fase 4, debugging (15 novembre 2026)

36. **Video YouTube e sponsorizzati** (15 nov 2026, domanda 1): l'esclusione "sponsorizzati e
    offerte" **non si applica più ai video** (tipi video e short), che passano alla valutazione.
    Per arXiv e per i siti resta com'è. Corregge il difetto S-01 (decisione 13). Va precisato il
    testo di `WEB-23`. *Costo*: ogni video in più passa dalla valutazione (stima della 6b: 7-29
    mila token l'uno).
37. **Margine di rilettura nella raccolta incrementale** (15 nov 2026, domanda 2): **no, niente
    margine**. L'ADR 0011 resta com'è. *Rischio accettato*: un sito con il feed in ritardo di
    qualche ora rispetto alla pubblicazione (caso redhotcyber) perde parte degli articoli senza
    che lo stato del sito lo dica (nella prova del revisore: 12 su 41 con 12 ore di ritardo).
    Annotato nell'ADR 0011.
38. **Altre prove con l'LLM sui video** (15 nov 2026, domanda 3): **no**.
39. **Indirizzi della rete di casa** (15 nov 2026, domanda 4): si controllano **solo i redirect**
    (compreso quello di robots.txt, S-32); il controllo dei nomi di dominio che puntano a
    indirizzi privati si riprende con la 6c.
40. **Rete che arriva tardi** (15 nov 2026, domanda 5): attesa della rete portata a **15 minuti**,
    e un'esecuzione fallita per mancanza di rete **non conta** per il recupero del giorno (il
    recupero scatta comunque solo a un nuovo avvio del servizio). Precisa `ESE-01`.
41. **`/pausa` e `/riprendi`** (15 nov 2026, domanda 6): restano come oggi (i comandi mandati a PC
    spento si scartano; `/riprendi` dopo l'orario non recupera l'esecuzione saltata), **scritto
    nella risposta del bot e nell'Aiuto**.
42. **Migrazione fallita** (15 nov 2026, domanda 7): **nessun ripristino automatico**: la copia
    pulita non va mai sovrascritta e l'errore dice quale file usare.
43. **`gradiens aggiorna`** (15 nov 2026, domanda 8): se dopo l'aggiornamento il servizio non
    riparte, **resta spento e lo dice**, con il percorso dei log.

## Decisioni sulla fase 5, dipendenze e stile (15 novembre 2026)

44. **Aggiornamenti di Claude Code** (15 nov 2026, domanda 1): canale **`stable`**. È
    un'impostazione di Claude Code dell'utente, fuori dalla repository: la cambia l'utente, non
    Gradiens. Vale anche per l'uso interattivo.
45. **Prova di fumo di Claude Code** (15 nov 2026, domanda 2): **sì**: una chiamata breve (stima:
    1.300-2.000 token) ogni volta che Gradiens rileva che la versione di Claude Code è cambiata,
    con segnalazione in Home e su Telegram se fallisce. Da implementare insieme alla registrazione
    della versione a ogni esecuzione.
46. **yt-dlp e runtime JavaScript** (15 nov 2026, domanda 3): **prova vera autorizzata** su un
    canale seguito (poche richieste a YouTube, nessuna quota LLM); l'aggiunta del runtime (6
    pacchetti nuovi, tra cui Deno) si decide con il risultato della prova.
47. **Formatter** (15 nov 2026, domanda 4): **dopo i refactoring**, una cartella alla volta. Ruff
    come linter entra subito, come dipendenza di sviluppo.
48. **Avvisi come errori nei test** (15 nov 2026, domanda 5): **sì, dopo la pulizia** delle
    connessioni non chiuse (che deve coprire anche i motori creati dentro i test).
49. **Aggiornamenti delle librerie** (15 nov 2026, domanda 6): **a mano, una volta al mese**, un
    pacchetto alla volta; niente Dependabot né Renovate.

## Intervista per la proposta 6c (15 novembre 2026)

50. **Chi accede alla dashboard da fuori casa** (15 nov 2026): **solo l'utente, dai suoi
    dispositivi** (telefono e portatile, su cui può installare un'app). Nessun accesso per altre
    persone né indirizzo pubblico.
51. **Dominio** (15 nov 2026): l'utente **non ha** un nome di dominio suo.
52. **Tailscale** (15 nov 2026, verificato sulla macchina, non chiesto): è **già installato e
    attivo** su questa macchina Linux, con il PC Windows nella stessa rete privata.

## Decisioni sulla proposta 6c (15-16 novembre 2026)

53. **Accesso da fuori casa** (domanda D1): **sì, con Tailscale Serve**. Gradiens resta in ascolto
    solo sul PC; niente tunnel pubblici.
54. **Certificati HTTPS della rete privata** (domanda D2): **sì**, dopo aver controllato (ed
    eventualmente cambiato) il nome della macchina in Tailscale, perché finisce in un registro
    pubblico dei certificati.
55. **Versione** (domanda D3): **completa**: oltre al nome della macchina nel `.env` e alle
    correzioni di sicurezza, una sezione "Accesso da fuori casa" nelle Impostazioni e un link al
    resoconto nel messaggio Telegram. Cambia la decisione 51 dell'intervista sui requisiti (niente
    link alla dashboard su Telegram) e `TG-03`.
56. **Azioni solo dal PC** (domande D4 e D4 bis): oltre alla base (spegnimento, avvio
    all'accensione, icone, cambio di bot o chat Telegram) anche **togliere i cuori, eliminare
    interessi e fonti, alzare i tetti**. Da remoto: leggere, mettere il cuore, avviare
    un'esecuzione, aggiungere fonti e interessi. *Rischio che resta*: un dispositivo della rete
    privata in mani altrui può leggere tutto e avviare esecuzioni.
57. **`AMB-01` e ADR 0001** (domanda D5): **aggiornati** il 15 nov 2026: il requisito dice che
    l'installazione di tutti i giorni è il portatile Linux, l'ADR 0001 ha una nota in fondo.

ADR: [0013](../adr/0013-dashboard-da-fuori-casa-con-tailscale-serve.md), implementato il 17 nov 2026 con
`AMB-02`, `TG-03` e `struttura.md` aggiornati. Comprende le correzioni della rilettura di sicurezza: una
seconda porta locale per Serve, le intestazioni contro l'incorniciamento e il controllo degli indirizzi
aggiunti a mano (che chiude il punto rimandato dalla decisione 39).

## Implementazione dell'ADR 0012 (17 novembre 2026)

58. **Aiuto dell'LLM al profilo di un sito** (17 nov 2026, piano proposto prima del codice): si implementa
    **subito**, prima delle proposte 6a-4, 6a-7 e 6a-9 che l'ADR 0012 e la scheda 6a-12 mettevano prima. Il tetto
    di 10.000 token vale **per ogni richiesta** (ogni clic sul bottone), non come totale per sito. L'LLM propone
    **solo sezioni ed esclusioni**, come dice l'ADR: la "forma degli indirizzi degli articoli" della scheda 6a-12 resta
    fuori, perché il profilo non ha un campo per salvarla e servirebbe toccare la strategia HTML.

## Altre decisioni dell'implementazione (17 novembre 2026)

Prese nelle conversazioni dei singoli pezzi e scritte allora solo negli ADR o nel [README.md](README.md); riportate
qui nella rilettura finale del 17 novembre 2026, senza cambiarle.

59. **Colonne della raccolta incrementale**: la migrazione `0013` aggiunge solo `coperto_fino_a` e `coperto_con`;
    niente colonne per le statistiche di raccolta, che nessun codice leggerebbe ancora
    ([ADR 0011](../adr/0011-raccolta-incrementale-dei-siti.md)).
60. **Feed e sitemap a ogni esecuzione**: un sito che pubblica poco, nelle esecuzioni senza articoli nuovi, legge
    anche la strategia dopo il feed (una richiesta in più, nessuna quota LLM). Fermarsi al feed farebbe perdere in
    silenzio gli articoli di un feed in ritardo. Compromesso accettato (ADR 0011).
61. **Prova di funzionamento di Claude Code fallita**: l'esecuzione si ferma come "fallita" con il motivo, e la prova
    si ripete all'esecuzione successiva (decisione 45, sezione 4.5 di
    [05-dipendenze-e-stile.md](05-dipendenze-e-stile.md)). Autorizzata e fatta una prova vera, fuori
    dall'esecutore: 1.764 token.
62. **Identità di Tailscale obbligatoria**: la porta per Tailscale Serve rifiuta le richieste senza
    `Tailscale-User-Login`, che manca nel traffico di Funnel. *Rischio*: se una versione di Serve non la mandasse
    più, l'accesso da fuori casa si fermerebbe ([ADR 0013](../adr/0013-dashboard-da-fuori-casa-con-tailscale-serve.md)).

## Decisioni dopo il refactoring (17 novembre 2026)

63. **"copertura parziale" non è un problema** (17 nov 2026, l'utente ha lasciato la scelta a Claude): lo stato
    entra in `STATI_BUONI` (`dati/esecuzioni.py`). Non dà segnali nelle Impostazioni e non compare tra i problemi in
    Telegram e nella CLI; in Impostazioni > Siti è grigio e la riga non è evidenziata; nel resoconto è verde, come
    "nessun articolo nuovo". *Perché*: per `WEB-26` e l'ADR 0011 non è un guasto, e il caso analogo del tetto arXiv
    raggiunto non si segnala. L'alternativa scartata ("visibile ma non rosso", come "profilo rigenerato") toccava
    più punti e avrebbe mostrato una "novità" che non lo è. *Rischio accettato*: un sito che raggiunge spesso il
    tetto si nota solo guardando la sezione Siti o il resoconto (la pagina Aiuto suggerisce di alzare i tetti).
    Test: T-08 (`tests/dashboard/test_stati_dei_siti.py`).
64. **Formatter** (17 nov 2026, attua la decisione 47): `ruff format` con lo stile predefinito (virgolette doppie,
    come già tutto il codice) e `line-length = 120`; migrazioni escluse. E501 entra nel linter: le 28 righe lunghe
    che il formatter non spezza (stringhe, commenti, docstring) sono state spezzate a mano. `ruff format --check` in
    CI, su Windows e Linux. Un commit per cartella e proprietario, elencati in `.git-blame-ignore-revs`.
65. **`except A, B:` senza parentesi** (17 nov 2026): si accetta la forma di Python 3.14 (PEP 758) che il formatter
    scrive da solo; il comportamento è identico. *Rischio accettato*: somiglia alla sintassi di Python 2 e non gira
    sotto Python 3.14, che è già il minimo (`requires-python`). L'alternativa (`target-version = "py313"`) avrebbe
    tolto anche al linter le regole della sintassi nuova.
