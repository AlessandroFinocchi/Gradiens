# La raccolta dai siti diventa incrementale

**Stato**: accettato, da implementare (decisione dell'utente del 13 novembre 2026, n. 17 di
[decisioni.md](../miglioramenti/decisioni.md)). Il codice e il PRD descrivono ancora il comportamento
precedente: si aggiornano insieme.

Oggi a ogni esecuzione ogni sito rifà la ricerca su tutta la finestra di raccolta, con tetti fissi di 40
pagine e 100 articoli. Per un sito ad alto volume come hwupgrade non basta: i feed coprono circa 10 ore,
la home non ha date, e le pagine del tetto si spendono in gran parte per cercare date di articoli vecchi o
già visti. L'analisi è in [06a-ricerca-sui-siti.md](../miglioramenti/06a-ricerca-sui-siti.md), scheda
6a-6 (con 6a-3).

Per questo ogni sito ricorderà fino a quando è stato coperto ("coperto fino a"), e l'esecuzione successiva
cercherà solo gli articoli usciti dopo, sempre dentro la finestra di raccolta. Il valore si salva a fine
esecuzione, non al momento della raccolta, così un'esecuzione interrotta o fallita non fa perdere
articoli. Se un sito non riesce a coprire l'intervallo entro i suoi tetti, riceve lo stato nuovo
"copertura parziale".

## Quando avanza "coperto fino a"

Precisazione del 14 novembre 2026 (decisione 34; analisi in
[03-revisione-architetturale.md](../miglioramenti/03-revisione-architetturale.md), scheda A-03 e proposta
P-2). Durante l'esecuzione si annotano, per ogni sito, gli indirizzi nuovi e la loro data. A fine esecuzione
"coperto fino a" avanza al minimo tra l'ora della raccolta e la data della notizia più vecchia di quel sito
che non è nel registro delle notizie già viste, cioè che è rimasta senza esito per un errore o per
un'interruzione. Non c'è una regola a parte per le esecuzioni interrotte: le notizie non elaborate
trattengono il loro sito, al massimo per la durata della finestra di raccolta.

Scartate: avanzare sempre (perde le notizie da riprovare); avanzare solo se tutte le notizie del sito hanno
un esito (una sola notizia senza esito bloccherebbe il sito, anche a tempo indefinito se ha la data
incerta); un elenco di notizie in attesa nel database (più preciso, ma più stato da tenere: resta la strada
se le esecuzioni vere mostrano siti trattenuti a lungo).

Rischio noto e accettato (decisione 37 del 15 novembre 2026): se il feed di un sito mostra gli articoli con
qualche ora di ritardo rispetto alla pubblicazione, gli articoli usciti in quelle ore prima di ogni raccolta
non vengono più raccolti, e lo stato del sito non lo segnala (analisi in
[04-debugging.md](../miglioramenti/04-debugging.md), scheda 2). L'utente ha scelto di non aggiungere un
margine di rilettura.

## Opzioni considerate

- **Lasciare così e alzare i tetti a mano**: scartata. Più pagine a ogni esecuzione per rileggere le
  stesse cose, e hwupgrade resta comunque scoperto.
- **Saltare le strategie che per quel sito non trovano mai niente**: non adottata da sola. Toglierebbe ai
  siti poco frequenti il controllo del feed fermo (`WEB-24`).

## Conseguenze

- Serve una migrazione della tabella `siti` (colonne per "coperto fino a" e per le statistiche di
  raccolta), da provare su una copia del database vero prima di applicarla.
- Cambia il contratto delle fonti di [struttura.md](../architettura/struttura.md): la raccolta di un sito
  riceve anche il punto da cui ripartire e, con la proposta 6a-3, il registro delle notizie già viste.
  Le strategie restano moduli intercambiabili con l'interfaccia comune.
- `WEB-26` acquista lo stato "copertura parziale"; `WEB-19` (tetti per sito) resta. L'utente ha scelto di
  non mettere un tetto di notizie nuove per sito (decisione 12): gli articoli trovati in più consumano
  quota nel pre-filtro e nella valutazione (stima per hwupgrade: 40-80 mila token per esecuzione).
- Vanno definiti i casi in cui si riparte dalla finestra intera: prima raccolta, dopo un guasto, dopo un
  cambio della finestra di raccolta, dopo una modifica del profilo (feed o sezione aggiunti a mano).
- Il vantaggio c'è se Gradiens gira con regolarità: dopo giorni di spegnimento l'intervallo da coprire
  torna a essere la finestra intera.
- L'effetto su richieste e copertura è una stima: l'utente ha scelto di non costruire il banco di misura
  (decisione 15), quindi si verifica il meccanismo con i test su file salvati e l'effetto guardando le
  esecuzioni vere.
- Nessuna differenza tra Windows e Linux.
