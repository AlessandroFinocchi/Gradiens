"""Fonti delle notizie: il contratto comune (docs/architettura/struttura.md, "Contratti").

Ogni fonte espone:
- `async raccogli(client, ..., dal) -> list[Candidata]`: trova le notizie nuove, con il sommario
  per il pre-filtro ma, se costa richieste in più, senza il contenuto completo;
- `async completa(client, candidata) -> Candidata`, se serve: scarica il contenuto completo.
  L'esecuzione la chiama solo per le notizie che passano il pre-filtro e il tetto.
  Se il contenuto non c'è (es. video senza trascrizione) solleva `ContenutoAssente`.
"""

from dataclasses import dataclass
from datetime import datetime

USER_AGENT = "Gradiens/0.1 (app personale di raccolta notizie)"  # generico, senza dati personali (WEB-18)


@dataclass
class Candidata:
    """Una notizia trovata da una fonte, prima di filtro e valutazione."""

    tipo: str  # arxiv, sito, video, short
    url: str  # indirizzo canonico https://: è la chiave del registro delle notizie viste
    fonte: str
    titolo: str
    sommario: str  # per il pre-filtro (ESE-04)
    contenuto: str  # per la valutazione completa (ESE-05); vuoto finché `completa` non lo scarica
    pubblicata_il: datetime  # UTC senza fuso
    data_incerta: bool = False
    stato: str | None = None


class ContenutoAssente(Exception):
    """La notizia non si può valutare. Il messaggio è lo stato per il resoconto, es. "trascrizione assente"."""


class NonAncoraDisponibile(Exception):
    """La notizia non si può ancora valutare (es. diretta non conclusa, YT-04): si riprova la volta dopo."""
