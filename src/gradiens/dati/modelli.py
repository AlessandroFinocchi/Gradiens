"""Tabelle del database. Ogni modifica qui richiede una migrazione in `migrazioni/versions/`.

Le date sono salvate in UTC senza fuso orario; la dashboard le mostra nell'ora locale.
"""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

TEMI = ("auto", "light", "dark")
TIPI_NOTIZIA = ("arxiv", "sito", "video", "short")
STATI_ESECUZIONE = ("in_corso", "completata", "interrotta", "fallita")


class Base(DeclarativeBase):
    pass


class Impostazioni(Base):
    """Impostazioni modificabili dalla dashboard. Ha sempre una sola riga, con id 1."""

    __tablename__ = "impostazioni"
    __table_args__ = (CheckConstraint(f"tema IN {TEMI}", name="tema_valido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tema: Mapped[str] = mapped_column(String(5), default="auto")
    soglia: Mapped[int] = mapped_column(default=60)  # ESE-06
    finestra_giorni: Mapped[int] = mapped_column(default=7)  # ESE-03
    tetto_arxiv: Mapped[int] = mapped_column(default=50)  # ARX-03
    provider_prefiltro: Mapped[str] = mapped_column(String(20), default="claude-code")  # LLM-03
    modello_prefiltro: Mapped[str] = mapped_column(String(60), default="haiku")
    provider_elaborazione: Mapped[str] = mapped_column(String(20), default="claude-code")
    modello_elaborazione: Mapped[str] = mapped_column(String(60), default="haiku")
    escludi_sponsorizzati: Mapped[bool] = mapped_column(default=True)  # WEB-23
    escludi_pagamento: Mapped[bool] = mapped_column(default=True)  # WEB-23
    orario_programmato: Mapped[str] = mapped_column(String(5), default="07:00")  # ESE-01, "HH:MM" nell'ora del PC
    programmazione_in_pausa: Mapped[bool] = mapped_column(default=False)  # TG-10
    # TG-01: il token sta nel .env; qui il nome del bot e l'unica chat autorizzata (TG-02).
    telegram_bot: Mapped[str | None] = mapped_column(String(64))
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_chat_nome: Mapped[str | None] = mapped_column(String(200))
    ultima_proposta_interesse_il: Mapped[datetime | None]  # INT-06: contano i cuori messi dopo questa data


class Interesse(Base):
    __tablename__ = "interessi"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    descrizione: Mapped[str] = mapped_column(Text)
    raffinamento: Mapped[str | None] = mapped_column(Text)
    ultima_proposta_il: Mapped[datetime | None]  # INT-04: contano i cuori messi dopo questa data


class CanaleYoutube(Base):
    __tablename__ = "canali_youtube"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # UC…
    nome: Mapped[str] = mapped_column(String(200))


class Sito(Base):
    """Un sito seguito, con il suo profilo (WEB-02) e lo stato dell'ultima raccolta (WEB-26)."""

    __tablename__ = "siti"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    profilo: Mapped[str] = mapped_column(Text)  # JSON di fonti.siti.Profilo
    profilo_precedente: Mapped[str | None] = mapped_column(Text)  # dopo una rigenerazione, per le differenze (WEB-25)
    stato: Mapped[str | None] = mapped_column(String(40))
    dettaglio: Mapped[str | None] = mapped_column(Text)
    guasti_consecutivi: Mapped[int] = mapped_column(default=0)  # 3 di fila: si rigenera il profilo (WEB-24)


class CategoriaArxiv(Base):
    __tablename__ = "categorie_arxiv"

    codice: Mapped[str] = mapped_column(String(32), primary_key=True)  # es. cs.CR
    nome: Mapped[str | None] = mapped_column(String(100))  # es. "Crittografia e Sicurezza", per i filtri


class Esecuzione(Base):
    __tablename__ = "esecuzioni"

    id: Mapped[int] = mapped_column(primary_key=True)
    avviata_il: Mapped[datetime]
    finita_il: Mapped[datetime | None]
    avviata_da: Mapped[str] = mapped_column(String(20))  # dashboard, cli, telegram, programmazione
    stato: Mapped[str] = mapped_column(String(10), default="in_corso")
    motivo: Mapped[str | None] = mapped_column(Text)
    metriche: Mapped[str | None] = mapped_column(Text)  # JSON: per tipo di fonte e token per ruolo


class Notizia(Base):
    __tablename__ = "notizie"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(6))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    fonte: Mapped[str] = mapped_column(String(200))
    titolo: Mapped[str] = mapped_column(Text)  # titolo originale
    titolo_it: Mapped[str | None] = mapped_column(Text)  # solo se l'originale non è in italiano
    sommario: Mapped[str | None] = mapped_column(Text)  # es. l'abstract di arXiv (ARX-04)
    riassunto: Mapped[str] = mapped_column(Text)
    pubblicata_il: Mapped[datetime]  # per le date incerte è la data di scoperta (WEB-15)
    data_incerta: Mapped[bool] = mapped_column(default=False)
    scoperta_il: Mapped[datetime]
    stato: Mapped[str | None] = mapped_column(String(40))  # es. "contenuto parziale"
    cuore: Mapped[bool] = mapped_column(default=False, index=True)
    cuore_il: Mapped[datetime | None]  # quando è stato messo il cuore (INT-04, INT-06)
    esecuzione_id: Mapped[int | None] = mapped_column(ForeignKey("esecuzioni.id", ondelete="SET NULL"))
    argomento_id: Mapped[int | None] = mapped_column(ForeignKey("argomenti.id", ondelete="SET NULL"), index=True)  # ESE-08

    argomento: Mapped["Argomento | None"] = relationship(back_populates="notizie")

    pertinenze: Mapped[list["Pertinenza"]] = relationship(
        back_populates="notizia", cascade="all, delete-orphan", order_by="Pertinenza.punteggio.desc()"
    )


class Argomento(Base):
    """Un singolo evento e la sua evoluzione (ESE-08), non un tema generale."""

    __tablename__ = "argomenti"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    creato_il: Mapped[datetime]

    notizie: Mapped[list[Notizia]] = relationship(back_populates="argomento", order_by="Notizia.pubblicata_il.desc()")


class Pertinenza(Base):
    __tablename__ = "pertinenze"

    notizia_id: Mapped[int] = mapped_column(ForeignKey("notizie.id", ondelete="CASCADE"), primary_key=True)
    interesse_id: Mapped[int] = mapped_column(ForeignKey("interessi.id", ondelete="CASCADE"), primary_key=True)
    punteggio: Mapped[int]

    notizia: Mapped[Notizia] = relationship(back_populates="pertinenze")
    interesse: Mapped[Interesse] = relationship()


class Proposta(Base):
    """Proposta dell'LLM da approvare (INT-04, INT-06): un raffinamento per un interesse, oppure,
    senza interesse, un interesse nuovo con nome e descrizione."""

    __tablename__ = "proposte"

    id: Mapped[int] = mapped_column(primary_key=True)
    interesse_id: Mapped[int | None] = mapped_column(ForeignKey("interessi.id", ondelete="CASCADE"))
    testo: Mapped[str] = mapped_column(Text)  # raffinamento proposto, oppure descrizione del nuovo interesse
    nome: Mapped[str | None] = mapped_column(String(80))  # solo per un interesse nuovo
    notizie: Mapped[int]  # notizie con il cuore da cui nasce
    creata_il: Mapped[datetime]

    interesse: Mapped[Interesse | None] = relationship()


class NotiziaVista(Base):
    """Registro delle notizie già viste, scartate comprese: non si rivalutano (ESE-07)."""

    __tablename__ = "notizie_viste"

    url: Mapped[str] = mapped_column(String(1000), primary_key=True)
    vista_il: Mapped[datetime]
