# Avvisi e versioni (15 novembre 2026)

Dati grezzi della fase 5 ([05-dipendenze-e-stile.md](../05-dipendenze-e-stile.md)). Commit `3868260`, Linux (Debian 13), Python 3.14.10, uv 0.13.7.

## Avvisi di deprecazione

Comando: `uv run --frozen pytest -q -p no:cacheprovider -W default::DeprecationWarning -W default::PendingDeprecationWarning -W default::FutureWarning`.

```
........................................................................ [ 39%]
........................................................................ [ 79%]
......................................                                   [100%]
```

## Versioni installate (`uv pip list`, da `uv.lock`)

```
Package                Version    Editable project location
---------------------- ---------- -------------------------------------------------
alembic                1.20.1
annotated-doc          0.0.5
annotated-types        0.8.0
anyio                  4.16.0
babel                  2.18.0
certifi                2026.10.23
charset-normalizer     3.5.2
click                  8.5.0
courlan                1.4.0
dateparser             1.5.0
defusedxml             0.7.1
fastapi                0.162.0
feedparser             6.0.14
feedparser-sgmllib     2.1.0
gradiens               0.1.0      /home/alessandro/Scrivania/apps/gradiens/Gradiens
h11                    0.16.0
htmldate               1.11.0
httpcore               1.0.9
httpcore2              2.16.0
httpx                  0.28.1
httpx2                 2.16.0
idna                   3.20
iniconfig              2.3.1
jinja2                 3.1.6
justext                3.0.2
lxml                   6.1.3
lxml-html-clean        0.4.6
mako                   1.4.3
markupsafe             3.0.4
opentelemetry-api      1.45.2
packaging              26.3
pluggy                 1.7.0
pydantic               2.14.2
pydantic-core          2.50.2
pydantic-settings      2.16.2
pygments               2.21.0
pytest                 9.2.0
python-dateutil        4.0.0
python-dotenv          1.2.4
python-multipart       0.0.33
python-telegram-bot    22.8
pytz                   2026.6
regex                  2026.9.29
requests               2.34.2
sqlalchemy             2.1.8
starlette              1.10.0
tld                    0.13.2
trafilatura            2.3.1
truststore             0.10.5
typing-extensions      4.16.0
typing-inspection      0.4.5
tzdata                 2026.6
tzlocal                5.4.5
urllib3                2.8.0
uvicorn                0.54.0
youtube-transcript-api 1.2.5
yt-dlp                 2026.10.26
```

## Esito

- **Deprecazioni**: 182 test verdi e **nessun avviso** `DeprecationWarning`, `PendingDeprecationWarning` o
  `FutureWarning`, né dal codice di Gradiens né dalle librerie durante i test.
- **Altri avvisi** (comando con `-W default`, cioè tutte le categorie): 118 `ResourceWarning: unclosed database
  in <sqlite3.Connection ...>` (connessioni SQLite non chiuse esplicitamente, emesse durante i test; da capire
  se vengono dalle fixture o dal codice dell'app) e 1 `ResourceWarning: subprocess ... is still running`.
- **Limite**: gli avvisi compaiono solo per il codice che i test eseguono (copertura 86,8% delle righe); le
  librerie delle fonti che fanno rete (yt-dlp, youtube-transcript-api) nei test sono in gran parte simulate.
