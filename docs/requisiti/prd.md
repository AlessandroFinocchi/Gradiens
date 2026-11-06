# Gradiens – Documento dei requisiti (PRD)

Versione 1.3 del 6 novembre 2026. Questo documento riunisce in un unico testo il [prompt originale](prompt-originale.md) e le 40 decisioni del [registro dell'intervista](decisioni-intervista.md). Se c'è un contrasto con il prompt originale, vale questo documento. I termini in grassetto sono definiti in [CONTEXT.md](../../CONTEXT.md).

Ogni requisito ha un codice (es. `ESE-03`). I test e le verifiche citano questi codici.

## 1. Scopo

Gradiens è un'applicazione personale, con un solo utente. Raccoglie contenuti da YouTube, arXiv e siti web, li filtra con un LLM in base agli **interessi** dell'utente e li riassume in italiano, così che le notizie si possano leggere velocemente e già filtrate.

## 2. Ambiente

- `AMB-01` L'applicazione gira sul PC di casa (Windows 11, RTX 3070 8 GB). Da fuori casa si raggiunge tramite Tailscale. Vedi [ADR 0001](../adr/0001-esecuzione-sul-pc-di-casa.md).
- `AMB-02` L'applicazione non è esposta su internet: è raggiungibile solo dalla rete locale e da Tailscale.
- `AMB-03` Il codice non usa dipendenze specifiche di Windows, così si può spostare su un server. Fa eccezione solo la registrazione dell'avvio all'accensione (`AMB-04`).
- `AMB-04` Nelle Impostazioni un interruttore decide come si avvia Gradiens:
  - **all'accensione del PC**: parte da solo, senza bisogno di accedere a Windows né di accendere il monitor. Basta accendere il PC e lanciare l'esecuzione dal bot Telegram;
  - **a mano**, con `gradiens avvia`. È il valore predefinito.

  Quando l'interruttore viene disattivato, la registrazione nel sistema operativo viene rimossa. Cambiare l'interruttore richiede una conferma di amministratore sullo schermo del PC, quindi si fa stando al PC e non da remoto (vedi [ADR 0005](../adr/0005-avvio-all-accensione-con-attivita-pianificata.md)).

## 3. Interessi

- `INT-01` Un **interesse** ha un nome, usato nei filtri, una descrizione scritta dall'utente e un **raffinamento** facoltativo. Il filtro LLM usa insieme la descrizione e il raffinamento.
- `INT-02` Dalle Impostazioni l'utente aggiunge, modifica, rinomina ed elimina gli interessi. Deve sempre esistere almeno un interesse.
- `INT-03` Il filtro funziona qualunque sia la lingua della notizia e qualunque sia la lingua in cui è scritto l'interesse.
- `INT-04` **Raffinamento**:
  - Alla fine di un'esecuzione, per ogni interesse che ha almeno 3 nuove notizie con il **cuore** dall'ultima proposta, l'LLM aggrega quelle notizie e genera una **proposta di raffinamento**.
  - La proposta compare nelle Impostazioni con le modifiche evidenziate. L'utente la approva, la modifica o la scarta.
  - La descrizione scritta dall'utente non viene mai modificata dall'LLM.
- `INT-05` L'utente può modificare o azzerare a mano il raffinamento in qualsiasi momento.
- `INT-06` Se ci sono notizie con il cuore che non corrispondono a nessun interesse, l'LLM propone un nuovo interesse. Anche questa proposta va approvata dall'utente.
- `INT-07` Questi eventi fanno rivalutare all'inizio dell'esecuzione successiva tutte le notizie conservate degli ultimi 7 giorni:
  - si aggiunge un interesse;
  - si modifica la descrizione di un interesse;
  - si modifica un raffinamento, a mano o approvando una proposta.

  Le notizie scartate in passato non vengono recuperate.
- `INT-08` Rinominare un interesse ne cambia solo l'etichetta.
- `INT-09` Eliminare un interesse cancella i suoi punteggi di **pertinenza**:
  - le notizie che non hanno più nessun punteggio sopra la soglia escono dalla pagina Notizie;
  - le notizie in archivio restano, con l'etichetta "interesse eliminato".

## 4. Fonti

### 4.1 YouTube

- `YT-01` L'utente aggiunge un canale incollando un suo indirizzo qualsiasi (`@nome`, `/channel/ID` o il link di un video). L'applicazione ricava il canale da sola.
- `YT-02` Vengono raccolti i video nuovi dei canali configurati. Gli **Short** sono inclusi e sono un tipo di notizia distinto dal video normale.
- `YT-03` Valgono come trascrizione anche i sottotitoli generati automaticamente da YouTube.
- `YT-04` Le dirette e le anteprime si elaborano solo quando sono disponibili, cioè dopo la trasmissione.
- `YT-05` I video senza trascrizione:
  - non vengono valutati e non diventano notizie;
  - compaiono solo nel resoconto dell'esecuzione, canale per canale, con lo stato "trascrizione assente" (o un altro problema, se è diverso) e il link al video.

### 4.2 arXiv

- `ARX-01` L'utente sceglie le categorie arXiv nelle Impostazioni (es. `cs.CR`, `cs.AI`). Deve esserci almeno una categoria.
- `ARX-02` Tutti i paper nuovi delle categorie scelte passano dal pre-filtro.
- `ARX-03` Un tetto configurabile limita il numero di paper elaborati per esecuzione. Se il tetto viene superato si elaborano i paper più recenti e il resoconto segnala "tetto raggiunto".

### 4.3 Siti web

**Aggiunta e profilo**

- `WEB-01` Per aggiungere un sito basta il suo indirizzo, senza configurazioni scritte apposta per quel sito. L'indirizzo può essere la home page o una sezione.
- `WEB-02` All'aggiunta, l'applicazione analizza il sito una volta e salva un **profilo del sito** che contiene:
  - perimetro;
  - feed;
  - sitemap;
  - sezioni;
  - piattaforma riconosciuta;
  - dove si trova la data degli articoli;
  - strategia scelta.

  L'utente vede un'anteprima degli articoli che il sito produrrebbe.
- `WEB-03` Nelle Impostazioni il profilo è visibile e modificabile. L'utente può:
  - includere o escludere sezioni e feed;
  - aggiungere a mano un feed o una sezione;
  - impostare limiti di pagine e di articoli.
- `WEB-04` L'LLM può intervenire solo durante la creazione del profilo, per esempio per riconoscere l'elenco degli articoli quando le euristiche falliscono. Le esecuzioni usano le regole salvate e non consumano token per la scoperta.
- `WEB-05` Lo scraping è sempre fatto dal codice dell'applicazione e non viene mai affidato agli strumenti di navigazione di un provider LLM.

**Perimetro**

- `WEB-06` Se l'indirizzo è una home page, il perimetro è l'intero dominio, sottodomini compresi.
- `WEB-07` I domini esterni trovati durante l'analisi compaiono nel profilo come "siti collegati", disattivati. L'utente li può attivare.
- `WEB-08` Un feed ospitato su un altro dominio (feedburner, Substack) si usa per trovare gli articoli, se il sito lo collega, ma non allarga il perimetro.
- `WEB-09` Se l'indirizzo è una sezione, l'esplorazione resta dentro la sezione: le sue pagine successive e le sue sottosezioni, senza sottodomini. Gli articoli che la sezione elenca valgono anche se il loro indirizzo è fuori dal percorso della sezione (casi e3rehab, ACN).

**Scoperta degli articoli**

- `WEB-10` La scoperta procede a cascata, dalla strategia più affidabile ed economica alla più costosa, e combina i risultati:
  1. feed RSS/Atom (dai tag `rel="alternate"`, dai link nella pagina e dai percorsi comuni);
  2. sitemap (da robots.txt e dai percorsi comuni, news sitemap comprese);
  3. API della piattaforma (es. l'API REST di WordPress);
  4. esplorazione controllata dell'HTML statico (menu, sezioni, paginazione) con profondità limitata, che si ferma quando gli articoli diventano più vecchi della finestra di raccolta.
- `WEB-11` La cascata gestisce questi casi, emersi dalla [verifica dei siti](verifica-siti-esempio-2026-11-02.md):
  - un feed che risponde con HTML non è un feed;
  - i feed possono stare su altri domini o sottodomini, e i loro indirizzi possono non avere il protocollo (`//host/…`);
  - gli elementi di un feed possono non essere in ordine di data;
  - la pagina di partenza può non contenere tutti gli articoli della finestra.
- `WEB-12` Le strategie di scoperta e di estrazione sono moduli intercambiabili. Si possono aggiungere nuove piattaforme o adattatori per un singolo sito senza toccare il resto.
- `WEB-13` La prima versione non ha un browser headless. Un sito che mostra i contenuti solo tramite JavaScript riceve lo stato "richiede JavaScript", con il suggerimento di inserire a mano l'indirizzo di un feed.

**Estrazione e date**

- `WEB-14` Il testo principale si estrae con una libreria di tipo readability. Titolo, autore, data e sezione si prendono dai metadati della pagina (JSON-LD, Open Graph, `<time>`).
- `WEB-15` La data di pubblicazione si cerca in quest'ordine: feed o sitemap, metadati della pagina, URL, data relativa nell'elenco (es. "2 giorni fa"). Se non si trova, la notizia riceve lo stato "data incerta".
- `WEB-16` Le pagine si leggono correttamente qualunque sia la codifica (es. ISO-8859-1) e la lingua.

**Scraping rispettoso**

- `WEB-17` Il robots.txt si controlla prima di qualsiasi altra richiesta al sito, comprese quelle all'API della piattaforma.
- `WEB-18` Ogni dominio ha un limite di richieste, con pause tra una e l'altra. Le richieste usano uno User-Agent identificabile ma generico, senza dati personali. Sono previsti timeout, nuovi tentativi e cache HTTP (ETag e Last-Modified).
- `WEB-19` A ogni esecuzione ogni sito ha un tetto di pagine e un tetto di articoli.
- `WEB-20` Paywall, captcha e protezioni anti-bot non si aggirano. Si usa ciò che è pubblico, si cerca un canale ufficiale alternativo (es. il feed RSS dell'ACN) oppure si segnala il limite.

**Esclusioni**

- `WEB-21` Le offerte commerciali si escludono nel profilo, escludendo la sezione o il percorso. All'analisi del sito l'applicazione propone già come escluse le sezioni commerciali.
- `WEB-22` I contenuti sponsorizzati mescolati agli articoli li riconosce il pre-filtro LLM.
- `WEB-23` Nelle Impostazioni ci sono due interruttori globali, entrambi attivi per default: "Escludi contenuti sponsorizzati e offerte" ed "Escludi articoli a pagamento". Se il secondo è disattivo, gli articoli a pagamento vengono mostrati con il riassunto della parte pubblica e lo stato "contenuto parziale (paywall)".

**Rigenerazione e stati**

- `WEB-24` Il profilo si rigenera in automatico solo dopo guasti veri per 3 esecuzioni di fila. Sono guasti veri:
  - un feed che risponde con un errore (es. 404) o con HTML;
  - un errore di lettura;
  - un feed fermo mentre la sitemap mostra articoli più recenti.

  "Zero articoli nuovi", da solo, non fa mai scattare la rigenerazione.
- `WEB-25` Dopo la rigenerazione il sito ha lo stato "profilo rigenerato" e si vedono le differenze rispetto al profilo precedente. La rigenerazione conserva le modifiche manuali dell'utente. Un feed aggiunto a mano che smette di funzionare viene segnalato ma non rimosso. Nelle Impostazioni un bottone permette di rigenerare il profilo a mano.
- `WEB-26` Ogni sito ha uno stato visibile, per esempio:
  - "ok";
  - "nessun articolo nuovo", che è un esito normale e non un errore;
  - "accesso bloccato";
  - "richiede JavaScript";
  - "profilo rigenerato";
  - "nessuna strategia funzionante".

  Ogni notizia ha uno stato visibile, per esempio "ok", "data incerta", "contenuto parziale (paywall)", "errore di estrazione".

### 4.4 Duplicati

- `DUP-01` Gli indirizzi si normalizzano: si usa l'indirizzo canonico e si tolgono i parametri di tracciamento. Un registro delle notizie già viste impedisce di rielaborare la stessa notizia.
- `DUP-02` Se un articolo incorpora o linka un video YouTube già raccolto, articolo e video diventano una notizia sola con il link "disponibile anche su…". Come contenuto principale si tiene quello con la trascrizione o il testo più completo.
- `DUP-03` Notizie diverse sullo stesso evento non sono duplicati: restano separate e vanno nello stesso **argomento**.

## 5. Esecuzione

**Avvio**

- `ESE-01` Un'**esecuzione** si avvia in quattro modi:
  - dal bottone in dashboard;
  - dalla CLI;
  - dal comando `/aggiorna` del bot Telegram;
  - dalla programmazione giornaliera, il cui orario si configura nelle Impostazioni. La programmazione la gestisce l'applicazione stessa mentre è in funzione, e si può mettere in pausa (`TG-10`).
- `ESE-02` Gira una sola esecuzione alla volta. Se ne viene richiesta un'altra mentre una è in corso, la richiesta viene rifiutata con il messaggio "esecuzione già in corso".

**Raccolta e filtro**

- `ESE-03` Si raccolgono solo le notizie pubblicate nella **finestra di raccolta**, che si configura nelle Impostazioni da 1 a 7 giorni (valore predefinito 7). Per le notizie con data incerta conta la data di scoperta.
- `ESE-04` **Pre-filtro**: l'LLM legge a blocchi titolo e sommario delle notizie nuove e scarta quelle fuori tema e quelle escluse (vedi `WEB-22` e `WEB-23`).
- `ESE-05` **Valutazione completa**: per le notizie che passano il pre-filtro si scarica il testo completo o la trascrizione. L'LLM assegna un punteggio di pertinenza da 0 a 100 per ogni interesse pertinente, quindi una notizia può corrispondere a più interessi. Nella stessa fase l'LLM:
  - scrive il riassunto in italiano. Il riassunto deve essere corretto e completo: riporta solo ciò che c'è nel contenuto, senza aggiunte, e ne copre tutti i punti principali, non solo l'inizio. Se il contenuto è parziale, il riassunto lo dice;
  - traduce il titolo in italiano, se la notizia è in un'altra lingua;
  - assegna la notizia a un argomento, oppure a nessuno.
- `ESE-06` Una notizia viene mostrata se almeno uno dei suoi punteggi supera la soglia. La soglia si configura nelle Impostazioni e per default vale 60.
- `ESE-07` Delle notizie scartate si conserva solo l'indirizzo, nel registro delle notizie già viste.

**Argomenti**

- `ESE-08` L'LLM assegna ogni notizia mostrata a un argomento esistente, oppure ne crea uno nuovo, oppure non le assegna nessun argomento. Una notizia appartiene al massimo a un argomento. Un argomento è un singolo evento e la sua evoluzione, non un tema generale.

**Cancellazione delle notizie**

- `ESE-09` All'inizio di ogni esecuzione, e comunque almeno una volta al giorno, si cancellano le notizie più vecchie di 7 giorni che non sono in **archivio**. Il limite resta di 7 giorni qualunque sia la finestra di raccolta, quindi fuori dall'archivio non compaiono mai notizie più vecchie di 7 giorni. Per le notizie con data incerta conta la data di scoperta.
- `ESE-10` Un argomento che resta senza notizie viene cancellato.

**Metriche e interruzione**

- `ESE-11` Ogni esecuzione registra le metriche, divise per tipo di fonte:
  - durata;
  - notizie esaminate (quelle nuove nella finestra di raccolta);
  - scartate dal pre-filtro;
  - scartate dalla valutazione;
  - escluse;
  - mostrate;
  - errori;
  - token usati e costo stimato in dollari, divisi per ruolo. Per Claude Code e per i modelli locali si mostrano solo i token, perché non hanno un costo a consumo.

  Non c'è nessun tetto di spesa.
- `ESE-12` Se l'applicazione viene spenta durante un'esecuzione, l'esecuzione viene segnata come "interrotta". Ciò che è già stato elaborato si conserva, e le notizie rimaste si riprendono all'esecuzione successiva, se sono ancora nella finestra.
- `ESE-13` Un'esecuzione fallita viene segnalata con il suo motivo, nella dashboard e su Telegram.

## 6. Provider LLM

- `LLM-01` I provider LLM sono intercambiabili, dietro un'unica interfaccia. Aggiungere un provider (es. Gemini) non richiede modifiche al resto dell'applicazione.
- `LLM-02` La prima versione supporta tre provider:
  - **Claude Code**, che è il default: l'app usa la modalità senza interfaccia (`claude -p`) di Claude Code, già installato sul PC e collegato all'account dell'utente. Le chiamate consumano la quota del suo abbonamento (es. Pro), senza costi aggiuntivi. Vedi [ADR 0006](../adr/0006-claude-code-come-provider-predefinito.md);
  - **API di Claude**, con una chiave a pagamento, in alternativa;
  - un collegamento compatibile con l'API di OpenAI, che copre i modelli locali (Ollama, LM Studio).
- `LLM-03` Nelle Impostazioni si scelgono provider e modello separatamente per due ruoli:
  - **pre-filtro**;
  - **elaborazione**, che comprende valutazione completa, riassunto, argomento, proposte di raffinamento e analisi del profilo dei siti.

  Il default di entrambi i ruoli è Claude Code con un modello economico (Haiku). Per il pre-filtro, che fa più chiamate, si può scegliere un modello locale per risparmiare quota dell'abbonamento.
- `LLM-04` La configurazione di ChatGPT e di Gemini è fuori dalla prima versione.
- `LLM-05` Con Claude Code ogni chiamata è isolata: niente strumenti, niente server MCP, niente conversazioni salvate. Il modello riceve solo il testo da valutare e risponde nel formato richiesto.
- `LLM-06` Se la quota dell'abbonamento si esaurisce durante un'esecuzione, l'esecuzione si ferma con lo stato "interrotta" e il motivo "quota dell'abbonamento esaurita", con l'orario in cui torna disponibile se Claude Code lo indica. Ciò che è già elaborato si conserva, e le notizie rimaste si riprendono all'esecuzione successiva, come in `ESE-12`.

## 7. Telegram

- `TG-01` Telegram è obbligatorio. Il bot si collega nella configurazione iniziale, seguendo un tutorial passo dopo passo:
  1. aprire @BotFather in Telegram, creare il bot con `/newbot` e scegliere nome e username;
  2. copiare il token del bot nell'app, che verifica subito che il token funzioni;
  3. mandare `/start` al proprio bot. L'app rileva la chat, ne mostra il nome e chiede di confermarla come unica chat autorizzata.

  Alla fine l'app registra l'elenco dei comandi presso Telegram, così compaiono nel menu del bot.
- `TG-02` Il bot risponde solo alla chat configurata e ignora tutti gli altri messaggi.
- `TG-03` Alla fine di ogni esecuzione il bot manda un messaggio che contiene:
  - per ogni tipo di fonte (arXiv, YouTube, siti web), le 3 notizie con la pertinenza più alta, ciascuna con titolo in italiano, fonte, interesse con il suo punteggio, una o due frasi di riassunto e link;
  - una riga di metriche: esaminate, mostrate, durata, errori, costo (o token, per Claude Code e i modelli locali);
  - il link alla dashboard tramite l'indirizzo Tailscale.
- `TG-04` Se un tipo di fonte ha meno di 3 notizie si mostrano quelle presenti. Se non ne ha nessuna, il messaggio dice "nessuna notizia nuova".
- `TG-05` Al comando `/aggiorna` il bot risponde "esecuzione avviata" oppure "esecuzione già in corso".
- `TG-06` Il comando `/help` elenca tutti i comandi del bot e spiega cosa fa ciascuno.
- `TG-07` Il comando `/stato` mostra le stesse informazioni di `gradiens stato` (`CLI-03`):
  - l'esecuzione in corso con il suo avanzamento, oppure l'ultima conclusa con la riga di metriche di `TG-03`;
  - la prossima esecuzione programmata, oppure "programmazione in pausa" (vedi `TG-10`).
- `TG-08` Il comando `/ultima` rimanda il messaggio di fine dell'ultima esecuzione conclusa (`TG-03`). Se non c'è ancora nessuna esecuzione, il bot risponde "nessuna esecuzione ancora".
- `TG-09` Sotto ogni notizia del messaggio di `TG-03` c'è un bottone ❤️ che mette o toglie il cuore, con lo stesso effetto del cuore in dashboard (`UI-05`). Il bottone mostra se il cuore è già messo. Se la notizia è già stata cancellata, il bot risponde "notizia non più disponibile".
- `TG-10` I comandi `/pausa` e `/riprendi` sospendono e riattivano l'esecuzione programmata giornaliera. Durante la pausa le esecuzioni avviate a mano funzionano normalmente. La pausa resta attiva anche dopo un riavvio, si vede in Home e si può togliere anche dalle Impostazioni.

## 8. Dashboard

Tutta l'interfaccia è in italiano. L'applicazione si usa interamente dalla dashboard. Tutta la dashboard segue lo stile delle app Claude, con tema chiaro e scuro e notizie mostrate come elenco compatto (variante 2 di [mockup/00-confronto-stili.html](../../mockup/00-confronto-stili.html)).

- `UI-01` **Sidebar**: mostra sempre le icone di tutte le pagine. Quando ci si passa sopra con il puntatore, o la si raggiunge con la tastiera, si espande sopra il contenuto e mostra anche i nomi. In alto ci sono le pagine Home, Notizie, Timeline e Archivio, in quest'ordine. In basso, separate, ci sono Aiuto e, sotto, l'icona a ingranaggio delle Impostazioni. L'ingranaggio mostra un segnale quando almeno una sezione delle Impostazioni ne ha uno (`UI-10`).
- `UI-02` **Home**, organizzata in quattro blocchi:
  1. ultima esecuzione, con ora di avvio, durata, metriche, errori, bottone "Avvia esecuzione" e avanzamento se un'esecuzione è in corso; prossima esecuzione programmata, oppure "programmazione in pausa";
  2. "In evidenza", con le 3 notizie a pertinenza più alta per ogni tipo di fonte;
  3. avvisi: proposte di raffinamento da approvare, siti in stato di errore, argomenti con notizie nuove;
  4. storico delle esecuzioni.

  Non c'è un digest scritto dall'LLM.
- `UI-03` **Resoconto di un'esecuzione**, che si apre dallo storico. Contiene:
  - le metriche divise per tipo di fonte;
  - lo stato di ogni sito e di ogni canale;
  - i video senza trascrizione;
  - le notizie escluse;
  - la segnalazione del tetto arXiv, se è stato raggiunto.
- `UI-04` **Pagina Notizie**: è l'elenco di tutte le notizie. Mostra le notizie degli ultimi 7 giorni che superano la soglia. Per ogni notizia mostra:
  - titolo originale, e la traduzione italiana se la notizia è in un'altra lingua;
  - fonte, tipo e data;
  - interessi con il loro punteggio;
  - argomento;
  - stato;
  - riassunto, tagliato a due righe;
  - link.

  Da qui si avvia un'esecuzione con un bottone. Cliccando una notizia si apre la pagina della notizia specifica (`UI-13`).
- `UI-05` Il **cuore** mette una notizia in archivio e contribuisce al raffinamento degli interessi. Se si toglie il cuore, la notizia torna alla regola dei 7 giorni.
- `UI-06` **Filtri** della pagina Notizie:
  - tipo: arXiv, sito, video YT, short YT;
  - interesse;
  - data;
  - fonte;
  - cuore.

  Dentro lo stesso filtro i valori si combinano in OR, filtri diversi si combinano in AND.
- `UI-07` **Ordinamento** della pagina Notizie, con verso invertibile, per due criteri:
  - pertinenza, che è il default: conta il punteggio più alto, oppure quello dell'interesse filtrato;
  - data di pubblicazione: per le notizie con data incerta conta la data di scoperta.
- `UI-08` **Archivio**: tutte le notizie con il cuore. Non vengono mai cancellate e hanno gli stessi filtri e ordinamenti della pagina Notizie.
- `UI-09` **Timeline**:
  - è un elenco compatto di argomenti: per ognuno mostra solo il nome, i metadati (numero di notizie, periodo, ultimo aggiornamento, notizie in archivio, notizie arrivate con l'ultima esecuzione) e i bottoni per rinominare, unire ed eliminare;
  - compaiono solo gli argomenti con almeno 2 notizie, prima quelli aggiornati più di recente;
  - cliccando un argomento si apre la **pagina dell'argomento**, con un indirizzo proprio, che mostra tutte le sue notizie in ordine di tempo, cioè quelle degli ultimi 7 giorni e quelle in archivio. Ogni notizia apre la pagina della notizia specifica (`UI-13`). Anche qui si può rinominare, unire ed eliminare l'argomento.
- `UI-10` **Impostazioni**: si aprono dall'ingranaggio come finestra sopra la pagina corrente, nello stile delle impostazioni delle app Claude, e si chiudono con la X o con Esc. Sul telefono occupano tutto lo schermo. A sinistra c'è l'elenco delle sezioni, ognuna con la sua icona; a destra il contenuto della sezione scelta. Le sezioni sono:
  - **Interessi**: interessi con raffinamenti e proposte da approvare;
  - **Canali YouTube**;
  - **Siti web**, con il loro profilo;
  - **arXiv**: categorie e tetto di paper;
  - **Modelli LLM**: provider e modello per i due ruoli, stato di Claude Code, chiavi API;
  - **Esecuzione**: soglia di pertinenza, finestra di raccolta (da 1 a 7 giorni), interruttori di esclusione, orario dell'esecuzione programmata e sua pausa;
  - **Avvio**: all'accensione o a mano;
  - **Telegram**;
  - **Aspetto**: tema chiaro, scuro oppure come il sistema operativo, che è il valore predefinito.

  Le Impostazioni si possono aprire direttamente su una sezione, per esempio da un avviso della Home.
- `UI-14` **Segnali delle sezioni delle Impostazioni**: a destra del nome di una sezione compare un'icona quando la sezione richiede attenzione. Passandoci sopra si legge il motivo, e dentro la sezione è evidenziata la voce interessata. Ci sono due tipi di segnale:
  - **avvertimento** (triangolo), per problemi e dati mancanti:
    - Interessi, Canali YouTube, Siti web, arXiv: dati obbligatori mancanti (`UI-11`);
    - Canali YouTube: un canale non è più raggiungibile;
    - Siti web: un sito è in stato di errore ("accesso bloccato", "richiede JavaScript", "nessuna strategia funzionante") oppure un feed aggiunto a mano ha smesso di funzionare;
    - Modelli LLM: Claude Code non installato, non collegato a un account o con la quota esaurita; chiave API mancante o rifiutata; modello locale non raggiungibile;
    - Telegram: bot non collegato o token non più valido;
    - Avvio: la registrazione dell'avvio all'accensione è fallita o non è più valida;
  - **novità** (pallino), per cose da guardare o approvare:
    - Interessi: proposte di raffinamento da approvare;
    - Siti web: un profilo è stato rigenerato e le differenze sono da guardare (`WEB-25`), oppure ci sono siti collegati proposti e non ancora attivati (`WEB-07`);
    - arXiv: nell'ultima esecuzione è stato raggiunto il tetto di paper;
    - Esecuzione: la programmazione è in pausa.

  Se una sezione ha entrambi i tipi di segnale, si mostra l'avvertimento. Il segnale sparisce da solo quando la causa viene risolta.
- `UI-11` **Configurazione iniziale**: si apre all'avvio se mancano dati obbligatori, e la dashboard non si usa finché non è completa. I dati obbligatori sono:
  - almeno un canale YouTube, un sito, un interesse e una categoria arXiv;
  - Claude Code installato e collegato a un account, se è usato in almeno un ruolo; la chiave dell'API di Claude, se è usata in almeno un ruolo;
  - bot Telegram, collegato con il tutorial di `TG-01`.
- `UI-12` **Aiuto**: si apre dall'icona in basso nella sidebar. È una pagina statica che spiega come usare l'intera applicazione:
  - fonti e profili dei siti;
  - interessi e raffinamento;
  - il cuore;
  - argomenti;
  - stati;
  - avvio all'accensione;
  - comandi della CLI e di Telegram.
- `UI-13` **Pagina della notizia specifica**: ogni notizia ha una pagina sua, con un indirizzo proprio, che si apre da Notizie, Archivio e Timeline, anche in una nuova scheda del browser. Mostra per intero tutto ciò che l'elenco accorcia: titolo originale e traduzione, fonte, tipo, data, stato, riassunto completo, tutti gli interessi con il loro punteggio, argomento con il link alla pagina dell'argomento e cuore. Il testo integrale non viene salvato né mostrato: per leggerlo c'è un link ben visibile all'originale, che si apre in una nuova scheda.

## 9. CLI

- `CLI-01` `gradiens avvia` fa partire dashboard, programmazione giornaliera e bot Telegram. Se l'avvio all'accensione è attivo (`AMB-04`), il PC esegue questo passo da solo.
- `CLI-02` `gradiens esegui` lancia un'esecuzione, ne mostra l'avanzamento e alla fine stampa le metriche. Rispetta `ESE-02`.
- `CLI-03` `gradiens stato` mostra l'esecuzione in corso o l'ultima conclusa, e la prossima esecuzione programmata oppure "programmazione in pausa".
- `CLI-04` `gradiens spegni` termina l'applicazione (vedi `ESE-12`).

## 10. Persistenza e sicurezza

- `PER-01` Sopravvivono al riavvio dell'applicazione e del PC:
  - configurazione, compresa la pausa della programmazione;
  - interessi e raffinamenti;
  - profili dei siti;
  - archivio;
  - notizie degli ultimi 7 giorni;
  - argomenti;
  - registro delle notizie già viste;
  - storico delle esecuzioni.
- `PER-02` Tutto ciò che l'applicazione salva sta dentro la cartella della repository, in percorsi esclusi da git (`.gitignore`): configurazione, chiavi API e token (in `.env`), database, cache e log.
- `PER-03` L'applicazione non salva nulla fuori dalla cartella della repository. Le conseguenze sono due:
  - cancellando la cartella si cancella tutto ciò che riguarda l'app;
  - una copia scaricata da GitHub su un altro dispositivo parte senza configurazione e va configurata da capo.

  L'unica eccezione è la registrazione dell'avvio all'accensione nel sistema operativo (`AMB-04`). Claude Code, quando è usato come provider, tiene il login e i propri file nella sua cartella utente (`~/.claude`): sono file di Claude Code, non di Gradiens, e Gradiens non vi fa salvare conversazioni (`LLM-05`).
- `PER-04` Chiavi API e token non finiscono mai in file versionati, nel codice o nei log.

## 11. Fuori dalla prima versione

- Browser headless (Playwright): si potrà aggiungere come nuovo modulo di strategia (`WEB-13`).
- Configurazione di ChatGPT e di Gemini (`LLM-04`).
- Tetto di spesa LLM.
- Digest testuale in homepage.
- Lettura delle notizie da CLI.
- Ordinamenti diversi da pertinenza e data.

## 12. Criteri di accettazione

- `ACC-01` Per ciascuno dei 13 siti di esempio del prompt originale, l'applicazione deve fare una di queste due cose:
  - trovare gli articoli degli ultimi 7 giorni, anche quelli che non compaiono nella pagina indicata, oppure dare l'esito "nessun articolo nuovo" quando il sito non ha pubblicato nulla;
  - segnalare con uno stato chiaro perché non ci riesce e cosa può fare l'utente.
- `ACC-02` Un'esecuzione completa su tutte le fonti produce:
  - le notizie mostrate, con riassunto in italiano e punteggi;
  - il resoconto con tutte le metriche di `ESE-11`;
  - il messaggio Telegram di `TG-03`.
- `ACC-03` Se si avvia una seconda esecuzione mentre la prima è in corso, la richiesta viene rifiutata da tutti e quattro i canali di avvio (`ESE-02`).
- `ACC-04` Dopo un riavvio, i dati elencati in `PER-01` sono ancora presenti e invariati.
- `ACC-05` Una notizia non archiviata più vecchia di 7 giorni viene cancellata alla pulizia successiva. Una notizia archiviata non viene mai cancellata.
- `ACC-06` Dopo aver messo il cuore a 3 notizie dello stesso interesse, alla fine dell'esecuzione successiva compare una proposta di raffinamento. La descrizione dell'interesse resta invariata finché l'utente non approva.
- `ACC-07` Un messaggio al bot da una chat diversa da quella configurata non produce nessun effetto.
- `ACC-08` Nessuna chiave o token compare nei file tracciati da git.
- `ACC-09` Con l'avvio all'accensione attivo, si accende il PC senza accedere a Windows e si manda `/aggiorna` al bot: l'esecuzione parte e il messaggio di fine esecuzione arriva.
- `ACC-10` Dopo una configurazione completa e un'esecuzione, si verificano tre cose:
  - nessun file dell'app è stato scritto fuori dalla cartella della repository, salvo la registrazione di `AMB-04` e i file propri di Claude Code;
  - `git status` non mostra file di configurazione o di dati;
  - un clone nuovo della repository si apre sulla configurazione iniziale.
- `ACC-11` Con la finestra di raccolta impostata a N giorni, l'esecuzione non raccoglie notizie pubblicate prima di N giorni fa.
- `ACC-12` Premendo ❤️ su una notizia del messaggio Telegram, la notizia compare con il cuore nell'Archivio della dashboard. Premendolo di nuovo, il cuore viene tolto.
- `ACC-13` Dopo `/pausa`, all'orario programmato non parte nessuna esecuzione, anche dopo un riavvio, mentre `/aggiorna` funziona. Dopo `/riprendi` l'esecuzione programmata riparte.
- `ACC-14` Su un campione di 10 notizie di tipi diversi, confrontando il riassunto con l'originale: il riassunto non contiene affermazioni assenti nell'originale e ne copre i punti principali (verifica manuale).
- `ACC-15` Con Claude Code come provider, un'esecuzione completa non richiede nessuna chiave API e nel resoconto mostra i token senza costo. Se Claude Code non è collegato a un account, l'esecuzione non parte e la sezione Modelli LLM mostra l'avvertimento.
