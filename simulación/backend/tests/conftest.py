"""Fixtures: base de datos en memoria y cliente de pruebas."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.database import crear_engine, crear_sesiones  # noqa: E402
from app.dependencies import get_db, get_simulador  # noqa: E402
from app.main import app  # noqa: E402
from app.services.simulador import Simulador  # noqa: E402


@pytest.fixture(scope="session")
def simulador() -> Simulador:
    return get_simulador(get_settings())


@pytest.fixture()
def cliente() -> Iterator[TestClient]:
    """Cada prueba usa una base SQLite en memoria nueva."""
    fabrica = crear_sesiones(crear_engine("sqlite:///:memory:"))

    def db_de_prueba() -> Iterator[Session]:
        sesion = fabrica()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = db_de_prueba
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
