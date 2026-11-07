"""Registro delle esecuzioni."""

import json
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from gradiens.dati.modelli import Esecuzione
from gradiens.dati.notizie import adesso


def inizia(sessione: Session, avviata_da: str) -> Esecuzione:
    esecuzione = Esecuzione(avviata_il=adesso(), avviata_da=avviata_da, stato="in_corso")
    sessione.add(esecuzione)
    sessione.commit()
    return esecuzione


def termina(sessione: Session, id: int, stato: str, metriche: dict, motivo: str | None = None) -> None:
    esecuzione = sessione.get_one(Esecuzione, id)
    esecuzione.stato, esecuzione.motivo = stato, motivo
    esecuzione.finita_il = adesso()
    esecuzione.metriche = json.dumps(metriche, ensure_ascii=False)
    sessione.commit()


def segna_interrotte(sessione: Session) -> int:
    """All'avvio del servizio, un'esecuzione ancora "in corso" è stata interrotta (ESE-12)."""
    risultato = sessione.execute(
        update(Esecuzione)
        .where(Esecuzione.stato == "in_corso")
        .values(stato="interrotta", finita_il=adesso(), motivo="Gradiens è stato spento durante l'esecuzione.")
    )
    sessione.commit()
    return risultato.rowcount


def avviate_dal(sessione: Session, quando: datetime) -> bool:
    """C'è un'esecuzione avviata da `quando` (UTC) in poi? Serve al recupero all'avvio (ESE-01)."""
    return sessione.scalars(select(Esecuzione.id).where(Esecuzione.avviata_il >= quando).limit(1)).first() is not None


STATI_BUONI = ("ok", "nessun articolo nuovo")
CONTATORI = ("esaminate", "scartate_prefiltro", "scartate_valutazione", "escluse", "senza_contenuto",
             "oltre_tetto", "mostrate", "errori")


def storico(sessione: Session, limite: int = 20) -> list[Esecuzione]:
    return list(sessione.scalars(select(Esecuzione).order_by(Esecuzione.id.desc()).limit(limite)))


def riepilogo(esecuzione: Esecuzione) -> dict:
    """Metriche salvate (ESE-11) con i totali di tutte le fonti; vuote per un'esecuzione in corso.
    Le esecuzioni registrate prima della fetta 4b non hanno alcuni campi: si leggono con `.get`."""
    m = json.loads(esecuzione.metriche or "{}")
    fonti, token = m.get("fonti", {}), m.get("token", {})
    totali = {k: sum(f.get(k, 0) for f in fonti.values()) for k in CONTATORI}
    totali["token"] = sum(t.get("ingresso", 0) + t.get("uscita", 0) for t in token.values())

    def tutti(chiave: str) -> list[dict]:
        return [voce for f in fonti.values() for voce in f.get(chiave, [])]

    return {
        "durata_s": m.get("durata_s"), "fonti": fonti, "token": token, "totali": totali,
        # Prima siti e canali con un problema, poi quelli andati bene.
        "stati": sorted(tutti("stati"), key=lambda st: st["stato"] in STATI_BUONI),
        "problemi": tutti("problemi"), "escluse": tutti("notizie_escluse"),
    }


def ultima(sessione: Session) -> Esecuzione | None:
    return sessione.scalars(select(Esecuzione).order_by(Esecuzione.id.desc()).limit(1)).first()
