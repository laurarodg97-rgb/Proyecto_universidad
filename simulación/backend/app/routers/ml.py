"""Predicción con el metamodelo de ML (cargado con Singleton)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.dependencies import get_db, get_predictor, get_simulador
from app.ml.predictor import ModelPredictor
from app.models.db_models import Prediccion
from app.models.schemas import PrediccionRequest, PrediccionResponse
from app.services.simulador import Simulador

router = APIRouter(tags=["Machine learning"])


@router.post("/predict", response_model=PrediccionResponse, status_code=status.HTTP_201_CREATED,
             summary="Brecha de ingreso predicha por el modelo de ML")
def predict(peticion: PrediccionRequest, db: Session = Depends(get_db),
            predictor: ModelPredictor = Depends(get_predictor),
            simulador: Simulador = Depends(get_simulador),
            settings: Settings = Depends(get_settings)) -> PrediccionResponse:
    metodo, palancas = peticion.parametros.metodo, peticion.parametros.palancas()
    brecha = predictor.predecir(metodo, palancas)
    registro = Prediccion(metodo=metodo, parametros=palancas, brecha_predicha_mm=brecha,
                          version_modelo=predictor.version(metodo))
    db.add(registro)
    db.commit()
    return PrediccionResponse(
        id=registro.id, metodo=metodo, parametros=palancas, brecha_predicha_mm=brecha,
        brecha_exacta_mm=simulador.brecha(metodo, palancas),
        en_equilibrio=abs(brecha) <= settings.tolerancia_equilibrio_mm,
        version_modelo=registro.version_modelo)


@router.get("/modelo", summary="Metadata del modelo entrenado")
def modelo(predictor: ModelPredictor = Depends(get_predictor)) -> dict[str, Any]:
    return predictor.metadata


@router.get("/predicciones", summary="Log de predicciones")
def predicciones(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    filas = db.scalars(select(Prediccion).order_by(Prediccion.id.desc()).limit(100))
    return [{"id": p.id, "creada": p.creada, "metodo": p.metodo, "parametros": p.parametros,
             "brecha_predicha_mm": p.brecha_predicha_mm, "version_modelo": p.version_modelo}
            for p in filas]
