"""Istruzioni e schemi per i due ruoli LLM (PRD ESE-04, ESE-05, INT-03).

La parte fissa (istruzioni e interessi) va nel prompt di sistema, uguale per tutte le chiamate di
un'esecuzione, così Claude la rilegge dalla cache; la notizia va nel messaggio (ADR 0006).
"""

import json

from gradiens.dati.modelli import Argomento, Interesse, Notizia
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


def sistema_argomenti(argomenti: list[Argomento]) -> str:
    """ESE-08, ADR 0008: un passo unico per tutte le notizie mostrate dall'esecuzione."""
    elenco = "\n".join(f"[{a.id}] {a.nome}" for a in argomenti) or "(nessuno)"
    return f"""Sei il passo degli argomenti di Gradiens. Un argomento è un singolo evento preciso e la sua
evoluzione nel tempo (es. "Attacco ransomware all'ASL Valle Verde"), non un tema generale
(non "attacchi ransomware", non "intelligenza artificiale").

Argomenti esistenti, con il loro id:
{elenco}

Ricevi notizie in JSON con id, titolo e riassunto. Per ogni notizia restituisci il suo id e:
- argomento: l'id di un argomento esistente, se la notizia segue proprio quell'evento;
- oppure nuovo: il nome di un argomento nuovo, breve e in italiano, se la notizia riguarda un evento
  preciso che può avere sviluppi. Dai lo stesso nome alle notizie dello stesso evento;
- oppure nessuno dei due, se la notizia non riguarda un evento preciso (guide, paper, opinioni)."""


SCHEMA_ARGOMENTI = {
    "type": "object",
    "properties": {"assegnazioni": {"type": "array", "items": {
        "type": "object",
        "properties": {"notizia": {"type": "integer"}, "argomento": {"type": "integer"}, "nuovo": {"type": "string"}},
        "required": ["notizia"],
    }}},
    "required": ["assegnazioni"],
}


def messaggio_argomenti(blocco: list[Notizia]) -> str:
    voci = [{"id": i, "titolo": n.titolo_it or n.titolo, "riassunto": n.riassunto[:600]} for i, n in enumerate(blocco)]
    return json.dumps(voci, ensure_ascii=False)


def _notizie_con_cuore(notizie: list[Notizia]) -> str:
    voci = [{"titolo": n.titolo_it or n.titolo, "riassunto": n.riassunto[:600]} for n in notizie]
    return json.dumps(voci, ensure_ascii=False)


def sistema_raffinamento(interesse: Interesse) -> str:
    """INT-04: il raffinamento precisa l'interesse; la descrizione dell'utente non si cambia."""
    return f"""Sei l'assistente di Gradiens che propone il raffinamento di un interesse dell'utente.

Interesse: {interesse.nome}
Descrizione scritta dall'utente (non va cambiata né ripetuta): {interesse.descrizione}
Raffinamento attuale: {interesse.raffinamento or "(nessuno)"}

Ricevi in JSON le notizie a cui l'utente ha messo il cuore. Capisci cosa hanno in comune e restituisci
in raffinamento un nuovo testo che sostituisce quello attuale: in italiano, da 1 a 3 frasi, che dica
cosa interessa di più all'utente dentro questo interesse. Tieni ciò che resta valido del raffinamento
attuale. Se le notizie non aggiungono niente, restituisci una stringa vuota."""


SCHEMA_RAFFINAMENTO = {"type": "object", "properties": {"raffinamento": {"type": "string"}}, "required": ["raffinamento"]}


def sistema_nuovo_interesse(interessi: list[Interesse]) -> str:
    """INT-06, decisione 57: è l'LLM a decidere se i cuori rivelano un tema che gli interessi non coprono."""
    return f"""Sei l'assistente di Gradiens che propone nuovi interessi all'utente.

Interessi che l'utente ha già:
{_interessi(interessi)}

Ricevi in JSON le ultime notizie a cui l'utente ha messo il cuore, ciascuna con il punteggio di
pertinenza (0-100) che ha avuto per i suoi interessi. Chiediti se almeno 3 di queste notizie hanno in
comune un tema che gli interessi esistenti non coprono già, nemmeno in parte: un tema nuovo, non un
aspetto di un interesse che c'è già (per quello esiste il raffinamento). Solo in quel caso proponi un
interesse nuovo: nome (breve, al massimo 5 parole) e descrizione (1 o 2 frasi in italiano, come la
scriverebbe l'utente). Altrimenti, che è il caso più comune, restituisci nome e descrizione vuoti."""


SCHEMA_NUOVO_INTERESSE = {
    "type": "object",
    "properties": {"nome": {"type": "string"}, "descrizione": {"type": "string"}},
    "required": ["nome", "descrizione"],
}


def messaggio_proposta(notizie: list[Notizia]) -> str:
    return _notizie_con_cuore(notizie)


def messaggio_nuovo_interesse(notizie: list[Notizia]) -> str:
    voci = [{"titolo": n.titolo_it or n.titolo, "riassunto": n.riassunto[:600],
             "punteggi": {p.interesse.nome: p.punteggio for p in n.pertinenze}} for n in notizie]
    return json.dumps(voci, ensure_ascii=False)

