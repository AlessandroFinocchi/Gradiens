"""Avanzamento e metriche di un'esecuzione (ESE-11, UI-03).

Le metriche si salvano in `esecuzioni.metriche` e le leggono `dati.esecuzioni.riepilogo`, la CLI, Telegram e il
resoconto: una chiave si aggiunge, non si toglie né si rinomina (T-30, `tests/dati/test_esecuzioni.py`).
"""

from dataclasses import dataclass, field

from gradiens.dati.modelli import FONTE_DI_TIPO
from gradiens.fonti import Candidata


@dataclass
class Avanzamento:
    esecuzione_id: int
    fase: str = "raccolta"
    fatti: int = 0
    totale: int = 0

    def inizia_fase(self, fase: str, totale: int) -> None:
        self.fase, self.fatti, self.totale = fase, 0, totale


@dataclass
class Contatori:
    """ESE-11 per un tipo di fonte, per il resoconto (UI-03). `stati`: un elemento per sito, canale o
    arXiv; `problemi`: notizie senza contenuto (es. "trascrizione assente", YT-05); `notizie_escluse`:
    notizie scartate per WEB-23, con il motivo."""

    raccolta_s: float = 0  # le fonti di un tipo si leggono in parallelo: conta la più lenta
    esaminate: int = 0
    scartate_prefiltro: int = 0
    oltre_tetto: int = 0
    escluse: int = 0  # es. articoli a pagamento con l'esclusione attiva (WEB-23)
    senza_contenuto: int = 0
    scartate_valutazione: int = 0
    mostrate: int = 0
    errori: int = 0
    bloccate: int = 0  # rimandate perché la fonte ha limitato le richieste (es. YouTube): non sono errori
    stati: list[dict] = field(default_factory=list)
    problemi: list[dict] = field(default_factory=list)
    notizie_escluse: list[dict] = field(default_factory=list)


@dataclass
class Metriche:
    fonti: dict[str, Contatori] = field(default_factory=dict)
    token: dict = field(
        default_factory=lambda: {r: {"ingresso": 0, "uscita": 0} for r in ("prefiltro", "elaborazione")}
    )
    versione_llm: dict | None = None  # decisione 45: provider, versione, precedente (se è cambiata), provata

    def escludi(self, c: Candidata, motivo: str) -> None:
        conta = self.di(c.tipo)
        conta.escluse += 1
        conta.notizie_escluse.append({"fonte": c.fonte, "titolo": c.titolo, "url": c.url, "motivo": motivo})

    def di(self, tipo: str) -> Contatori:
        """Contatori della fonte di un tipo di notizia (video e short sono entrambi "youtube")."""
        return self.fonti.setdefault(FONTE_DI_TIPO.get(tipo, tipo), Contatori())

    def conta_token(self, ruolo: str, risposta) -> None:
        self.token[ruolo]["ingresso"] += risposta.token_ingresso
        self.token[ruolo]["uscita"] += risposta.token_uscita
