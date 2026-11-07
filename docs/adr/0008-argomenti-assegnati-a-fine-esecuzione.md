# Gli argomenti si assegnano con un passo unico a fine esecuzione

Le notizie si valutano tre alla volta, in parallelo (ADR 0006). Se l'argomento si assegnasse dentro ogni chiamata di valutazione, come diceva la prima versione di `ESE-05`, tre articoli sullo stesso evento arrivati nella stessa esecuzione non si vedrebbero a vicenda, e ognuno creerebbe il suo argomento.

Per questo, dopo la valutazione, l'esecuzione fa un passo apposta. Claude riceve tutte le notizie mostrate dall'esecuzione (titolo e riassunto in italiano) e gli argomenti esistenti, e per ciascuna notizia sceglie un argomento esistente, ne crea uno nuovo oppure nessuno (`ESE-08`). Le notizie si mandano a blocchi, uno dopo l'altro, così un blocco vede gli argomenti creati da quello prima. Gli argomenti esistenti sono quelli con almeno una notizia aggiornata negli ultimi 30 giorni, al massimo 100: un evento più vecchio difficilmente ha sviluppi nuovi.

## Alternative considerate

- **Argomento nella chiamata di valutazione**: scartato. Crea argomenti doppi per lo stesso evento nella stessa esecuzione, e manda l'elenco degli argomenti a ogni notizia invece che una volta per blocco.

## Conseguenze

- Il passo usa il provider e il modello dell'elaborazione, e i suoi token si contano in quel ruolo.
- Se il passo fallisce (rete, Claude), le notizie restano senza argomento e l'esecuzione si chiude lo stesso: un argomento mancante non è un errore grave.
- Le notizie che restano senza argomento non vengono ripresentate alle esecuzioni successive.
