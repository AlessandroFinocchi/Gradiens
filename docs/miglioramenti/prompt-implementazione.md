# Prompt per implementare i miglioramenti

Un pezzo per conversazione. Per ogni pezzo: apri una conversazione nuova, incolla il **prompt di
partenza** con dentro il **paragrafo del pezzo**, e usa i **prompt per continuare** finché il pezzo
è chiuso. Poi fai il commit e passa al pezzo successivo.

I 15 pezzi preparati il 15 novembre 2026, il refactoring e il formatter sono stati fatti dal 15 al 17
novembre: l'elenco con i commit è in [README.md](README.md), sezione "Fatto". Qui restano i pezzi ancora
aperti. Meglio senza sottoagenti in parallelo: sono loro che hanno fatto finire la quota durante l'analisi.

## 1. Prompt di partenza (uguale per tutti i pezzi)

Sostituisci `<<PEZZO>>` con uno dei paragrafi della sezione 2.

```text
Lavori su Gradiens, in questa cartella. Leggi CLAUDE.md, poi docs/miglioramenti/README.md e
docs/miglioramenti/decisioni.md.

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

## 2. I pezzi rimasti

### Avvisi come errori nei test (Opus 5.5, effort high)

```text
La decisione 48: prima chiudere le connessioni al database lasciate aperte, compresi i motori creati
dentro i test (sezione 3 di docs/miglioramenti/05-dipendenze-e-stile.md e misura M-2
dell'appendice), poi far fallire i test sugli avvisi (sezione 3.4). Su Windows e su Linux.
```

### Campi di `claude auth status` (Sonnet 5.5, effort high)

```text
Il punto 4 della sezione 4.5 di docs/miglioramenti/05-dipendenze-e-stile.md: leggere da
`claude auth status` solo i campi documentati. Non lanciare chiamate al modello.
```

### Una proposta in bozza: prima si discute (Opus 5.5, effort high)

Per le proposte ancora in bozza (elenco in [README.md](README.md), "Ancora aperto"). Questo prompt non
scrive codice: porta a una decisione, che poi diventa un pezzo.

```text
Discutiamo la proposta <<6a-4 | 6a-5 | 6a-7 | ...>> di docs/miglioramenti/<<documento>>. Controlla
prima se il codice di oggi la cambia (dopo l'analisi sono arrivati ADR 0010-0013). Poi fammi le
domande una alla volta, con la risposta che consigli, e scrivi le mie risposte in
docs/miglioramenti/decisioni.md. Non scrivere codice.
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
1. lancia tutti i test, `uv run ruff check` e `uv run ruff format --check`, e dimmi il risultato;
2. esegui /ponytail-review e dimmi cosa ha trovato;
3. aggiorna i documenti che il pezzo tocca e la sezione "Fatto" di docs/miglioramenti/README.md;
4. dimmi con parole semplici: cosa è cambiato, come lo verifico io a mano, e cosa non hai
   potuto provare (per esempio su Windows);
5. proponimi il messaggio di commit. Il commit lo faccio io.
```

**Se la conversazione si è allungata troppo a metà pezzo:**

```text
Scrivi in docs/miglioramenti/README.md, sotto "Ancora aperto", a che punto siamo con questo
pezzo: cosa è fatto, cosa manca, quali file hai toccato. Poi mi fermo e riprendo in una
conversazione nuova.
```

## 4. Cose da non mettere in nessun pezzo, per ora

- **La migrazione del database in transazione** e **il doppio avvio del servizio** (schede 5 e 6
  del documento 04): non c'è una soluzione sicura. Vanno prima ripensate, in una conversazione
  dedicata, con Fable 5.2.
- **Le misure sui token M1-M6 e la prova di yt-dlp**: sono autorizzate, ma decidi tu quando,
  perché consumano quota o fanno richieste a YouTube.
