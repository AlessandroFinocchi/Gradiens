# Prova vera dell'aiuto dell'LLM al profilo di un sito (17 novembre 2026)

Autorizzata dall'utente il 17 nov 2026 (una chiamata). Riguarda l'[ADR 0012](../../adr/0012-llm-del-profilo-del-sito-nel-backend.md)
e la decisione 58. Dati grezzi: [prova-aiuto-profilo-2026-11-17.json](prova-aiuto-profilo-2026-11-17.json) (messaggio inviato,
risposta grezza, proposta convalidata; solo link pubblici del sito, nessun dato personale).

## Come

- Script fuori dal progetto che chiama `esecuzione/aiuto_profilo.aiuta` come la rotta del bottone, su una **copia** del
  database: il profilo vero non è stato modificato.
- Sito: redhotcyber (id 2), il caso della scheda 6a-12: le 8 sezioni del profilo erano partner, community e sei
  pagine delle conferenze.
- Provider e modello dell'elaborazione: Claude Code con Haiku, su Linux. Richieste al sito: robots.txt e la home.

## Risultato

| Misura | Valore |
|---|---|
| Durata | 14,4 s |
| Ingresso inviato | 1.023 caratteri di sistema + 4.967 di messaggio, 15 gruppi di link, nessuno tolto |
| Stima prima della chiamata | 2.549 token di testo + 1.300 di carico fisso + 700 di uscita = 4.549 |
| Token veri | 4.325 in ingresso, 2.658 in uscita, **6.983** in tutto (tetto 10.000) |

- **Proposta**: togliere tutte le 8 sezioni vecchie; aggiungere 8 pagine di categoria delle notizie (cybersecurity,
  Italia, cybercrime, hacking, bug di sicurezza, cyberpolitica, rubriche) e la pagina inglese delle vulnerabilità
  critiche; escludere `/servizi/` e `academy.redhotcyber.com` (corsi a pagamento). Le due esclusioni che il profilo
  aveva già sono state scartate dalla convalida, come previsto.
- **Qualità** (giudizio di chi ha fatto la prova, da confermare dall'utente): le sezioni tolte sono quelle inutili
  indicate dalla scheda 6a-12, e quelle nuove elencano davvero articoli. La pagina inglese va contro la decisione 22
  (traduzioni escluse per default); l'utente può togliere la spunta.

## Cosa non torna con le stime

- **Uscita**: 2.658 token contro i 700 stimati dalla 6a-12. La nota della risposta è lunga (circa 560 caratteri invece
  di "una o due frasi"), ma da sola non spiega la differenza: probabilmente conta il ragionamento di Haiku, che la 6b
  segnala come sempre attivo (6b-5). È una misura sola.
- **Conseguenza**: con un sito dall'albero grande, l'ingresso viene accorciato fino a circa 8.000 token stimati, e con
  un'uscita come questa il totale vero passerebbe i 10.000. Il bottone lo segnala ("oltre il tetto stimato") ma non
  lo impedisce.
- **Nota tagliata**: la convalida taglia la nota a 300 caratteri, a metà di una parola.

## Correzione dopo la prova (17 nov 2026, chiesta dall'utente)

L'uscita stimata in `esecuzione/aiuto_profilo.USCITA` passa da 700 a 2.700 token e la nota si taglia a 600 caratteri
invece di 300 (`fonti/siti/aiuto.NOTA_MASSIMA`). Così l'ingresso si accorcia prima, a circa 6.000 token stimati
invece di 8.000.
