"""Testi del bot (TG-03..TG-08), in HTML di Telegram. I testi delle fonti sono dati esterni: sempre escapati."""

import re
from datetime import UTC, datetime
from html import escape

from gradiens.dashboard.comune import AVVIATA_DA, FONTI, durata, token_brevi
from gradiens.dati.esecuzioni import STATI_BUONI
from gradiens.dati.modelli import Esecuzione, Notizia
from gradiens.dati.notizie import nome_fonte

ICONE = {"siti": "🌐", "youtube": "▶️", "arxiv": "📄"}
MAX_TITOLO, MAX_RIASSUNTO = 120, 220  # 9 notizie stanno nei 4096 caratteri di un messaggio
MAX_PROBLEMI = 5  # fonti con un problema elencate nel messaggio: le altre sono nel resoconto
COMANDI = {
    "aggiorna": "avvia un'esecuzione",
    "stato": "esecuzione in corso o ultima conclusa, e prossima programmata",
    "ultima": "rimanda il messaggio dell'ultima esecuzione",
    "pausa": "sospende l'esecuzione programmata ogni giorno",
    "riprendi": "riattiva l'esecuzione programmata",
    "help": "elenca i comandi",
}


def _taglia(testo: str, massimo: int) -> str:
    return testo if len(testo) <= massimo else testo[:massimo - 1].rstrip() + "…"


def _due_frasi(riassunto: str) -> str:
    return _taglia(" ".join(re.split(r"(?<=[.!?])\s+", riassunto.strip())[:2]), MAX_RIASSUNTO)


def _quando(e: Esecuzione) -> str:
    """Le date nel database sono in UTC: si mostrano nell'ora del PC."""
    return f"{e.avviata_il.replace(tzinfo=UTC).astimezone():%d/%m alle %H:%M}"


def riga_metriche(r: dict) -> str:
    t = r["totali"]
    errori = "1 errore" if t["errori"] == 1 else f"{t['errori']} errori"
    return f"{t['esaminate']} esaminate · {t['mostrate']} mostrate · {durata(r['durata_s'])} · {errori} · {token_brevi(t['token'])} token"


def fine_esecuzione(e: Esecuzione, r: dict, gruppi: dict[str, list[Notizia]],
                    nomi_categorie: dict[str, str], avviso: str | None = None) -> tuple[str, list[Notizia]]:
    """TG-03, TG-04, ESE-13: testo del messaggio e notizie numerate, nell'ordine dei bottoni ❤️."""
    righe = [f"<b>Esecuzione {escape(e.stato)}</b> · {_quando(e)} · avviata da: {AVVIATA_DA.get(e.avviata_da, e.avviata_da)}"]
    if e.motivo:
        righe.append(f"Motivo: {escape(e.motivo)}")
    numerate: list[Notizia] = []
    for gruppo, elenco in gruppi.items():
        righe.append(f"\n{ICONE[gruppo]} <b>{FONTI[gruppo][1]}</b>")
        if not elenco:
            righe.append("nessuna notizia nuova")
        for n in elenco:
            numerate.append(n)
            migliore = n.pertinenze[0]
            righe.append(f'{len(numerate)}. <a href="{escape(n.url)}">{escape(_taglia(n.titolo_it or n.titolo, MAX_TITOLO))}</a>')
            righe.append(f"<i>{escape(nome_fonte(n.tipo, n.fonte, nomi_categorie))} · {escape(migliore.interesse.nome)} {migliore.punteggio}</i>")
            righe.append(escape(_due_frasi(n.riassunto)))
    righe.append(f"\n{riga_metriche(r)}")
    # Un sito in errore o un canale irraggiungibile si vedrebbero solo aprendo la dashboard.
    if problemi := [st for st in r["stati"] if st["stato"] not in STATI_BUONI]:
        righe.append("\n⚠️ <b>Fonti con problemi</b>")
        righe += [f"• {escape(st['fonte'])}: {escape(st['stato'])}" for st in problemi[:MAX_PROBLEMI]]
        if len(problemi) > MAX_PROBLEMI:
            righe.append(f"… e altre {len(problemi) - MAX_PROBLEMI}: le trovi nel resoconto, nella dashboard.")
    if avviso:  # es. il login di Claude Code che scade: lo si legge ogni giorno, senza aprire la dashboard
        righe.append(f"\n⚠️ {escape(avviso)}")
    return "\n".join(righe), numerate


def etichetta_cuore(numero: int, n: Notizia) -> str:
    return f"{'❤️' if n.cuore else '🤍'} {numero}. {_taglia(n.titolo_it or n.titolo, 28)}"


def stato(avanzamento, ultima: Esecuzione | None, r: dict | None, prossima: datetime | None) -> str:
    """TG-07: le stesse informazioni di `gradiens stato` (CLI-03)."""
    if avanzamento is not None:
        fatti = f": {avanzamento.fatti} di {avanzamento.totale}" if avanzamento.totale else ""
        righe = [f"Esecuzione in corso, fase {avanzamento.fase}{fatti}."]
    elif ultima is not None:
        righe = [f"Ultima esecuzione {escape(ultima.stato)} · {_quando(ultima)}"]
        if ultima.motivo:
            righe.append(f"Motivo: {escape(ultima.motivo)}")
        righe.append(riga_metriche(r))
    else:
        righe = ["Nessuna esecuzione ancora."]
    righe.append(f"Prossima esecuzione programmata: {prossima:%d/%m alle %H:%M}" if prossima else "Programmazione in pausa.")
    return "\n".join(righe)


def aiuto() -> str:
    """TG-06."""
    return "Comandi di Gradiens:\n" + "\n".join(f"/{c} – {spiegazione}" for c, spiegazione in COMANDI.items())
