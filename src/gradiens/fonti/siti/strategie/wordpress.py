"""API REST di WordPress, che filtra per data. robots.txt si controlla anche qui (ilsoftware.it vieta /wp-json/)."""

import json
from datetime import datetime, timedelta
from urllib.parse import urlencode, urljoin

from gradiens.fonti import Candidata
from gradiens.fonti.siti.date import da_iso, nella_finestra
from gradiens.fonti.siti.indirizzi import normalizza, titolo_da_url
from gradiens.fonti.siti.pagine import testo_semplice
from gradiens.fonti.siti.rete import Navigatore, Pagina
from gradiens.fonti.siti.strategie.raccolta import Raccolta

PER_PAGINA = 100


def _api(profilo, **parametri) -> str:
    return urljoin(profilo.url, "/wp-json/wp/v2/posts") + "?" + urlencode(parametri)


def _voci(pagina: Pagina) -> list | None:
    if not pagina.ok or pagina.html:
        return None
    try:
        voci = json.loads(pagina.dati)
    except ValueError:
        return None
    return voci if isinstance(voci, list) else None


def _reso(campo) -> str:
    return testo_semplice(str(campo.get("rendered", ""))) if isinstance(campo, dict) else ""


async def analizza(nav: Navigatore, profilo, pagina: Pagina | None) -> str | None:
    if profilo.piattaforma != "wordpress" or profilo.sezione:  # in una sezione darebbe gli articoli di tutto il sito
        return None
    voci = _voci(await nav.leggi(_api(profilo, per_page=1, _fields="link")))  # `leggi` rispetta robots.txt
    return "API WordPress" if voci else None


async def raccogli(nav: Navigatore, profilo, dal: datetime) -> Raccolta:
    r = Raccolta()
    # `after` usa l'ora locale del sito: un giorno di margine, poi si filtra su date_gmt.
    letta = await nav.leggi(_api(profilo, after=(dal - timedelta(days=1)).isoformat(), per_page=PER_PAGINA,
                                 _fields="link,date_gmt,title,excerpt"))
    voci = _voci(letta)
    if voci is None:
        if letta.ok:
            r.guasti.append(f"l'API di WordPress {letta.url} non risponde in JSON")
        else:
            r.errore(letta, "l'API di WordPress")
        return r
    r.riuscita = True
    r.copre = len(voci) < PER_PAGINA
    for v in voci:
        if not isinstance(v, dict):
            continue
        url = normalizza(str(v.get("link", "")))
        data = da_iso(str(v.get("date_gmt", "")))
        if url and data and nella_finestra(data, dal):
            r.candidate.append(Candidata(
                tipo="sito", url=url, fonte=profilo.dominio,
                titolo=_reso(v.get("title")) or titolo_da_url(url), sommario=_reso(v.get("excerpt")), contenuto="",
                pubblicata_il=data,
            ))
    return r
