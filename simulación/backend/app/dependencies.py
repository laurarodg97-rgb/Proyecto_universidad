"""Dependencias que FastAPI inyecta en las rutas con Depends()."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import crear_engine, crear_sesiones
from app.ml.predictor import ModelPredictor, ModelStore
from app.services.datos import cargar_base_agregada
from app.services.simulador import Simulador


@lru_cache
def _fabrica_sesiones(database_url: str) -> sessionmaker:
    """Cachea la fábrica para no recrear el Engine en cada petición."""
    return crear_sesiones(crear_engine(database_url))


def get_db(settings: Settings = Depends(get_settings)) -> Generator[Session, None, None]:
    sesion = _fabrica_sesiones(settings.database_url)()
    try:
        yield sesion
    finally:
        sesion.close()


@lru_cache
def _simulador(ruta: str) -> Simulador:
    return Simulador(cargar_base_agregada(ruta))


def get_simulador(settings: Settings = Depends(get_settings)) -> Simulador:
    try:
        return _simulador(str(settings.ruta_base_agregada))
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e


def get_predictor(settings: Settings = Depends(get_settings)) -> ModelPredictor:
    if ModelStore.ruta is None:
        ModelStore.configurar(settings.ruta_modelos)
    try:
        return ModelPredictor(ModelStore.get(), ModelStore.metadata())
    except (FileNotFoundError, KeyError, RuntimeError) as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            f"El modelo no está disponible: {e}") from e
