# Prompt per implementare i miglioramenti

Un pezzo per conversazione. Per ogni pezzo: apri una conversazione nuova, incolla il **prompt di
partenza** con dentro il **paragrafo del pezzo**, e usa i **prompt per continuare** finché il pezzo
è chiuso. Poi fai il commit e passa al pezzo successivo.

Modello ed effort consigliati sono indicati per ogni pezzo. Meglio senza sottoagenti in parallelo:
sono loro che hanno fatto finire la quota durante l'analisi.

## 1. Prompt di partenza (uguale per tutti i pezzi)

Sostituisci `<<PEZZO>>` con uno dei paragrafi della sezione 2.

```text
Lavori su Gradiens, in questa cartella. Leggi CLAUDE.md, poi il "Riepilogo finale" in cima a
docs/miglioramenti/README.md e docs/miglioramenti/decisioni.md.

In questa conversazione voglio implementare UNA sola cosa:

<<PEZZO>>

Regole:
- Nei documenti di docs/miglioramenti, se in testa c'è una nota "Decisioni dell'utente" o una
  sezione "Esito della rilettura", vale quella sul testo sotto.
- Prima scrivi i test, poi il codice. I test devono essere verdi prima e dopo.
- Tocca solo ciò che serve a questo pezzo. Se trovi altro da sistemare, scrivimelo e non farlo.
- Deve funzionare su Windows e su Linux.
- Non consumare quota LLM, non installare pacchetti e non fare molte richieste a siti esterni
  senza chiedermelo prima.
- Non fare commit, merge o push: li faccio io.
- Non lanciare sottoagenti in parallelo.
- Se i documenti e il codice non coincidono, fermati e chiedimelo.

Prima di scrivere codice dimmi in poche righe, con parole semplici, cosa farai e in quanti
passi, e aspetta il mio ok.
```

## 2. I pezzi, nell'ordine consigliato

### Pezzo 1 — Video YouTube (Sonnet 5.5, effort medium)

```text
La correzione dei video YouTube esclusi come "sponsorizzati": l'esclusione non si applica più
ai video (decisione 36; scheda 1 di docs/miglioramenti/04-debugging.md). Per arXiv e per i siti
resta com'è. Alla fine aggiorna il testo di WEB-23 nel PRD.
```

### Pezzo 2 — I primi 10 test (Sonnet 5.5, effort high)

```text
I test di caratterizzazione T-01…T-10 di docs/miglioramenti/02-test-e-copertura.md (decisione
26), tenendo conto delle correzioni scritte in "Esito della rilettura". Fissano il comportamento
di oggi: se un test mostra un comportamento sbagliato, resta verde con un commento "vedi S-nn"
(decisione 24). Nessuna modifica al codice dell'app. Aggiungi anche pytest-cov come dipendenza
di sviluppo, senza soglia minima (decisione 23): per questo chiedimi il permesso di installare.
```

### Pezzi 3-7 — Refactoring, un passo per conversazione (Opus 5.5, effort high)

Usa lo stesso paragrafo cambiando il nome del passo, in quest'ordine: `R-02a`, `R-01`, `R-03`,
`R-04`, `R-02b`.

```text
Il passo di refactoring <<R-02a | R-01 | R-03 | R-04 | R-02b>> di
docs/miglioramenti/03-revisione-architetturale.md (decisione 28), nella versione corretta dopo
la rilettura. È solo uno spostamento di codice: il comportamento non deve cambiare. Non
correggere bug: se ne incontri uno, lascialo com'è e scrivimelo. Dimmi quali test esistenti
vanno aggiornati perché usano nomi che il passo sposta. Alla fine aggiorna
docs/architettura/struttura.md.
```

### Pezzo 8 — Filtro dei paper arXiv (Opus 5.5, effort high)

```text
L'ADR 0010 (docs/adr/0010-prefiltro-arxiv-fino-al-tetto.md): il pre-filtro dei paper arXiv si
ferma quando i promossi riempiono il tetto. Dettagli nella scheda 6b-2 di
docs/miglioramenti/06b-consumo-di-token.md. Porta il tetto arXiv predefinito a 30 (decisione 9).
Alla fine aggiorna nel PRD ARX-02 ed ESE-04, la pagina Aiuto e porta l'ADR allo stato
"accettato".
```

### Pezzo 9 — Protezione del profilo dei siti (Opus 5.5, effort high)

```text
La decisione 21: se un sito non risponde e la nuova analisi non trova niente, si tiene il
profilo vecchio e si segnala il problema (proposta 6a-11 B di
docs/miglioramenti/06a-ricerca-sui-siti.md; scheda A-02 di
docs/miglioramenti/03-revisione-architetturale.md). Aggiungi anche le decisioni 18 (voci di
altri domini nei feed fuori, salvo i siti collegati) e 22 (traduzioni escluse per default).
Alla fine aggiorna nel PRD WEB-08, WEB-24 e WEB-25.
```

### Pezzo 10 — Ricerca sui siti incrementale (Opus 5.5, effort xhigh)

```text
L'ADR 0011 (docs/adr/0011-raccolta-incrementale-dei-siti.md), compresa la sezione "Quando
avanza coperto fino a". Dettagli nella scheda 6a-6 di docs/miglioramenti/06a-ricerca-sui-siti.md
e nella scheda 2 di docs/miglioramenti/04-debugging.md. Serve una migrazione del database:
provala su una COPIA del database vero prima di applicarla, e non cambiare il modo in cui
dati/database.py apre le transazioni (quel problema è ancora aperto). Nessun margine di
rilettura (decisione 37). Alla fine aggiorna PRD (WEB-26), struttura.md e lo stato dell'ADR.
```

### Pezzo 11 — Correzioni dei bug con soluzione pronta (Opus 5.5, effort high)

Una conversazione per scheda, oppure due o tre schede piccole insieme.

```text
Le correzioni delle schede <<numeri>> di docs/miglioramenti/04-debugging.md, come corrette in
"Esito della rilettura" e con le decisioni 39-43. Schede con soluzione pronta: 3 (database
bloccato), 4 (risposte dell'LLM di forma inattesa), 7 (due avvii del bot), 8 (redirect di
robots.txt), 9 (ora solare), 12 (gradiens aggiorna), 13 (rete che arriva tardi), 14
(robots.txt). NON toccare le schede 5 e 6: non hanno una soluzione pronta. Per ogni scheda
scrivi prima il test che oggi fallisce.
```

### Pezzo 12 — Linter (Sonnet 5.5, effort medium)

```text
Ruff come linter, con la configurazione minima della sezione 6.1 di
docs/miglioramenti/05-dipendenze-e-stile.md (decisione 47): solo il linter, niente formatter.
Chiedimi il permesso di installarlo. Mostrami l'elenco delle segnalazioni prima di correggerle.
Aggiungi il passo alla CI.
```

### Pezzo 13 — Claude Code sotto controllo (Opus 5.5, effort high)

```text
La sezione 4.5 di docs/miglioramenti/05-dipendenze-e-stile.md: registrare la versione di Claude
Code a ogni esecuzione, fermare subito l'esecuzione su un errore di login, e la prova di fumo
quando la versione cambia (decisione 45). La prova di fumo consuma quota: prima di lanciarla
davvero chiedimelo.
```

### Pezzo 14 — Dashboard dal telefono (Opus 5.5, effort xhigh)

```text
L'ADR 0013 (docs/adr/0013-dashboard-da-fuori-casa-con-tailscale-serve.md), versione completa
(decisioni 53-56). Leggi tutta la sezione "Esito della rilettura di sicurezza" di
docs/miglioramenti/06c-dashboard-da-internet.md: il controllo "viene dal PC" deve usare una
seconda porta locale per Tailscale Serve, non le intestazioni. Non cambiare tu la
configurazione di Tailscale né del sistema: dimmi i comandi che devo lanciare io. Alla fine
aggiorna PRD (AMB-02, TG-03), struttura.md, la pagina Aiuto e lo stato dell'ADR.
```

### Pezzo 15 — Aiuto dell'LLM per i siti difficili (Opus 5.5, effort high)

```text
L'ADR 0012 (docs/adr/0012-llm-del-profilo-del-sito-nel-backend.md) e la decisione 19: un
bottone che chiede all'LLM di aiutare a creare il profilo di un sito, con un tetto di 10.000
token. Dettagli nella scheda 6a-12 di docs/miglioramenti/06a-ricerca-sui-siti.md. Ogni prova
vera consuma quota: chiedimelo prima.
```

## 3. Prompt per continuare la conversazione

**Dopo il piano, per dare il via:**

```text
Ok, procedi con il primo passo. Fermati alla fine del passo e dimmi cosa hai fatto.
```

**Per andare avanti:**

```text
Ok, passo successivo.
```

**Se non hai capito una cosa:**

```text
Non ho capito questo punto: <<incolla la frase>>. Spiegamelo con parole semplici e con un
esempio, senza termini tecnici.
```

**Se qualcosa non funziona:**

```text
Non funziona: <<incolla l'errore o descrivi cosa vedi>>. Prima di correggere dimmi qual è la
causa. Se non la sai, dimmelo invece di tirare a indovinare.
```

**Per chiudere il pezzo:**

```text
Chiudiamo il pezzo:
1. lancia tutti i test e dimmi il risultato;
2. esegui /ponytail-review e dimmi cosa ha trovato;
3. aggiorna i documenti che il pezzo tocca e lo stato della proposta in
   docs/miglioramenti/README.md;
4. dimmi con parole semplici: cosa è cambiato, come lo verifico io a mano, e cosa non hai
   potuto provare (per esempio su Windows);
5. proponimi il messaggio di commit. Il commit lo faccio io.
```

**Se la conversazione si è allungata troppo a metà pezzo:**

```text
Scrivi in docs/miglioramenti/README.md, sotto la proposta di questo pezzo, a che punto siamo:
cosa è fatto, cosa manca, quali file hai toccato. Poi mi fermo e riprendo in una
conversazione nuova.
```

## 4. Cose da non mettere in nessun pezzo, per ora

- **La migrazione del database in transazione** e **il doppio avvio del servizio** (schede 5 e 6
  del documento 04): non c'è una soluzione sicura. Vanno prima ripensate, in una conversazione
  dedicata, con Fable 5.2.
- **Il formatter**: solo dopo i refactoring (decisione 47).
- **Le misure sui token M1-M6 e la prova di yt-dlp**: sono autorizzate, ma decidi tu quando,
  perché consumano quota o fanno richieste a YouTube.
