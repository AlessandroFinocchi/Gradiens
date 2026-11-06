"""Tabelle del database. Ogni modifica qui richiede una migrazione in `migrazioni/versions/`."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

TEMI = ("auto", "light", "dark")


class Base(DeclarativeBase):
    pass


class Impostazioni(Base):
    """Impostazioni modificabili dalla dashboard. Ha sempre una sola riga, con id 1."""

    __tablename__ = "impostazioni"
    __table_args__ = (CheckConstraint(f"tema IN {TEMI}", name="tema_valido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tema: Mapped[str] = mapped_column(String(5), default="auto")
