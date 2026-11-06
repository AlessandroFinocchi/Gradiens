# Claude Code, con l'abbonamento dell'utente, è il provider LLM predefinito

Gradiens usa come provider predefinito Claude Code già installato sul PC, chiamato nella sua modalità senza interfaccia (`claude -p`). Le chiamate consumano la quota dell'abbonamento dell'utente (piano Pro), quindi l'app non ha costi a consumo. Il provider sta dietro la stessa interfaccia degli altri (`LLM-01`), quindi API di Claude e modelli locali restano scelte possibili per ciascun ruolo.

Ogni chiamata è isolata (`LLM-05`):
- nessuno strumento (`--tools ""`);
- nessun server MCP;
- nessuna conversazione salvata (`--no-session-persistence`);
- risposta in JSON validato da uno schema (`--json-schema`).

Il modello è scelto con `--model`; il predefinito è Haiku.

## Come si chiama Claude Code

Misure del 6 novembre 2026 (Claude Code 2.1.318, modello Haiku), chiamata minima "rispondi ok":

| Chiamata | Token di contesto | Tempo |
|---|---|---|
| opzioni di default | ~36.000 (prompt e strumenti di Claude Code, server MCP, plugin, CLAUDE.md) | 4,4 s |
| opzioni sotto | ~700 | 2,8 s |

Ogni chiamata usa quindi: `claude -p --model <modello> --output-format json --json-schema <schema> --system-prompt <istruzioni> --tools "" --strict-mcp-config --safe-mode --disable-slash-commands --no-session-persistence`.

- `--safe-mode` esclude CLAUDE.md, plugin, hook e skill, ma mantiene il login dell'abbonamento. `--bare` sarebbe ancora più minimale, ma accetta solo una chiave API e non si può usare.
- `--json-schema` restituisce un JSON già validato (`structured_output`), senza errori di lettura né nuovi tentativi. Costa qualche centinaio di token di uscita in più.
- Il prompt di sistema contiene la parte fissa (istruzioni, interessi, raffinamenti), uguale per tutte le chiamate di un'esecuzione, così le chiamate successive la rileggono dalla cache. La notizia va nel messaggio.
- Le chiamate sono poche: il pre-filtro valuta 25-40 notizie per chiamata; notizie già viste e duplicati si scartano prima; la valutazione completa produce punteggi, riassunto, traduzione e argomento in una sola chiamata.
- Si eseguono 3-4 chiamate in parallelo (sottoprocessi `asyncio`), ognuna con un timeout e un solo nuovo tentativo per gli errori temporanei.
- Dal JSON di risposta si leggono `usage` (token per `ESE-11`), `is_error` e `api_error_status` (quota esaurita, `LLM-06`) e `credential_expires_at` (avviso prima della scadenza del login).
- Scartati: un processo unico con `--input-format stream-json`, perché le chiamate diventerebbero una sola conversazione e ogni notizia pagherebbe le precedenti; il Claude Agent SDK per Python, perché usa la stessa CLI e aggiungerebbe solo una dipendenza.

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
