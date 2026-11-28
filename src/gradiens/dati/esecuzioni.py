"""Registro delle esecuzioni."""

import json
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from gradiens.dati.modelli import Esecuzione
from gradiens.dati.notizie import adesso

SPENTO = "Gradiens è stato spento durante l'esecuzione."
NESSUNA_RETE = "Nessuna connessione a internet: controlla la rete e riprova."


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
        .values(stato="interrotta", finita_il=adesso(), motivo=SPENTO)
    )
    sessione.commit()
    return risultato.rowcount


def avviate_dal(sessione: Session, quando: datetime) -> bool:
    """C'è un'esecuzione avviata da `quando` (UTC) in poi? Serve al recupero (ESE-01). Quelle fallite per
    mancanza di rete non contano: un riavvio con la rete recupera la giornata (decisione 40)."""
    return (
        sessione.scalars(
            select(Esecuzione.id)
            .where(Esecuzione.avviata_il >= quando, Esecuzione.motivo.is_distinct_from(NESSUNA_RETE))
            .limit(1)
        ).first()
        is not None
    )


# Stati di un sito o di una fonte che non sono problemi: "copertura parziale" non è un guasto (WEB-26, decisione 63).
STATI_BUONI = ("ok", "nessun articolo nuovo", "copertura parziale")
CONTATORI = (
    "esaminate",
    "scartate_prefiltro",
    "scartate_valutazione",
    "escluse",
    "senza_contenuto",
    "oltre_tetto",
    "mostrate",
    "errori",
    "bloccate",
)


def storico(sessione: Session, limite: int = 20) -> list[Esecuzione]:
    return list(sessione.scalars(select(Esecuzione).order_by(Esecuzione.id.desc()).limit(limite)))


def versione_provata(sessione: Session, provider: str, limite: int = 50) -> str | None:
    """Versione del provider (es. Claude Code) dell'ultima esecuzione che l'ha usata dopo averla provata
    (decisione 45). None se non c'è: per esempio la prima volta, o dopo più di `limite` esecuzioni senza."""
    for esecuzione in storico(sessione, limite):
        v = json.loads(esecuzione.metriche or "{}").get("versione_llm") or {}
        if v.get("provider") == provider and v.get("provata"):
            return v.get("versione")
    return None


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
        "durata_s": m.get("durata_s"),
        "fonti": fonti,
        "token": token,
        "totali": totali,
        # Prima siti e canali con un problema, poi quelli andati bene.
        "stati": sorted(tutti("stati"), key=lambda st: st["stato"] in STATI_BUONI),
        "problemi": tutti("problemi"),
        "escluse": tutti("notizie_escluse"),
        "versione_llm": m.get("versione_llm"),
    }


def ultima(sessione: Session) -> Esecuzione | None:
    return sessione.scalars(select(Esecuzione).order_by(Esecuzione.id.desc()).limit(1)).first()
