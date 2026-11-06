# Claude Code, con l'abbonamento dell'utente, è il provider LLM predefinito

Gradiens usa come provider predefinito Claude Code già installato sul PC, chiamato nella sua modalità senza interfaccia (`claude -p`). Le chiamate consumano la quota dell'abbonamento dell'utente (piano Pro), quindi l'app non ha costi a consumo. Il provider sta dietro la stessa interfaccia degli altri (`LLM-01`), quindi API di Claude e modelli locali restano scelte possibili per ciascun ruolo.

Ogni chiamata è isolata (`LLM-05`):
- nessuno strumento (`--tools ""`);
- nessun server MCP;
- nessuna conversazione salvata (`--no-session-persistence`);
- risposta in JSON validato da uno schema (`--json-schema`).

Il modello è scelto con `--model`; il predefinito è Haiku.

## Opzioni considerate

- **API di Claude come predefinito**: scartata come predefinito perché a pagamento, separatamente dall'abbonamento. Resta disponibile in alternativa, con la chiave in `.env`.
- **Solo modelli locali (RTX 3070, 8 GB)**: scartata come predefinito. I modelli che ci stanno (7-9 miliardi di parametri) vanno bene per il pre-filtro, ma sono più deboli sui riassunti in italiano corretti e completi (`ESE-05`). Restano consigliati per il pre-filtro, per risparmiare quota.
- **Livello gratuito dell'API di Gemini**: scartata. Gemini è fuori dalla prima versione (`LLM-04`), e nel livello gratuito i dati inviati possono essere usati per addestrare i modelli.

## Conseguenze

- La quota Pro (finestre di 5 ore e tetto settimanale) è condivisa con l'uso interattivo di Claude Code, compreso lo sviluppo di Gradiens. Se la quota finisce durante un'esecuzione, l'esecuzione si interrompe e riprende alla successiva (`LLM-06`).
- Il resoconto mostra solo i token, senza costo in dollari (`ESE-11`).
- Ogni chiamata avvia un processo e costa qualche secondo. Per un'esecuzione al giorno è accettabile; il pre-filtro raggruppa più notizie in una sola chiamata.
- Claude Code tiene login e file propri in `~/.claude`, fuori dalla repository. Sono file dello strumento, non di Gradiens (`PER-03`).
- Con l'avvio all'accensione (ADR 0005) l'app gira con lo stesso utente in modalità S4U: va verificato nella fetta 7 che il login di Claude Code sia leggibile anche in quel contesto.
- L'uso dell'abbonamento tramite `claude -p` per un'app personale va tenuto allineato alle condizioni d'uso di Anthropic, che possono cambiare.
