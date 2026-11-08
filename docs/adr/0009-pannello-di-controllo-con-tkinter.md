# Il pannello di controllo è una finestrella Tkinter, aperta da un'icona che si crea dalle Impostazioni

`AMB-05` chiede che una persona senza familiarità con l'informatica possa accendere e spegnere Gradiens e vederne lo stato senza terminale, su Windows e su Linux.

Il pannello è una piccola finestra fatta con Tkinter, la libreria grafica che fa parte di Python. Mostra lo stato con un pallino colorato (spento, acceso, esecuzione in corso), lo aggiorna da solo ogni pochi secondi e ha tre bottoni: Accendi, Spegni, Apri la dashboard. Parla con Gradiens attraverso la stessa interfaccia locale della CLI (`/api/stato`, `/api/spegni`), quindi vede anche un Gradiens partito all'accensione (`AMB-04`), e chiuderla non spegne Gradiens. Si apre con `gradiens pannello`; su Windows l'icona usa `pythonw.exe`, così non compare la finestra della console.

L'icona che apre il pannello, sul desktop e nel menu delle applicazioni (un collegamento `.lnk` su Windows, un file `.desktop` su Linux), si crea e si toglie con un interruttore nella sezione Avvio delle Impostazioni, e l'ultimo passo della configurazione iniziale propone di crearla. Le icone sono file dell'utente: non serve la conferma di amministratore.

Decisioni dell'utente dell'8 nov 2026.

## Opzioni considerate

- **Icona nell'area di notifica** (`pystray`): scartata. Mostra lo stato sempre, ma su Linux con Wayland (il KDE dell'utente) richiede PyGObject, che dentro la `.venv` di uv va compilato contro le librerie di sistema, e aggiunge due dipendenze. Si potrà aggiungere in seguito, per esempio solo su Windows.
- **Solo un collegamento "Apri Gradiens"** con il bottone Spegni nella dashboard: scartato. Da spento non si vede lo stato, e dopo lo spegnimento la pagina del browser resta aperta ma non funziona.
- **Icone create da un comando da terminale** (`gradiens pannello --crea-icone`): scartato. Chi non usa l'informatica dipenderebbe da chi gli installa Gradiens.

## Conseguenze

- Le icone sono la seconda eccezione di `PER-03`, dopo la registrazione dell'avvio all'accensione: stanno fuori dalla repository, ma si creano solo su richiesta e si tolgono con lo stesso interruttore.
- Il codice che crea e toglie le icone sta in `app/avvio_sistema.py`, con un ramo per Windows e uno per Linux (`AMB-03`). Su Windows il collegamento si crea con PowerShell (`WScript.Shell`), che trova il desktop vero anche quando è spostato su OneDrive. Su Linux il desktop si trova con `xdg-user-dir`, che dà il nome della cartella nella lingua del sistema (per esempio `Scrivania`).
- Tkinter è già nel Python installato da uv su Windows e su Linux: nessuna dipendenza nuova.
- Lo stato si vede solo con la finestra aperta.
