# I dati stanno in SQLite, letti e scritti con SQLAlchemy 2.0 e migrati con Alembic

Tutti i dati dell'app (notizie, archivio, interessi, profili dei siti, argomenti, esecuzioni, registro delle notizie già viste) stanno in un unico file SQLite, dentro la repository ed escluso da git (`PER-02`). Il codice accede ai dati con SQLAlchemy 2.0, con tabelle descritte come classi Python e query tipizzate. Ogni cambio di struttura del database passa da una migrazione Alembic, che aggiorna il file esistente senza perdere dati. Serve soprattutto perché l'archivio è permanente.

## Opzioni considerate

- **SQLModel**: scartato. È più semplice all'inizio, ma è meno maturo, e per i filtri combinati e gli ordinamenti si ricade comunque su SQLAlchemy.
- **SQL scritto a mano con `sqlite3`**: scartato. Le modifiche di struttura andrebbero gestite a mano, con rischi per l'archivio, e i filtri combinabili di `UI-06` richiederebbero di concatenare stringhe SQL.
- **Un server di database (PostgreSQL)**: scartato. Per un solo utente basta SQLite, e un server andrebbe installato e gestito fuori dalla repository, contro `PER-03`.

## Conseguenze

- All'avvio l'app applica le migrazioni mancanti, così un aggiornamento del codice non richiede passaggi manuali.
- SQLite gestisce bene un solo processo che scrive. Questo coincide con l'[ADR 0003](0003-dashboard-generata-dal-server.md): dashboard, bot e programmazione girano nello stesso processo.
- Fare il backup dell'app significa copiare un file. Cancellare la cartella cancella tutto (`PER-03`).
