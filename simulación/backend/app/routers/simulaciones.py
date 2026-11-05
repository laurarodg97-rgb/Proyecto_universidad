"""Métodos, simulación de escenarios e historial."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.dependencies import get_db, get_simulador
from app.models.db_models import Simulacion
from app.models.schemas import (FilaGrupo, MetodoInfo, NombreMetodo, PalancaInfo,
                                SimulacionRequest, SimulacionResponse)
from app.services.simulador import MIL_MILLONES, Simulador

router = APIRouter(tags=["Simulación"])


def filas_grupo(tabla: pd.DataFrame, columna: str) -> list[FilaGrupo]:
    return [FilaGrupo(grupo=str(getattr(f, columna)), estudiantes=int(f.N),
                      ingreso_real_mm=f.INGRESO_REAL / MIL_MILLONES,
                      ingreso_simulado_mm=f.SIMULADO / MIL_MILLONES,
                      brecha_mm=f.BRECHA / MIL_MILLONES, brecha_pct=f.BRECHA_PCT)
            for f in tabla.itertuples()]


def comprobar_periodos(simulador: Simulador, periodos: list[int] | None) -> None:
    if periodos:
        desconocidos = sorted(set(periodos) - set(simulador.periodos()))
        if desconocidos:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                f"Periodos sin datos: {desconocidos}. Disponibles: {simulador.periodos()}")


@router.get("/metodos", response_model=list[MetodoInfo], summary="Métodos y sus palancas")
def metodos(simulador: Simulador = Depends(get_simulador)) -> list[MetodoInfo]:
    return [MetodoInfo(nombre=m.nombre, descripcion=m.descripcion,
                       palancas=[PalancaInfo(**vars(p)) for p in m.palancas])
            for m in simulador.metodos.values()]


@router.get("/periodos", response_model=list[int], summary="Periodos disponibles")
def periodos(simulador: Simulador = Depends(get_simulador)) -> list[int]:
    return simulador.periodos()


@router.get("/balance/{metodo}", response_model=SimulacionResponse,
            summary="Balance del método tal como se presentó")
def balance(metodo: NombreMetodo, agrupar_por: str = Query("FACULTAD", pattern="^(FACULTAD|PERIODO|BANDA)$"),
            simulador: Simulador = Depends(get_simulador),
            settings: Settings = Depends(get_settings)) -> SimulacionResponse:
    r = simulador.simular(metodo)
    return SimulacionResponse(
        metodo=metodo, parametros=simulador.metodo(metodo).parametros_actuales(),
        ingreso_real_mm=r.ingreso_real / MIL_MILLONES, ingreso_simulado_mm=r.ingreso_simulado / MIL_MILLONES,
        brecha_mm=r.brecha / MIL_MILLONES, brecha_pct=r.brecha_pct,
        en_equilibrio=abs(r.brecha / MIL_MILLONES) <= settings.tolerancia_equilibrio_mm,
        detalle=filas_grupo(simulador.simular_por(agrupar_por, metodo), agrupar_por))


@router.post("/simulaciones", response_model=SimulacionResponse, status_code=status.HTTP_201_CREATED,
             summary="Simula un escenario y lo guarda en el historial")
def crear_simulacion(peticion: SimulacionRequest, db: Session = Depends(get_db),
                     simulador: Simulador = Depends(get_simulador),
                     settings: Settings = Depends(get_settings)) -> SimulacionResponse:
    comprobar_periodos(simulador, peticion.periodos)
    metodo, palancas = peticion.parametros.metodo, peticion.parametros.palancas()
    r = simulador.simular(metodo, palancas, peticion.periodos)
    registro = Simulacion(metodo=metodo, parametros=palancas, periodos=peticion.periodos,
                          ingreso_real_mm=r.ingreso_real / MIL_MILLONES,
                          ingreso_simulado_mm=r.ingreso_simulado / MIL_MILLONES,
                          brecha_mm=r.brecha / MIL_MILLONES, brecha_pct=r.brecha_pct)
    db.add(registro)
    db.commit()
    respuesta = SimulacionResponse.model_validate(registro)
    respuesta.en_equilibrio = abs(respuesta.brecha_mm) <= settings.tolerancia_equilibrio_mm
    respuesta.detalle = filas_grupo(
        simulador.simular_por("FACULTAD", metodo, palancas, peticion.periodos), "FACULTAD")
    return respuesta


@router.get("/simulaciones", response_model=list[SimulacionResponse], summary="Historial")
def listar_simulaciones(metodo: NombreMetodo | None = None, limite: int = Query(50, ge=1, le=500),
                        db: Session = Depends(get_db)) -> list[Simulacion]:
    consulta = select(Simulacion).order_by(Simulacion.id.desc()).limit(limite)
    if metodo:
        consulta = consulta.where(Simulacion.metodo == metodo)
    return list(db.scalars(consulta))


@router.get("/simulaciones/{id_simulacion}", response_model=SimulacionResponse)
def obtener_simulacion(id_simulacion: int, db: Session = Depends(get_db)) -> Simulacion:
    registro = db.get(Simulacion, id_simulacion)
    if registro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la simulación {id_simulacion}")
    return registro


@router.delete("/simulaciones/{id_simulacion}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_simulacion(id_simulacion: int, db: Session = Depends(get_db)) -> None:
    registro = db.get(Simulacion, id_simulacion)
    if registro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la simulación {id_simulacion}")
    db.delete(registro)
    db.commit()
