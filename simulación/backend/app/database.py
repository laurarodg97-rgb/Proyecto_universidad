"""Motor y sesiones de SQLAlchemy."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def crear_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        opciones: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in database_url:
            # Una sola conexión compartida para que la BD en memoria no se pierda
            opciones["poolclass"] = StaticPool
        return create_engine(database_url, **opciones)
    return create_engine(database_url, pool_pre_ping=True)


def crear_sesiones(engine: Engine) -> sessionmaker:
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
