# Argomenti tema – requisiti in lavorazione

Funzione nuova chiesta dall'utente il 27 novembre 2026. Qui si raccolgono le decisioni della fase 1
(requisiti), una domanda alla volta; a fase chiusa confluiscono nel PRD e in CONTEXT.md.

## Problema

Oggi un argomento è un singolo evento (`ESE-08`): le notizie su GTA 6 finiscono in argomenti diversi (uscita,
patch, trailer). Unirli in un argomento "GTA 6" sposta le notizie già trovate, ma le nuove non ci confluiscono
in modo affidabile, perché il prompt chiede all'LLM eventi precisi e gli mostra solo il nome degli argomenti.
In più un argomento rimasto senza notizie viene cancellato (`ESE-10`), e con lui la scelta dell'utente.

## Scelta

Tra "argomento marcato tema dall'utente" e "tema che contiene argomenti-evento" l'utente ha scelto il primo
(27 nov). Un argomento marcato come tema:
- sta nel prompt degli argomenti in un elenco a parte, con la regola "assegna qui ogni notizia che riguarda il
  tema, anche se è un evento preciso". Una notizia ha comunque un solo argomento, quindi il tema vince sull'evento;
- è sempre nell'elenco mandato all'LLM, anche oltre i 30 giorni e il limite di 100 (ADR 0008);
- non viene cancellato quando resta senza notizie.

## Decisioni

1. **Conservazione** (27 nov): le notizie di un tema seguono la regola dei 7 giorni (`ESE-09`), come tutte le
   altre. Il tema mostra l'ultima settimana e le notizie con il cuore; resta anche quando rimane vuoto.
2. **Creazione** (27 nov): in due modi. Da un argomento esistente, con un interruttore nella sua pagina; oppure
   da zero, con "Nuovo tema" nella Timeline, che chiede il nome (e la descrizione facoltativa, decisione 4): il tema esiste subito, vuoto, e l'LLM ci
   assegna le notizie dalla prossima esecuzione. Ne segue che la Timeline mostra i temi anche con meno di 2
   notizie, che per gli argomenti restano nascosti (`UI-09`).
3. **Posto nella Timeline** (27 nov): i temi stanno in una sezione "Temi" in cima, prima quelli aggiornati più
   di recente (un tema vuoto per ultimo), con il bottone "Nuovo tema"; sotto, gli argomenti come oggi. Il filtro
   sul cuore vale per entrambe le sezioni.
4. **Descrizione** (27 nov): un tema ha, oltre al nome, una descrizione facoltativa di una o due frasi scritta
   dall'utente (cosa entra e cosa no). L'LLM la legge accanto al nome nel passo degli argomenti.
5. **Regole di dettaglio** (27 nov, approvate in blocco):
   - le notizie già presenti non si riassegnano a un tema nuovo: si portano dentro con "Unisci";
   - unendo due argomenti, se almeno uno è un tema la destinazione diventa tema, tiene nome e descrizione, e
     prende la descrizione dell'altro se non ne ha una;
   - un argomento che smette di essere tema torna alle regole degli argomenti (sotto 2 notizie sparisce dalla
     Timeline, senza notizie viene cancellato, `ESE-10`);
   - solo l'utente crea, marca e smarca i temi; l'LLM assegna le notizie ma non crea temi;
   - da fuori casa si fa tutto, come per gli argomenti;
   - il riassunto dell'evoluzione e gli avvisi della Home funzionano come per gli argomenti.

Fase 1 chiusa il 27 novembre 2026: i requisiti sono nel PRD (`ESE-08b`, `ESE-10`, `UI-09`) e in CONTEXT.md.

## Fase 2

Nessuna libreria nuova. La decisione architetturale è nell'[ADR 0015](../adr/0015-temi-scelti-dall-utente.md)
(il numero 0014 è preso dai grafi sul branch `graph_dev`).

## Fase 3 (preview)

Preview del 27 nov: [temi.html](../../mockup/temi.html), costruita dalla Timeline vera (stile e sidebar della
dashboard di oggi, `src/gradiens/dashboard/static/stile.css`) con dati finti. Una barra in basso a destra passa tra
tre viste: la Timeline con le sezioni Temi e Argomenti e il modulo "Nuovo tema"; la pagina di un tema; la pagina di
un argomento, con l'interruttore spento. Contiene una copia dello stile della dashboard, quindi si apre
anche come file, senza server.

Scelte di dettaglio fatte nella preview, da approvare:
- nella Timeline la descrizione del tema compare sotto il nome, su una riga, tagliata se è lunga;
- un tema vuoto mostra "ancora nessuna notizia · creato il …";
- nella pagina dell'argomento un riquadro sopra la timeline ha l'interruttore "Raccogli tutto il tema"; acceso,
  mostra la descrizione da modificare con "Salva la descrizione". Accanto al nome di un tema c'è l'etichetta "tema";
- il testo di "Unisci" ricorda che, se uno dei due è un tema, la destinazione diventa tema.
