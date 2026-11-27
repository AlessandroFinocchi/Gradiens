# I temi sono argomenti marcati dall'utente

L'[ADR 0008](0008-argomenti-assegnati-a-fine-esecuzione.md) fa assegnare all'LLM ogni notizia a un singolo evento. Per un soggetto ampio, come "GTA 6", le notizie si spezzano in tanti argomenti (uscita, patch, trailer), e unirli a mano non basta: le notizie nuove non confluiscono nell'argomento unito, perché il prompt chiede eventi precisi, e un argomento rimasto senza notizie viene cancellato (`ESE-10`).

Un argomento può quindi essere marcato come **tema** dall'utente: una colonna booleana e una descrizione facoltativa sulla tabella `argomenti`, non una tabella nuova. Nel passo degli argomenti i temi si mandano all'LLM in un elenco a parte, con nome e descrizione, sempre (senza il limite dei 30 giorni e dei 100 argomenti) e con una regola diversa: ogni notizia che riguarda il tema va lì, anche se è un evento preciso. Una notizia resta in un solo argomento (`ESE-08`), quindi il tema vince sull'evento. La pulizia non cancella un tema vuoto. Requisiti: `ESE-08b`, `ESE-10`, `UI-09`, decisioni in [temi.md](../requisiti/temi.md).

## Alternative considerate

- **Tema come contenitore di argomenti-evento**: una tabella nuova sopra gli argomenti, con una seconda assegnazione (argomento → tema). Mantiene `ESE-08` intatto, ma aggiunge un concetto, una pagina e una chiamata in più per lo stesso risultato visibile. Scartata dall'utente il 27 nov.
- **Solo il nome, senza descrizione**: scartata, perché con nomi ampi o ambigui ("Elezioni", "Apple") l'LLM non sa cosa entra.
- **Riassegnare con l'LLM le notizie già presenti alla creazione di un tema**: scartata, consuma quota a ogni tema; le notizie già presenti si portano dentro con "Unisci".

## Conseguenze

- Il prompt degli argomenti cresce di un elenco sempre presente: pochi token per tema, ma senza tetto. Se i temi diventassero tanti andrà messo un limite.
- Un tema è sempre più "attraente" di un argomento-evento: un tema troppo ampio svuota gli argomenti precisi. La descrizione serve anche a restringerlo.
- Il riassunto dell'evoluzione legge al massimo 40 notizie (decisione 72): per un tema racconta solo l'ultimo periodo.
