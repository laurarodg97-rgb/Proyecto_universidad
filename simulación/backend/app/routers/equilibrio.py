"""Punto de equilibrio, Monte Carlo y validación temporal."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import Settings, get_settings
from app.dependencies import get_simulador
from app.models.schemas import (EquilibrioRequest, EquilibrioResponse, FilaPeriodo,
                                MonteCarloRequest, MonteCarloResponse, NombreMetodo,
                                ResumenBrecha, ValidacionTemporalResponse)
from app.routers.simulaciones import comprobar_periodos, filas_grupo
from app.services.simulador import Simulador

router = APIRouter(tags=["Equilibrio"])


@router.post("/equilibrio", response_model=EquilibrioResponse,
             summary="Valor de una palanca que deja el ingreso igual al real")
def equilibrio(peticion: EquilibrioRequest,
               simulador: Simulador = Depends(get_simulador)) -> EquilibrioResponse:
    comprobar_periodos(simulador, peticion.periodos)
    try:
        valor = simulador.equilibrio(peticion.metodo, peticion.palanca, peticion.fijos, peticion.periodos)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    parametros = {**simulador.metodo(peticion.metodo).parametros_actuales(),
                  **peticion.fijos, peticion.palanca: valor}
    return EquilibrioResponse(
        metodo=peticion.metodo, palanca=peticion.palanca, valor=valor, parametros=parametros,
        brecha_mm=simulador.brecha(peticion.metodo, parametros, peticion.periodos),
        detalle=filas_grupo(simulador.simular_por("FACULTAD", peticion.metodo, parametros,
                                                  peticion.periodos), "FACULTAD"))


@router.post("/montecarlo", response_model=MonteCarloResponse,
             summary="Sortea escenarios dentro del rango de cada palanca")
def montecarlo(peticion: MonteCarloRequest, simulador: Simulador = Depends(get_simulador),
               settings: Settings = Depends(get_settings)) -> MonteCarloResponse:
    if peticion.n > settings.max_escenarios_montecarlo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"n no puede superar {settings.max_escenarios_montecarlo}")
    rng = np.random.default_rng(peticion.semilla)
    palancas = simulador.metodo(peticion.metodo).palancas
    escenarios = [{p.nombre: float(rng.uniform(p.minimo, p.maximo)) for p in palancas}
                  for _ in range(peticion.n)]
    brechas = np.array([simulador.brecha(peticion.metodo, e) for e in escenarios])
    cerca = np.abs(brechas) <= settings.tolerancia_equilibrio_mm
    return MonteCarloResponse(
        metodo=peticion.metodo, n=peticion.n,
        brecha_mm=ResumenBrecha(minimo=brechas.min(), p05=np.percentile(brechas, 5),
                                mediana=np.median(brechas), p95=np.percentile(brechas, 95),
                                maximo=brechas.max(), media=brechas.mean()),
        proporcion_equilibrio=float(cerca.mean()),
        ejemplos_equilibrio=[e for e, c in zip(escenarios, cerca) if c][:10])


@router.get("/validacion-temporal/{metodo}", response_model=ValidacionTemporalResponse,
            summary="Calibra con los primeros periodos y prueba en los últimos")
def validacion_temporal(metodo: NombreMetodo,
                        ultimo_entrenamiento: int = Query(20242, description="Último periodo de entrenamiento"),
                        simulador: Simulador = Depends(get_simulador)) -> ValidacionTemporalResponse:
    todos = simulador.periodos()
    entrena = [p for p in todos if p <= ultimo_entrenamiento]
    prueba = [p for p in todos if p > ultimo_entrenamiento]
    if not entrena or not prueba:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"El corte debe dejar periodos a ambos lados; disponibles: {todos}")
    palanca = simulador.metodo(metodo).palancas[0].nombre
    valor = simulador.equilibrio(metodo, palanca, periodos=entrena)

    filas = []
    for p in todos:
        actual = simulador.simular(metodo, periodos=[p])
        calibrado = simulador.simular(metodo, {palanca: valor}, periodos=[p])
        try:
            valor_p = simulador.equilibrio(metodo, palanca, periodos=[p])
        except ValueError:
            valor_p = None
        filas.append(FilaPeriodo(periodo=p, muestra="entrenamiento" if p in entrena else "prueba",
                                 ingreso_real_mm=actual.ingreso_real / 1e9,
                                 brecha_pct_actual=actual.brecha_pct,
                                 brecha_pct_calibrado=calibrado.brecha_pct,
                                 valor_equilibrio_periodo=valor_p))
    return ValidacionTemporalResponse(
        metodo=metodo, palanca=palanca, ultimo_periodo_entrenamiento=entrena[-1], valor_calibrado=valor,
        brecha_pct_entrenamiento=simulador.simular(metodo, {palanca: valor}, entrena).brecha_pct,
        brecha_pct_prueba=simulador.simular(metodo, {palanca: valor}, prueba).brecha_pct,
        por_periodo=filas)
