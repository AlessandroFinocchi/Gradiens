"""Ambiente Alembic: usa la connessione passata da `database.migra`."""

from alembic import context

from gradiens.dati.modelli import Base

connessione = context.config.attributes["connection"]
# render_as_batch: SQLite non supporta quasi nessun ALTER TABLE, Alembic ricrea la tabella.
context.configure(connection=connessione, target_metadata=Base.metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
