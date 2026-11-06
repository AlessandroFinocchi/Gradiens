"""Fonti delle notizie. Ognuna restituisce `Candidata` in un formato comune (struttura.md)."""

from dataclasses import dataclass
from datetime import datetime

USER_AGENT = "Gradiens/0.1 (app personale di raccolta notizie)"  # generico, senza dati personali (WEB-18)


@dataclass
class Candidata:
    """Una notizia trovata da una fonte, prima di filtro e valutazione."""

    tipo: str  # arxiv, sito, video, short
    url: str  # indirizzo canonico: è la chiave del registro delle notizie viste
    fonte: str
    titolo: str
    sommario: str  # per il pre-filtro (ESE-04)
    contenuto: str  # per la valutazione completa (ESE-05); per arXiv è l'abstract (ARX-04)
    pubblicata_il: datetime  # UTC senza fuso
    data_incerta: bool = False
    stato: str | None = None
