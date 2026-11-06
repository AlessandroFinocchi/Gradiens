# Gradiens

Raccoglie notizie da YouTube, arXiv e siti web, le filtra con un LLM in base ai tuoi interessi e le riassume in italiano. È un'app personale: gira sul tuo PC (Windows o Linux) e si usa da una dashboard web.

Requisiti completi: [docs/requisiti/prd.md](docs/requisiti/prd.md). Architettura: [docs/architettura/](docs/architettura/).

## Cosa serve

- **Python 3.14** e **[uv](https://docs.astral.sh/uv/)**, che installa le dipendenze nella cartella `.venv` del progetto.
- **Claude Code** installato e collegato al tuo account Claude (per esempio Pro): è il motore che filtra e riassume, e usa la quota del tuo abbonamento senza costi in più ([ADR 0006](docs/adr/0006-claude-code-come-provider-predefinito.md)). Su una macchina senza browser il collegamento si fa con `claude setup-token`.

## Installazione

Su Windows (PowerShell) e su Linux i comandi sono gli stessi:

```
git clone https://github.com/AlessandroFinocchi/Gradiens.git
cd Gradiens
uv sync
uv run pytest
```

Se `uv` è stato installato con `pip` e non è nel PATH, usa `python -m uv` al posto di `uv`.

## Uso

```
uv run gradiens avvia     # dashboard, esecuzioni e (in futuro) bot Telegram, staccati dal terminale
uv run gradiens esegui    # lancia un'esecuzione e ne mostra l'avanzamento
uv run gradiens stato     # dice se Gradiens è in esecuzione
uv run gradiens spegni    # termina l'applicazione
```

Poi apri http://127.0.0.1:8765/notizie e, dall'ingranaggio in basso a sinistra, configura interessi, siti, canali YouTube e categorie arXiv.

`gradiens avvia` stacca l'app dal terminale, quindi continua a girare anche se chiudi la sessione SSH. Con `--primo-piano` resta collegata al terminale, il che è utile per il debug.

## Dove stanno i dati

Tutto resta nella cartella del progetto, escluso da git ([PRD PER-02, PER-03](docs/requisiti/prd.md)):

- `.env`: segreti e opzioni di avvio (prefisso `GRADIENS_`, per esempio `GRADIENS_PORTA=8765`);
- `.gradiens/`: database, log e cache.

Cancellando la cartella si cancella tutto. Un clone nuovo parte senza configurazione: per spostare Gradiens su un altro PC copia anche `.gradiens/` e `.env`.

## Avvio all'accensione

È previsto per Windows (attività pianificata, [ADR 0005](docs/adr/0005-avvio-all-accensione-con-attivita-pianificata.md)) e per Linux (servizio utente di systemd, [ADR 0007](docs/adr/0007-avvio-all-accensione-su-linux-con-systemd.md)). Arriva con l'ultima fetta del [piano](docs/architettura/piano-fase-4.md).

## Sviluppo

- Test: `uv run pytest`. Girano anche su GitHub, su Ubuntu e su Windows, a ogni push ([workflow](.github/workflows/test.yml)).
- Regole di lavoro e definizione di "fatto": [CLAUDE.md](CLAUDE.md).
