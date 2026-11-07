# L'avvio all'accensione usa un'attività pianificata di Windows senza password salvata

Quando l'interruttore di `AMB-04` è attivo, Gradiens registra un'attività pianificata di Windows con trigger "all'avvio del computer". L'attività esegue `gradiens avvia` con l'utente del PC in modalità S4U ("non memorizzare la password"). L'app parte prima di qualsiasi accesso, senza monitor, e i file della repository restano dell'utente. In modalità S4U l'app non raggiunge le risorse di rete autenticate (cartelle condivise), ma internet sì, e a Gradiens basta questo. L'attività è impostata per riavviare l'app se si blocca. Quando l'interruttore viene spento, l'attività viene rimossa. È l'unica cosa che l'app scrive fuori dalla repository (`PER-03`).

## Opzioni considerate

- **Servizio di Windows (`pywin32`, NSSM, WinSW)**: scartato. Un servizio Python è scomodo da sviluppare e da diagnosticare, NSSM e WinSW sono eseguibili di terze parti da scaricare, e il servizio di solito gira come utente di sistema, con i permessi sui file della repository da gestire a parte.
- **Accesso automatico a Windows più avvio all'accesso**: scartato. Lascia la password salvata nel registro e apre l'account a chiunque accenda il PC.

## Conseguenze

- Creare o rimuovere l'attività richiede i diritti di amministratore. L'interruttore chiede una conferma UAC sullo schermo del PC, quindi va cambiato stando al PC, non da remoto. La dashboard deve spiegarlo e mostrare se la registrazione è riuscita.
- La conferma UAC si chiede lanciando PowerShell come amministratore (`Start-Process -Verb RunAs`) con lo script che registra l'attività (fetta 7b, decisione dell'utente del 7 nov). Se Gradiens è stato avviato proprio dall'attività, gira nella sessione 0, senza desktop, e la finestra UAC non può comparire. Lo stesso vale se la conferma viene negata. In questi casi la dashboard mostra lo script da incollare in un PowerShell aperto come amministratore. L'utente dell'attività si legge prima dell'elevazione: con un account standard il PowerShell elevato appartiene all'amministratore.
- Il codice specifico per Windows sta in un solo modulo, per mantenere l'app portabile (`AMB-03`, [ADR 0001](0001-esecuzione-sul-pc-di-casa.md)).
- L'app avviata dall'attività non ha finestre (gira nella sessione 0). Per questo `gradiens stato` e `gradiens spegni` parlano con il processo in esecuzione attraverso la sua interfaccia locale, non attraverso la console.
- Se la cartella della repository viene cancellata con l'interruttore attivo, l'attività resta registrata ma fallisce senza effetti. Va rimossa a mano dall'Utilità di pianificazione.
