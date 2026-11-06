# Su Linux l'avvio all'accensione usa un servizio utente di systemd

Gradiens gira anche su Linux. L'unica parte che dipende dal sistema operativo è l'avvio all'accensione (`AMB-04`), che su Windows usa un'attività pianificata ([ADR 0005](0005-avvio-all-accensione-con-attivita-pianificata.md)).

Su Linux, quando l'interruttore è attivo, Gradiens scrive un servizio utente di systemd (`~/.config/systemd/user/gradiens.service`) e lo abilita con `systemctl --user enable --now gradiens`. Il servizio:
- lancia `gradiens avvia --primo-piano` con l'interprete della `.venv` del progetto e la cartella del progetto come cartella di lavoro;
- gira con l'utente che possiede la repository, quindi i file restano suoi;
- si riavvia da solo se l'app si blocca (`Restart=on-failure`), e i suoi messaggi finiscono anche nel registro di sistema (`journalctl --user -u gradiens`).

Perché parta all'accensione senza che l'utente acceda, serve il "lingering" dell'utente: `loginctl enable-linger <utente>`. Su molte distribuzioni l'utente può attivarlo per sé; dove serve la password di amministratore, la dashboard mostra il comando da lanciare in un terminale. Quando l'interruttore viene spento, il servizio si disabilita e il suo file si cancella. Il lingering invece resta, perché può servire ad altri servizi dell'utente.

## Opzioni considerate

- **Servizio di sistema** (`/etc/systemd/system`): scartato. Richiede i permessi di root per crearlo e gira come un utente di sistema, con i permessi sui file della repository da gestire a parte.
- **`@reboot` nel crontab dell'utente**: scartato come soluzione principale. È più semplice e non richiede il lingering, ma non riavvia l'app se si blocca e non ha un registro dei messaggi. Resta un'alternativa da documentare per i sistemi senza systemd.

## Conseguenze

- Il file del servizio sta fuori dalla repository, come l'attività pianificata su Windows: è l'eccezione di `PER-03`.
- Il codice che dipende dal sistema operativo sta tutto in un modulo, `app/avvio_sistema.py`, con un ramo per Windows e uno per Linux (`AMB-03`).
- Claude Code va installato e collegato all'account anche sulla macchina Linux. Su un server senza browser si usa `claude setup-token`.
- I test automatici girano su Ubuntu e su Windows a ogni push (`.github/workflows/test.yml`).
