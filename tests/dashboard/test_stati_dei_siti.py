"""T-08 (docs/miglioramenti/02-test-e-copertura.md, decisione 26): per ogni stato di un sito, dove compare come
problema. Uno stato nuovo si aggiunge qui, decidendo in modo consapevole se è un problema: "copertura parziale"
(ADR 0011) non lo è, come il tetto arXiv raggiunto (decisione 63). `STATI_BUONI` è definito una volta sola, in `dati/esecuzioni.py`: i modelli Jinja lo ricevono
come globale da `dashboard/comune.py`."""

import re
from dataclasses import asdict

import pytest

from gradiens.app import cli
from gradiens.dashboard import segnali
from gradiens.dati import esecuzioni
from gradiens.dati import siti as dati_siti
from gradiens.esecuzione.metriche import Contatori
from gradiens.fonti.siti import Profilo
from gradiens.telegram import messaggi

# stato: (segnale in Impostazioni, problema in Telegram, CLI e ordine del resoconto,
#         classe in Impostazioni > Siti, classe nel resoconto); classe "" = né verde né rossa.
ATTESI = {
    "ok": (None, False, "ok", "ok"),
    "nessun articolo nuovo": (None, False, "", "ok"),
    "copertura parziale": (None, False, "", "ok"),  # WEB-26: non è un guasto
    "profilo rigenerato": ("novita", True, "", ""),
    "accesso bloccato": ("avvertimento", True, "errore", "errore"),
    "richiede JavaScript": ("avvertimento", True, "errore", "errore"),
    "nessuna strategia funzionante": ("avvertimento", True, "errore", "errore"),
    "errore di lettura": ("avvertimento", True, "errore", "errore"),
    "non raggiungibile": ("avvertimento", True, "errore", "errore"),
}


def classi(pagina: str, stato: str) -> set[str]:
    """Classi in più dello `<span class="stato …">` che mostra lo stato."""
    return {c.strip() for c in re.findall(rf'<span class="stato( ok| errore)?">{re.escape(stato)}</span>', pagina)}


@pytest.mark.parametrize("stato", ATTESI)
def test_dove_ogni_stato_di_un_sito_compare_come_problema(client, stato):
    segnale, problema, classe_impostazioni, classe_resoconto = ATTESI[stato]
    with client.app.state.sessioni() as s:
        sito = dati_siti.aggiungi(s, "https://sito.it/", Profilo(url="https://sito.it/").come_dict())
        dati_siti.registra_esito(s, sito.id, stato, "dettaglio dello stato", stato != "ok")
        conta = Contatori(stati=[{"fonte": "altro.it", "stato": "ok", "nuove": 1},
                                 {"fonte": "sito.it", "stato": stato, "dettaglio": "dettaglio dello stato", "nuove": 0}])
        metriche = {"durata_s": 3, "fonti": {"siti": asdict(conta)}, "token": {}}
        e = esecuzioni.inizia(s, "cli")
        esecuzioni.termina(s, e.id, "completata", metriche)
        trovato = segnali.segnali(s).get("siti")
        r = esecuzioni.riepilogo(e)
        telegram, _ = messaggi.fine_esecuzione(e, r, {}, {})

    # Impostazioni: il segnale della sezione Siti (dashboard/segnali.py).
    assert (trovato.tipo if trovato else None) == segnale
    # Resoconto, Telegram e CLI (dati/esecuzioni.py, telegram/messaggi.py, app/cli.py).
    assert [st["fonte"] for st in r["stati"]] == (["sito.it", "altro.it"] if problema else ["altro.it", "sito.it"])
    assert (f"• sito.it: {stato}" in telegram) is problema
    assert (f"  - sito.it: {stato}" in cli._riepilogo({"stato": "completata", "metriche": metriche})) is problema
    # Le due pagine (templates/impostazioni/siti.html e resoconto.html).
    pagina = client.get("/impostazioni/siti").text
    assert classi(pagina, stato) == {classe_impostazioni}
    assert ('class="riga evidenziata"' in pagina) is (classe_impostazioni == "errore")
    assert classi(client.get(f"/esecuzioni/{e.id}").text, stato) == {classe_resoconto}
