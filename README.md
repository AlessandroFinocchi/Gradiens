# Gradiens

Raccoglie notizie da YouTube, arXiv e siti web, le filtra con un LLM in base ai tuoi interessi e le riassume in italiano. È un'app personale: gira sul tuo PC (Windows o Linux) e si usa da una dashboard web.

Requisiti completi: [docs/requisiti/prd.md](docs/requisiti/prd.md). Architettura: [docs/architettura/](docs/architettura/).

## Cosa serve

- **[uv](https://docs.astral.sh/uv/)**, che scarica da solo Python 3.14 se manca (la versione è fissata in `.python-version`, uguale su Windows e su Linux) e installa le dipendenze nella cartella `.venv` del progetto.
- **Claude Code** installato e collegato al tuo account Claude (per esempio Pro): è il motore che filtra e riassume, e usa la quota del tuo abbonamento senza costi in più ([ADR 0006](docs/adr/0006-claude-code-come-provider-predefinito.md)). Su una macchina senza browser il collegamento si fa con `claude setup-token`.
- **git**.

## Installazione

### 1. uv e Claude Code

**Windows** (PowerShell):

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
irm https://claude.ai/install.ps1 | iex
```

Se `uv` è stato installato con `pip` e non è nel PATH, usa `python -m uv` al posto di `uv`.

**Linux** (non servono permessi di amministratore):

```
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://claude.ai/install.sh | bash
```

Entrambi installano in `~/.local/bin`, che deve essere nel `PATH` (su Debian e Ubuntu lo è dopo un nuovo accesso).

Poi, su tutti e due i sistemi, collega Claude Code all'account con `claude` (o `claude setup-token` senza browser) e controlla con `claude auth status`.

### 2. Gradiens

I comandi sono gli stessi su Windows (PowerShell) e su Linux:

```
git clone https://github.com/AlessandroFinocchi/Gradiens.git
cd Gradiens
uv sync
uv run pytest
```

## Uso

```
uv run gradiens avvia     # dashboard, esecuzioni e bot Telegram, staccati dal terminale
uv run gradiens esegui    # lancia un'esecuzione e ne mostra l'avanzamento
uv run gradiens stato     # dice se Gradiens è in esecuzione
uv run gradiens spegni    # termina l'applicazione
```

Poi apri http://127.0.0.1:8765/. La prima volta si apre la configurazione iniziale, in quattro passi: interessi, fonti (basta un canale YouTube, un sito o una categoria arXiv), Claude Code e bot Telegram, con un tutorial passo dopo passo. Dopo, tutto si cambia dall'ingranaggio in basso a sinistra. Dal bot puoi poi usare `/aggiorna`, `/stato`, `/ultima`, `/pausa`, `/riprendi` e `/help`.

`gradiens avvia` stacca l'app dal terminale, quindi continua a girare anche se chiudi il terminale o la sessione SSH, su Windows come su Linux. Con `--primo-piano` resta collegata al terminale, il che è utile per il debug.

## Dove stanno i dati

Tutto resta nella cartella del progetto, escluso da git ([PRD PER-02, PER-03](docs/requisiti/prd.md)):

- `.env`: segreti e opzioni di avvio (prefisso `GRADIENS_`, per esempio `GRADIENS_PORTA=8765`), compreso il token del bot Telegram, che la dashboard scrive da sola;
- `.gradiens/`: database, log e cache.

Cancellando la cartella si cancella tutto. Un clone nuovo parte senza configurazione: per spostare Gradiens su un altro PC copia anche `.gradiens/` e `.env`.

## Avvio all'accensione

Si accende dalla dashboard, nelle Impostazioni, sezione **Avvio**. Gradiens parte poi a ogni accensione del PC, senza bisogno di accedere al sistema: basta accendere il PC e lanciare l'esecuzione dal bot Telegram.

- **Windows** ([ADR 0005](docs/adr/0005-avvio-all-accensione-con-attivita-pianificata.md)): Gradiens registra un'attività pianificata "Gradiens". Windows chiede la conferma di amministratore sullo schermo del PC, quindi l'interruttore va cambiato stando al PC. Se la conferma non può comparire (per esempio quando Gradiens è stato avviato proprio all'accensione), la dashboard mostra i comandi da incollare in PowerShell aperto come amministratore.
- **Linux** ([ADR 0007](docs/adr/0007-avvio-all-accensione-su-linux-con-systemd.md)): Gradiens scrive il servizio utente `~/.config/systemd/user/gradiens.service` e attiva il "lingering" (`loginctl enable-linger`), che fa partire i servizi dell'utente senza accesso. Se la distribuzione chiede la password per il lingering, la dashboard mostra il comando da lanciare con `sudo`. I messaggi del servizio si leggono con `journalctl --user -u gradiens`.

Vale dal prossimo avvio del PC. Spegnendo l'interruttore la registrazione si toglie (su Linux il lingering resta, perché può servire ad altri servizi). Se sposti la cartella di Gradiens, spegni e riaccendi l'interruttore.

## Sviluppo

Gradiens si sviluppa sia su Windows sia su Linux: ogni modifica deve funzionare su entrambi.

- Test: `uv run pytest`. Girano anche su GitHub, su Ubuntu e su Windows, a ogni push ([workflow](.github/workflows/test.yml)).
- Regole di lavoro e definizione di "fatto": [CLAUDE.md](CLAUDE.md).

### Strumenti per Claude Code

La definizione di "fatto" usa `/ponytail-review` e la review con `ocr`. Servono [Node.js](https://nodejs.org/) (LTS) e poi, con gli stessi comandi su Windows e su Linux:

```
npm i -g @alibaba-group/open-code-review
npx skills add DietrichGebert/ponytail -g --agent claude-code -y
npx skills add alibaba/open-code-review -g --agent claude-code -y
npx skills add mattpocock/skills -g --agent claude-code -y
```

Le skill finiscono nella cartella utente di Claude Code (`~/.claude/skills`, su Windows `%USERPROFILE%\.claude\skills`), non nella repository. `ocr` va poi collegato a un LLM (variabili `OCR_LLM_*` o `~/.opencodereview/config.json`) e si controlla con `ocr llm test`.

Node.js si installa dal sito su Windows. Su Linux, senza permessi di amministratore, si può estrarre l'archivio ufficiale in `~/.local/opt/node`, collegare `node`, `npm` e `npx` in `~/.local/bin` e lanciare `npm config set prefix ~/.local`, così anche `npm i -g` scrive in `~/.local/bin`.
