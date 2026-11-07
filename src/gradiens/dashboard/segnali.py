"""Segnali delle sezioni delle Impostazioni (UI-14): "avvertimento" per problemi e dati mancanti,
"novita" per cose da guardare. Si ricalcolano a ogni richiesta, quindi spariscono da soli quando la
causa è risolta. Modelli LLM arriva con la 7a, rimandata agli sviluppi futuri.
"""

import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from gradiens.dati import esecuzioni, impostazioni, interessi, proposte
from gradiens.dati import siti as dati_siti
from gradiens.dati.esecuzioni import STATI_BUONI


@dataclass
class Segnale:
    tipo: str  # "avvertimento" o "novita"
    motivi: list[str] = field(default_factory=list)
    voci: set[str] = field(default_factory=set)  # voci da evidenziare dentro la sezione

    @property
    def motivo(self) -> str:
        return "; ".join(self.motivi)


def segnali(s: Session, problema_telegram: str | None = None, problema_avvio: str | None = None) -> dict[str, Segnale]:
    trovati: dict[str, Segnale] = {}

    def segnala(sezione: str, tipo: str, motivo: str, voce: str) -> None:
        segnale = trovati.setdefault(sezione, Segnale(tipo))
        if tipo == "avvertimento" and segnale.tipo == "novita":  # l'avvertimento prevale
            segnale.tipo, segnale.motivi = tipo, []
        if tipo == segnale.tipo:
            segnale.motivi.append(motivo)
        segnale.voci.add(voce)

    # Dati obbligatori (UI-11).
    if not interessi.elenca(s):
        segnala("interessi", "avvertimento", "Serve almeno un interesse", "aggiungi")
    for p in proposte.pendenti(s):  # INT-04, INT-06
        if p.interesse is not None:
            segnala("interessi", "novita", f"{p.interesse.nome}: proposta di raffinamento", f"proposta-{p.interesse_id}")
        else:
            segnala("interessi", "novita", f"Proposta di un nuovo interesse: {p.nome}", "proposta-nuovo")
    canali, elenco_siti = impostazioni.canali_youtube(s), dati_siti.elenca(s)
    if not (canali or elenco_siti or impostazioni.categorie_arxiv(s)):  # decisione 56: basta una fonte qualsiasi
        for sezione, voce in (("canali-youtube", "aggiungi"), ("siti", "aggiungi"), ("arxiv", "categorie")):
            segnala(sezione, "avvertimento", "Serve almeno una fonte: un canale YouTube, un sito o una categoria arXiv", voce)

    # Ultima esecuzione conclusa: canali irraggiungibili e tetto arXiv.
    conclusa = next((e for e in esecuzioni.storico(s, 2) if e.stato != "in_corso"), None)
    fonti = esecuzioni.riepilogo(conclusa)["fonti"] if conclusa else {}
    seguiti = {c.nome for c in canali}
    for st in fonti.get("youtube", {}).get("stati", []):
        if st["stato"] not in STATI_BUONI and st["fonte"] in seguiti:
            segnala("canali-youtube", "avvertimento", f"{st['fonte']}: {st['stato']}", f"canale-{st['fonte']}")
    if fonti.get("arxiv", {}).get("oltre_tetto"):
        segnala("arxiv", "novita", "Tetto di paper raggiunto nell'ultima esecuzione", "tetto")

    for sito in elenco_siti:
        voce = f"sito-{sito.id}"
        if sito.stato == "profilo rigenerato":
            segnala("siti", "novita", f"{sito.url}: profilo rigenerato", voce)
        elif sito.stato and sito.stato not in STATI_BUONI:
            segnala("siti", "avvertimento", f"{sito.url}: {sito.stato}", voce)
        nuovo = sito.stato in (None, "profilo rigenerato")  # proposte segnalate solo fino alla prossima raccolta
        if nuovo and not all(json.loads(sito.profilo).get("siti_collegati", {}).values()):
            segnala("siti", "novita", f"{sito.url}: siti collegati proposti", voce)

    if problema_telegram:  # bot non collegato (UI-11) o token non più valido
        segnala("telegram", "avvertimento", problema_telegram, "bot")
    if problema_avvio:  # registrazione dell'avvio all'accensione da rifare o incompleta (AMB-04)
        segnala("avvio", "avvertimento", problema_avvio, "stato")
    if impostazioni.leggi(s).programmazione_in_pausa:
        segnala("esecuzione", "novita", "La programmazione è in pausa", "pausa")
    return trovati


def globale(trovati: dict[str, Segnale]) -> tuple[str, Segnale] | None:
    """Per l'ingranaggio della sidebar: la sezione con il segnale più grave e il segnale da mostrare."""
    if not trovati:
        return None
    sezione = next((k for k, v in trovati.items() if v.tipo == "avvertimento"), next(iter(trovati)))
    if len(trovati) == 1:
        return sezione, trovati[sezione]
    return sezione, Segnale(trovati[sezione].tipo, [f"{len(trovati)} sezioni delle Impostazioni da guardare"])
