# La dashboard si apre da fuori casa solo dalla rete Tailscale dell'utente, tramite Tailscale Serve

**Stato**: accettato (decisioni dell'utente del 15 novembre 2026, n. 50-57 di
[decisioni.md](../miglioramenti/decisioni.md)); **implementato il 17 novembre 2026** nella versione completa, con
`AMB-02`, `TG-03` e `struttura.md` aggiornati. Da fare a mano dall'utente: i passi di Tailscale (pagina Aiuto,
"Dashboard da fuori casa") e la verifica dal telefono. Non ancora verificati dal vero: Serve e il ramo Windows.

**Come è stato fatto**: Gradiens apre due prese su `127.0.0.1`, la porta principale (`GRADIENS_PORTA`, 8765) e
quella per Serve (`GRADIENS_PORTA_REMOTA`, 8766); se la seconda è occupata parte lo stesso e la sezione lo dice.
Vale "dal PC" solo una richiesta arrivata sulla porta principale da `127.0.0.1` o `::1` (`dashboard/comune.dal_pc`).
Sulla porta per Serve si accettano solo richieste con l'accesso attivo, con il nome Tailscale salvato e con
l'intestazione `Tailscale-User-Login` (`app/servizio.ControlloHost`). Interruttore e nome stanno nel database
(migrazione 0014). Il comando di Serve diventa quindi `tailscale serve --bg 8766`, non `8765`.

Oggi la dashboard ascolta solo su `127.0.0.1` e non ha autenticazione. L'utente vuole aprirla da fuori casa,
solo lui e solo dai suoi dispositivi; non ha un dominio e usa già Tailscale su questa macchina. L'analisi è in
[06c-dashboard-da-internet.md](../miglioramenti/06c-dashboard-da-internet.md); la sezione "Esito della
rilettura di sicurezza" di quel documento corregge la protezione proposta nella bozza e fa parte di questa
decisione.

Gradiens continua ad ascoltare solo sul PC. L'accesso da fuori casa passa da `tailscale serve` sullo stesso
PC, configurato una volta dall'utente: fa da proxy HTTPS e risponde solo ai dispositivi della rete Tailscale
dell'utente. Non c'è autenticazione nell'app: la fa Tailscale. Si fa la versione completa: una sezione
"Accesso da fuori casa" nelle Impostazioni e, quando l'accesso è attivo, un link al resoconto dell'esecuzione
nel messaggio Telegram.

## Che cosa si può fare da remoto e che cosa solo dal PC

Da remoto: leggere, mettere il cuore, avviare un'esecuzione, aggiungere fonti e interessi.

Solo dal PC su cui gira Gradiens: spegnere Gradiens; cambiare l'avvio all'accensione; creare o togliere le
icone del pannello; cambiare il bot o la chat di Telegram; **togliere i cuori**; **eliminare interessi e
fonti**; **alzare i tetti** (paper arXiv, pagine e articoli dei siti, finestra di raccolta).

## Vincoli di sicurezza (dalla rilettura)

- **Il controllo "questa richiesta viene dal PC" non deve dipendere dal proxy.** Un controllo basato su `Host`
  locale e assenza di `X-Forwarded-For` si aggira da un dispositivo della rete privata con una richiesta
  scritta a mano, a meno che Serve aggiunga `X-Forwarded-For`: un comportamento che la documentazione
  ufficiale di Serve non descrive. Serve deve quindi entrare da una **seconda porta locale** usata solo da
  lui, e una richiesta vale "dal PC" solo se arriva sulla porta principale. Serve va usato solo in modalità
  HTTP, mai nelle modalità TCP.
- **Niente incorniciamento**: le risposte portano le intestazioni che vietano di mostrare la dashboard dentro
  un'altra pagina.
- **Niente richieste verso la rete locale**: gli indirizzi aggiunti a mano (siti e feed) passano dallo stesso
  controllo dell'indirizzo pubblico usato per i link e i redirect, comprese le forme non canoniche di un
  indirizzo IP. È il punto che la decisione 39 rimandava a questa proposta.
- **Host consentiti**: si aggiunge il nome completo della macchina nella rete Tailscale, mai un modello con
  l'asterisco.
- **Verifica a mano dopo l'attivazione**: dal telefono, un'azione "solo dal PC" deve essere rifiutata.

## Opzioni considerate

- **Lasciare così** (solo dal PC): scartata, l'utente vuole leggere le notizie dal telefono.
- **Accesso diretto all'indirizzo della rete privata**: scartata. Gradiens dovrebbe ascoltare su un secondo
  indirizzo, e su un portatile che cambia rete ascoltare su tutti gli indirizzi lo esporrebbe sui Wi-Fi
  pubblici; niente HTTPS.
- **Tunnel pubblici** (Tailscale Funnel, Cloudflare Tunnel, ngrok) **e port forwarding con DNS dinamico**:
  scartati. Espongono la dashboard a chiunque, quindi richiederebbero un'autenticazione nell'app, un limite
  alle esecuzioni e altre protezioni; Cloudflare Tunnel con indirizzo stabile richiede un dominio.

## Conseguenze

- Cambiano `AMB-02`, `TG-03` e la regola "Sicurezza della dashboard" di `struttura.md`; la decisione 51
  dell'intervista sui requisiti (niente link alla dashboard su Telegram) è superata quando l'accesso da fuori
  casa è attivo.
- Passi a mano dell'utente, fuori da Gradiens: abilitare i certificati HTTPS nella rete Tailscale, dopo aver
  controllato il nome della macchina (finisce in un registro pubblico dei certificati); configurare Serve
  (su Linux serve `sudo` o l'utente operatore); installare l'app Tailscale sul telefono, che oggi non è nella
  rete privata.
- Rischio che resta: chi ha in mano un dispositivo della rete privata (un telefono rubato) può leggere tutto
  e avviare esecuzioni, consumando quota. Non può più cancellare l'Archivio né alzare i tetti.
- Se un giorno si attivasse Funnel per errore, tutta la dashboard diventerebbe pubblica senza autenticazione.
  **Deciso dall'utente il 17 novembre 2026**: la porta per Serve rifiuta le richieste senza `Tailscale-User-Login`,
  che Serve aggiunge per i dispositivi della rete Tailscale e che manca nel traffico di Funnel (pagina ufficiale di
  Serve). Rischio: se una versione di Serve non la mandasse più, l'accesso da fuori casa si fermerebbe; la prova dal
  telefono lo mostrerebbe subito.
- Non verificato: il comportamento di Serve dal vero e tutto il ramo Windows (lì Tailscale deve restare
  attivo senza accesso dell'utente). Un tunnel pubblico richiederà un ADR nuovo.
- Il codice specifico di un sistema operativo resta solo in `app/avvio_sistema.py`
  ([ADR 0007](0007-avvio-all-accensione-su-linux-con-systemd.md)): Gradiens non lancia né configura Tailscale.
