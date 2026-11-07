"""Lettura e scrittura delle impostazioni modificabili dalla dashboard."""

import re
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from gradiens.dati.modelli import TEMI, CanaleYoutube, CategoriaArxiv, Impostazioni

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


def salva_esecuzione(sessione: Session, soglia: int, finestra_giorni: int,
                     escludi_sponsorizzati: bool = True, escludi_pagamento: bool = True,
                     orario: str | None = None, in_pausa: bool = False) -> None:
    """`orario` None lascia quello attuale."""
    if not 0 <= soglia <= 100:
        raise ImpostazioneNonValida("La soglia va da 0 a 100.")
    if not 1 <= finestra_giorni <= 7:
        raise ImpostazioneNonValida("La finestra di raccolta va da 1 a 7 giorni.")
    imp = leggi(sessione)
    if orario is not None:
        try:
            imp.orario_programmato = time.fromisoformat(orario).strftime("%H:%M")
        except ValueError:
            raise ImpostazioneNonValida(f"«{orario}» non è un orario valido, per esempio 07:00.") from None
    imp.soglia, imp.finestra_giorni = soglia, finestra_giorni
    imp.escludi_sponsorizzati, imp.escludi_pagamento = escludi_sponsorizzati, escludi_pagamento
    imp.programmazione_in_pausa = in_pausa
    sessione.commit()


def imposta_pausa(sessione: Session, in_pausa: bool) -> None:
    """TG-10: /pausa e /riprendi."""
    leggi(sessione).programmazione_in_pausa = in_pausa
    sessione.commit()


def salva_tetto_arxiv(sessione: Session, tetto: int) -> None:
    if not 1 <= tetto <= 500:
        raise ImpostazioneNonValida("Il tetto di paper va da 1 a 500.")
    leggi(sessione).tetto_arxiv = tetto
    sessione.commit()


def elenca_categorie(sessione: Session) -> list[CategoriaArxiv]:
    return list(sessione.scalars(select(CategoriaArxiv).order_by(CategoriaArxiv.codice)))


def categorie_arxiv(sessione: Session) -> list[str]:
    return [c.codice for c in elenca_categorie(sessione)]


def nomi_categorie(sessione: Session) -> dict[str, str]:
    """{codice: nome} delle categorie a cui l'utente ha dato un nome."""
    query = select(CategoriaArxiv.codice, CategoriaArxiv.nome).where(CategoriaArxiv.nome.is_not(None))
    return {codice: nome for codice, nome in sessione.execute(query)}


def aggiungi_categoria(sessione: Session, codice: str, nome: str = "") -> None:
    """Aggiunge la categoria; se c'è già, ne cambia il nome (vuoto = nessun nome)."""
    codice, nome = codice.strip(), nome.strip()
    if not FORMATO_CATEGORIA.match(codice):
        raise ImpostazioneNonValida(f"«{codice}» non sembra una categoria arXiv, per esempio cs.CR.")
    if len(nome) > 100:
        raise ImpostazioneNonValida("Il nome della categoria può avere al massimo 100 caratteri.")
    categoria = sessione.get(CategoriaArxiv, codice) or CategoriaArxiv(codice=codice)
    categoria.nome = nome or None
    sessione.add(categoria)
    sessione.commit()


def rimuovi_categoria(sessione: Session, codice: str) -> None:
    """Anche l'ultima: arXiv è facoltativo se ci sono altre fonti (decisione 56); senza fonti c'è il segnale."""
    categoria = sessione.get(CategoriaArxiv, codice)
    if categoria is not None:
        sessione.delete(categoria)
        sessione.commit()


def canali_youtube(sessione: Session) -> list[CanaleYoutube]:
    return list(sessione.scalars(select(CanaleYoutube).order_by(CanaleYoutube.nome)))


def aggiungi_canale(sessione: Session, id: str, nome: str) -> None:
    """Il canale arriva già risolto e validato da `fonti.youtube.risolvi_canale`."""
    if sessione.get(CanaleYoutube, id) is None:
        sessione.add(CanaleYoutube(id=id, nome=nome))
        sessione.commit()


def rimuovi_canale(sessione: Session, id: str) -> None:
    canale = sessione.get(CanaleYoutube, id)
    if canale is not None:
        sessione.delete(canale)
        sessione.commit()
