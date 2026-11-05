"""Tablas ORM: historial de simulaciones y log de predicciones del modelo."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Simulacion(Base):
    __tablename__ = "simulaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creada: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    metodo: Mapped[str] = mapped_column(String(20), index=True)
    parametros: Mapped[dict] = mapped_column(JSON)
    periodos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ingreso_real_mm: Mapped[float] = mapped_column(Float)
    ingreso_simulado_mm: Mapped[float] = mapped_column(Float)
    brecha_mm: Mapped[float] = mapped_column(Float)
    brecha_pct: Mapped[float] = mapped_column(Float)


class Prediccion(Base):
    __tablename__ = "predicciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creada: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    metodo: Mapped[str] = mapped_column(String(20), index=True)
    parametros: Mapped[dict] = mapped_column(JSON)
    brecha_predicha_mm: Mapped[float] = mapped_column(Float)
    version_modelo: Mapped[str] = mapped_column(String(40))
