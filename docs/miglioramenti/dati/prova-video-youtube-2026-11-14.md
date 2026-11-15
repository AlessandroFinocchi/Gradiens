# Prova sui video YouTube esclusi come "sponsorizzato o offerta" (14 novembre 2026)

Dati della fase 4 ([04-debugging.md](../04-debugging.md), sospetto S-01). Prova autorizzata dall'utente
(decisione 25): **una** richiesta al feed del canale seguito e **una** chiamata di pre-filtro con Haiku.
Il nome del canale, i titoli e i testi delle descrizioni non sono riportati: sono dati dell'utente.

## Metodo

- Il feed del canale è stato letto con il codice dell'app (`fonti/youtube/__init__.py`, `raccogli`): 15 video,
  tra cui tutti e 7 quelli esclusi nelle esecuzioni 8, 9 e 10.
- I 15 video sono stati mandati al pre-filtro in **un solo blocco**, con il prompt di sistema vero
  (`esecuzione/prompt.py`, `sistema_prefiltro` con l'esclusione degli sponsorizzati attiva), lo schema vero e
  le stesse opzioni dell'app (`llm/claude_code.py`), modello `haiku` (Haiku 5.5). Il sommario è la
  descrizione del video tagliata a 1.500 caratteri, come fa l'app. Messaggio di 8.736 caratteri.
- Consumo: 5.881 token in ingresso (tutti scritti in cache a 1 ora) e 1.693 in uscita, di cui 1.567 di
  ragionamento; 7.576 in tutto (la stima era circa 5.000). 9,7 secondi.

## Che cosa c'è nel sommario dei video

| Tipo di video | Quanti | Lunghezza della descrizione | Link | Contenuto |
|---|---|---|---|---|
| Brevi | 11 | 153-248 caratteri | 0 | il titolo ripetuto, due o tre hashtag e **una riga fissa di autopromozione** del canale (invito a entrare in un corso a pagamento dell'autore, con il nome del sito) |
| Lunghi | 4 | 773-1.698 caratteri | 4-6 | **iniziano** con tre o quattro righe di link (il corso a pagamento, un servizio dell'autore, un profilo social; in un caso l'invito a provare un prodotto), poi il riassunto vero del video |

Nessuna descrizione contiene parole come "sponsor", "sconto", "coupon", "codice" o "offerta". **Tutte** le 15
descrizioni contengono l'invito al corso a pagamento dell'autore.

## Esito

| Video | Esclusi nelle esecuzioni 8-10 | Verdetto di oggi |
|---|---|---|
| 6 video (5 brevi, 1 lungo) | sì | **pertinenti** |
| 1 video lungo, la cui descrizione inizia con "Provalo su" e il nome di un prodotto | sì | **sponsorizzato** |
| 8 video (6 brevi, 2 lunghi) | no (più recenti, mai visti dall'app) | **pertinenti** |

Risposta dello strumento: 14 id tra i pertinenti, 1 tra gli sponsorizzati. Il testo del ragionamento del
modello non è disponibile nella risposta (il blocco è vuoto).

## Che cosa dimostra

1. **Il verdetto non è stabile.** Gli stessi 7 video, con lo stesso prompt e lo stesso modello, sono stati
   esclusi 7 volte su 7 nelle esecuzioni vere e 1 volta su 7 in questa prova. È cambiata la composizione del
   blocco: nelle esecuzioni vere i video stavano in blocchi misti con paper e articoli di siti (il blocco di
   confine tra paper e siti, non l'ultimo: vedi la scheda 1 di 04-debugging.md), qui in un blocco di soli
   video. Una sola prova: non si sa quanto pesi il caso e quanto il blocco.
2. **Il materiale per sbagliare c'è in ogni descrizione**: l'invito a un corso a pagamento. L'istruzione
   "Escludi i contenuti sponsorizzati e le offerte commerciali" (`esecuzione/prompt.py:25-26`) è pensata per
   gli articoli dei siti (`WEB-22`, `WEB-23`) ma viene applicata a ogni tipo di notizia, e il pre-filtro vede
   solo titolo e descrizione, non il contenuto del video.
3. **L'errore è definitivo**: un video escluso entra nel registro delle notizie già viste e non viene più
   riconsiderato (verificato nella fase 2). I 7 video sono persi per l'app, anche se oggi passerebbero.
4. **Campi della risposta riconfermati** (erano stati visti il 12 novembre in dati poi persi):
   `usage.output_tokens_details.thinking_tokens` e `usage.cache_creation.ephemeral_1h_input_tokens` esistono
   nella risposta di Claude Code 2.1.316; il ragionamento è il 93% dell'uscita di questa chiamata.

## Limiti

Una sola chiamata; un solo canale; il blocco misto delle esecuzioni vere non è stato riprodotto (servirebbero
altre chiamate, da chiedere all'utente).
