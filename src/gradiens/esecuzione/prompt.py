"""Istruzioni e schemi per i due ruoli LLM (PRD ESE-04, ESE-05, INT-03).

La parte fissa (istruzioni e interessi) va nel prompt di sistema, uguale per tutte le chiamate di
un'esecuzione, così Claude la rilegge dalla cache; la notizia va nel messaggio (ADR 0006).
"""

import json

from gradiens.dati.modelli import Interesse
from gradiens.fonti import Candidata

MAX_SOMMARIO = 1500  # caratteri per notizia nel pre-filtro: bastano titolo e inizio del sommario


def _interessi(interessi: list[Interesse]) -> str:
    righe = []
    for i in interessi:
        righe.append(f"[{i.id}] {i.nome}: {i.descrizione}")
        if i.raffinamento:
            righe.append(f"    Raffinamento: {i.raffinamento}")
    return "\n".join(righe)


def sistema_prefiltro(interessi: list[Interesse], escludi_sponsorizzati: bool = True) -> str:
    esclusione = ("\nEscludi i contenuti sponsorizzati e le offerte commerciali: non metterli tra i pertinenti"
                  " e restituisci i loro id in `sponsorizzate`." if escludi_sponsorizzati else "")  # WEB-22/23
    return f"""Sei il pre-filtro di Gradiens, un'app che seleziona notizie per un utente.

Interessi dell'utente, con il loro id:
{_interessi(interessi)}

Ricevi un elenco di notizie in JSON, ognuna con id, titolo e sommario, in qualsiasi lingua.
Restituisci gli id delle notizie che possono essere pertinenti ad almeno un interesse.
Nel dubbio includi la notizia: un passaggio successivo leggerà il contenuto completo.{esclusione}"""


SCHEMA_PREFILTRO = {
    "type": "object",
    "properties": {
        "pertinenti": {"type": "array", "items": {"type": "integer"}},
        "sponsorizzate": {"type": "array", "items": {"type": "integer"}},  # facoltativo (WEB-23)
    },
    "required": ["pertinenti"],
}


def messaggio_prefiltro(blocco: list[Candidata]) -> str:
    voci = [{"id": n, "titolo": c.titolo, "sommario": c.sommario[:MAX_SOMMARIO]} for n, c in enumerate(blocco)]
    return json.dumps(voci, ensure_ascii=False)


def sistema_valutazione(interessi: list[Interesse]) -> str:
    return f"""Sei il valutatore di Gradiens, un'app che seleziona e riassume notizie per un utente italiano.

Interessi dell'utente, con il loro id:
{_interessi(interessi)}

Ricevi una notizia in JSON (tipo, fonte, titolo, testo), in qualsiasi lingua. Restituisci:
- punteggi: per ogni interesse pertinente, la pertinenza da 0 a 100. 90-100: è esattamente ciò che
  l'utente cerca; 60-89: pertinente e utile; sotto 60: marginale. Ometti gli interessi non pertinenti.
- riassunto: in italiano, corretto e completo. Riporta solo ciò che c'è nel testo, senza aggiunte né
  opinioni, e copri tutti i punti principali, non solo l'inizio. Da 3 a 6 frasi.
  Se il testo è chiaramente incompleto, dillo nella prima frase.
- titolo_it: la traduzione italiana del titolo se il titolo non è in italiano, altrimenti una stringa vuota."""


SCHEMA_VALUTAZIONE = {
    "type": "object",
    "properties": {
        "punteggi": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "interesse": {"type": "integer"},
                    "pertinenza": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["interesse", "pertinenza"],
            },
        },
        "riassunto": {"type": "string"},
        "titolo_it": {"type": "string"},
    },
    "required": ["punteggi", "riassunto", "titolo_it"],
}


def messaggio_valutazione(c: Candidata) -> str:
    return json.dumps({"tipo": c.tipo, "fonte": c.fonte, "titolo": c.titolo, "testo": c.contenuto}, ensure_ascii=False)
