"""Lettura e scrittura delle impostazioni modificabili dalla dashboard."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from gradiens.dati.modelli import TEMI, CategoriaArxiv, Impostazioni

# Codici arXiv: archivio e, facoltativa, sottocategoria (cs.CR, math.PR, hep-th, astro-ph.GA).
FORMATO_CATEGORIA = re.compile(r"^[a-z][a-z-]*(\.[A-Za-z-]+)?$")


class ImpostazioneNonValida(ValueError):
    """Valore rifiutato: il messaggio è pensato per l'utente."""


def leggi(sessione: Session) -> Impostazioni:
    return sessione.get_one(Impostazioni, 1)


def salva_tema(sessione: Session, tema: str) -> None:
    if tema not in TEMI:
        raise ImpostazioneNonValida(f"Tema non valido: {tema!r}")
    leggi(sessione).tema = tema
    sessione.commit()


def salva_esecuzione(sessione: Session, soglia: int, finestra_giorni: int) -> None:
    if not 0 <= soglia <= 100:
        raise ImpostazioneNonValida("La soglia va da 0 a 100.")
    if not 1 <= finestra_giorni <= 7:
        raise ImpostazioneNonValida("La finestra di raccolta va da 1 a 7 giorni.")
    imp = leggi(sessione)
    imp.soglia, imp.finestra_giorni = soglia, finestra_giorni
    sessione.commit()


def salva_tetto_arxiv(sessione: Session, tetto: int) -> None:
    if not 1 <= tetto <= 500:
        raise ImpostazioneNonValida("Il tetto di paper va da 1 a 500.")
    leggi(sessione).tetto_arxiv = tetto
    sessione.commit()


def categorie_arxiv(sessione: Session) -> list[str]:
    return list(sessione.scalars(select(CategoriaArxiv.codice).order_by(CategoriaArxiv.codice)))


def aggiungi_categoria(sessione: Session, codice: str) -> None:
    codice = codice.strip()
    if not FORMATO_CATEGORIA.match(codice):
        raise ImpostazioneNonValida(f"«{codice}» non sembra una categoria arXiv, per esempio cs.CR.")
    if sessione.get(CategoriaArxiv, codice) is None:
        sessione.add(CategoriaArxiv(codice=codice))
        sessione.commit()


def rimuovi_categoria(sessione: Session, codice: str) -> None:
    categoria = sessione.get(CategoriaArxiv, codice)
    if categoria is not None and len(categorie_arxiv(sessione)) <= 1:
        raise ImpostazioneNonValida("Deve esserci almeno una categoria arXiv.")  # ARX-01
    if categoria is not None:
        sessione.delete(categoria)
        sessione.commit()
