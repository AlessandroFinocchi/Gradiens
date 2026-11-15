# Copertura della suite di test (13 novembre 2026)

Dati grezzi della fase 2 ([02-test-e-copertura.md](../02-test-e-copertura.md)). Commit `3868260`, Linux
(Debian 13), Python 3.14, 182 test verdi in circa 17 secondi.

**Metodo.** Nel progetto non ci sono né `coverage` né `pytest-cov`, e non è stato installato niente. La
copertura è stata misurata con la sola libreria standard: lo script [copertura.py.txt](copertura.py.txt)
(tenuto qui come allegato, non fa parte dell'app) registra con `sys.monitoring` ogni riga di `src/gradiens`
eseguita mentre gira `pytest`, in qualunque thread, e la confronta con le righe eseguibili di ogni file
(quelle che compaiono in `co_lines()` degli oggetti codice). Per rifarla, dalla cartella del progetto:
`uv run --frozen python <copia di copertura.py> <file di uscita.md>`.

**Limiti.** È copertura **per riga**, non per ramo: una riga con più condizioni conta come coperta se è stata
eseguita una volta. Le migrazioni Alembic sono escluse. I sottoprocessi non si contano. Una riga coperta non
dice che il suo comportamento sia verificato da un'asserzione. Misura fatta solo su Linux: i rami Windows di
`app/avvio_sistema.py` risultano coperti solo dove i test li simulano.

Esito di pytest: 0 (0 = tutti verdi). Righe eseguibili: 3987; coperte: 3462 (**86.8%**).

### Per pacchetto

| Pacchetto | Righe eseguibili | Coperte | % |
|---|---|---|---|
| `(radice)` | 3 | 1 | 33.3 |
| `app` | 721 | 468 | 64.9 |
| `dashboard` | 619 | 584 | 94.3 |
| `dati` | 576 | 565 | 98.1 |
| `esecuzione` | 514 | 473 | 92.0 |
| `fonti` | 1133 | 1024 | 90.4 |
| `llm` | 146 | 132 | 90.4 |
| `telegram` | 275 | 215 | 78.2 |

### Per modulo (dal meno coperto)

| Modulo | Righe eseguibili | Coperte | % | Righe non coperte |
|---|---|---|---|---|
| `__main__.py` | 2 | 0 | 0.0 | 1, 3 |
| `app/pannello.py` | 131 | 36 | 27.5 | 41-46, 48-69, 71-73, 76-78, 81-102, 105-109, 111-119, 122-124, 127-129, 131-138, 142, 144-148, 150-151, 154, 158-159 |
| `app/cli.py` | 153 | 78 | 51.0 | 33, 47, 49-50, 55-56, 69, 90-92, 96-97, 101, 103-112, 114-121, 127, 130-131, 143-151, 157-169, 171-179, 181-188, 190-191 |
| `fonti/siti/strategie/wordpress.py` | 51 | 26 | 51.0 | 26-27, 32, 43, 45-50, 52-65, 67 |
| `llm/__init__.py` | 8 | 5 | 62.5 | 10-12 |
| `telegram/bot.py` | 206 | 152 | 73.8 | 53, 56, 65, 68-71, 78-79, 88, 107-123, 125-128, 130-134, 139-143, 171, 177-178, 183, 186-187, 193-196, 225, 267, 271 |
| `fonti/youtube/__init__.py` | 95 | 71 | 74.7 | 71-73, 78-85, 109-111, 119-128 |
| `app/servizio.py` | 106 | 81 | 76.4 | 55, 66, 76, 84-91, 102, 124-128, 130, 135-141 |
| `app/avvio_sistema.py` | 242 | 195 | 80.6 | 27-28, 30-32, 89, 99, 105-108, 154, 164, 196, 217, 222, 224-226, 230-238, 257-260, 271-273, 285-288, 298-301, 369-372 |
| `app/aggiornamento.py` | 53 | 43 | 81.1 | 23-24, 31, 33, 39, 42, 54, 58, 61-62 |
| `fonti/siti/strategie/raccolta.py` | 19 | 16 | 84.2 | 19, 21, 23 |
| `esecuzione/programmatore.py` | 56 | 48 | 85.7 | 54-55, 73-78 |
| `dashboard/rotte_impostazioni.py` | 252 | 223 | 88.5 | 130, 191, 199, 219-224, 239, 273, 276-277, 279, 287, 290-291, 301-305, 310-314, 341-342 |
| `fonti/siti/rete.py` | 152 | 135 | 88.8 | 72-74, 115, 123, 135, 148, 153, 163, 165-167, 181, 187-190 |
| `llm/base.py` | 18 | 16 | 88.9 | 27, 31 |
| `dati/impostazioni.py` | 74 | 67 | 90.5 | 31-32, 35, 57-60 |
| `telegram/messaggi.py` | 69 | 63 | 91.3 | 45, 49, 80-81, 85, 88 |
| `fonti/siti/strategie/sitemap.py` | 93 | 85 | 91.4 | 32-33, 35, 44, 71, 91, 99, 109 |
| `esecuzione/esecutore.py` | 376 | 344 | 91.5 | 98-102, 108, 208, 214, 218, 224-226, 236-237, 246, 250, 312-315, 338, 348, 350, 372-377, 382, 392, 431 |
| `llm/claude_code.py` | 106 | 97 | 91.5 | 31-37, 55, 109 |
| `fonti/arxiv/__init__.py` | 53 | 49 | 92.5 | 30, 33, 52, 57 |
| `fonti/siti/strategie/html.py` | 93 | 86 | 92.5 | 26, 67, 69-70, 75, 101, 115 |
| `fonti/siti/estrazione.py` | 47 | 44 | 93.6 | 44, 52, 54 |
| `fonti/siti/pagine.py` | 90 | 85 | 94.4 | 21-22, 66, 121, 123 |
| `fonti/siti/date.py` | 68 | 65 | 95.6 | 56, 69, 87 |
| `fonti/siti/indirizzi.py` | 72 | 69 | 95.8 | 42-43, 50 |
| `fonti/siti/__init__.py` | 123 | 119 | 96.7 | 50, 127, 137, 153 |
| `dati/notizie.py` | 95 | 92 | 96.8 | 52, 62, 77 |
| `app/configurazione.py` | 36 | 35 | 97.2 | 60 |
| `dati/interessi.py` | 38 | 37 | 97.4 | 20 |
| `dashboard/comune.py` | 86 | 84 | 97.7 | 67, 70 |
| `fonti/siti/strategie/feed.py` | 86 | 84 | 97.7 | 35, 88 |
| `dashboard/segnali.py` | 61 | 60 | 98.4 | 45 |
| `fonti/siti/profilo.py` | 68 | 67 | 98.5 | 73 |
| `dashboard/rotte_configurazione.py` | 70 | 69 | 98.6 | 76 |
| `dashboard/rotte.py` | 150 | 148 | 98.7 | 93-94 |
| `esecuzione/prompt.py` | 82 | 81 | 98.8 | 20 |
| `__init__.py` | 1 | 1 | 100.0 | – |
| `dati/argomenti.py` | 62 | 62 | 100.0 | – |
| `dati/database.py` | 55 | 55 | 100.0 | – |
| `dati/esecuzioni.py` | 44 | 44 | 100.0 | – |
| `dati/modelli.py` | 115 | 115 | 100.0 | – |
| `dati/proposte.py` | 55 | 55 | 100.0 | – |
| `dati/siti.py` | 38 | 38 | 100.0 | – |
| `fonti/__init__.py` | 20 | 20 | 100.0 | – |
| `fonti/siti/strategie/__init__.py` | 3 | 3 | 100.0 | – |
| `llm/finto.py` | 14 | 14 | 100.0 | – |

### Funzioni mai eseguite dai test

| Modulo | Funzione | Riga | Righe del corpo |
|---|---|---|---|
| `app/avvio_sistema.py` | `_come_amministratore` | 229 | 9 |
| `app/avvio_sistema.py` | `_esegui` | 104 | 4 |
| `app/avvio_sistema.py` | `_powershell` | 216 | 1 |
| `app/avvio_sistema.py` | `_pythonw` | 269 | 3 |
| `app/avvio_sistema.py` | `_sessione_senza_desktop` | 220 | 4 |
| `app/avvio_sistema.py` | `_stato_windows` | 256 | 4 |
| `app/avvio_sistema.py` | `_utente_windows` | 195 | 1 |
| `app/avvio_sistema.py` | `eseguibile` | 366 | 4 |
| `app/cli.py` | `_riepilogo` | 100 | 19 |
| `app/cli.py` | `main` | 154 | 32 |
| `app/configurazione.py` | `configurazione` | 58 | 1 |
| `app/pannello.py` | `Pannello.__init__` | 40 | 31 |
| `app/pannello.py` | `Pannello._controlla` | 80 | 22 |
| `app/pannello.py` | `Pannello._imposta_passo` | 153 | 1 |
| `app/pannello.py` | `Pannello._leggi_sempre` | 75 | 3 |
| `app/pannello.py` | `Pannello._mostra` | 104 | 14 |
| `app/pannello.py` | `Pannello._premi_accendi` | 121 | 3 |
| `app/pannello.py` | `Pannello._premi_aggiorna` | 141 | 4 |
| `app/pannello.py` | `Pannello._premi_aggiorna.<locals>.lavora` | 144 | 4 |
| `app/pannello.py` | `Pannello._premi_spegni` | 126 | 11 |
| `app/pannello.py` | `apri` | 157 | 2 |
| `app/servizio.py` | `ciclo_di_vita` | 81 | 8 |
| `app/servizio.py` | `configura_log` | 123 | 6 |
| `app/servizio.py` | `esegui` | 133 | 7 |
| `dashboard/rotte_impostazioni.py` | `escludi_percorso` | 189 | 1 |
| `dashboard/rotte_impostazioni.py` | `rigenera_profilo` | 217 | 6 |
| `dashboard/rotte_impostazioni.py` | `scarta_proposta` | 128 | 1 |
| `dashboard/rotte_impostazioni.py` | `telegram_cambia_chat` | 308 | 5 |
| `dashboard/rotte_impostazioni.py` | `telegram_prova` | 299 | 5 |
| `dashboard/rotte_impostazioni.py` | `tetto_arxiv` | 237 | 1 |
| `dati/impostazioni.py` | `__annotate__` | 30 | 2 |
| `dati/impostazioni.py` | `salva_tetto_arxiv` | 56 | 4 |
| `dati/notizie.py` | `__annotate__` | 76 | 1 |
| `esecuzione/esecutore.py` | `Esecutore.__annotate__` | 217 | 1 |
| `esecuzione/esecutore.py` | `Esecutore.__annotate__` | 381 | 1 |
| `esecuzione/esecutore.py` | `Esecutore.__annotate__` | 430 | 1 |
| `esecuzione/esecutore.py` | `rete_disponibile` | 96 | 5 |
| `esecuzione/programmatore.py` | `Programmatore.gira` | 72 | 6 |
| `fonti/siti/profilo.py` | `Profilo.aggiungi_sezione` | 72 | 1 |
| `fonti/siti/strategie/wordpress.py` | `_reso` | 31 | 1 |
| `fonti/siti/strategie/wordpress.py` | `raccogli` | 42 | 22 |
| `fonti/youtube/__init__.py` | `_info` | 70 | 3 |
| `fonti/youtube/__init__.py` | `raccogli` | 106 | 3 |
| `fonti/youtube/__init__.py` | `risolvi_canale` | 76 | 8 |
| `llm/__init__.py` | `crea_provider` | 9 | 3 |
| `llm/base.py` | `Provider.chiedi` | 29 | 1 |
| `llm/base.py` | `Provider.pronto` | 25 | 1 |
| `llm/claude_code.py` | `trova_eseguibile` | 29 | 7 |
| `telegram/bot.py` | `BotGradiens.__annotate__` | 87 | 1 |
| `telegram/bot.py` | `BotGradiens._registra` | 191 | 4 |
| `telegram/bot.py` | `BotGradiens.avvia` | 106 | 26 |
| `telegram/messaggi.py` | `__annotate__` | 44 | 1 |
