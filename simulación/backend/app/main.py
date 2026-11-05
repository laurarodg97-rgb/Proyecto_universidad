"""API del simulador de equilibrio del cobro de matrícula.

    uvicorn app.main:app --reload        (desde backend/)

Documentación automática en /docs (Swagger) y /redoc.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.dependencies import get_simulador
from app.ml.predictor import ModelStore
from app.models.schemas import SaludResponse
from app.routers import equilibrio, ml, simulaciones
from app.services.simulador import Simulador


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Singleton: los modelos se cargan una vez al arrancar, no en cada petición
    ModelStore.configurar(settings.ruta_modelos)
    try:
        ModelStore.get()
    except FileNotFoundError:
        logging.getLogger("simulacion").warning("Sin modelos entrenados: /predict responderá 503")
    yield
    ModelStore.reset()


app = FastAPI(
    title="Simulador de equilibrio del cobro de matrícula",
    version="1.0.0",
    description=(
        "Compara el **cobro por créditos** y el **cobro por bandas** con el ingreso real de la "
        "universidad (2021-1 a 2026-1) y busca el punto de equilibrio: los parámetros con los que "
        "el ingreso simulado es igual al actual. Trabaja sobre una base agregada por facultad, "
        "periodo y banda; no contiene datos de estudiantes."
    ),
    lifespan=lifespan,
)

app.include_router(simulaciones.router)
app.include_router(equilibrio.router)
app.include_router(ml.router)


@app.get("/health", response_model=SaludResponse, tags=["Servicio"])
async def health(settings: Settings = Depends(get_settings),
                 simulador: Simulador = Depends(get_simulador)) -> SaludResponse:
    return SaludResponse(entorno=settings.entorno, modelos_cargados=ModelStore.cargados(),
                         celdas_base=len(simulador.celdas))
