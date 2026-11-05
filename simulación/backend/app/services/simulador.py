"""Simulador de los dos métodos de cobro sobre la base agregada.

Cada método es una clase con sus palancas y su fórmula de ingreso por
celda (FACULTAD × PERIODO × BANDA). Como el cobro es lineal dentro de
cada celda, el resultado es idéntico al cálculo estudiante por
estudiante de los scripts en R.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from app.decoradores import medir_tiempo

MIL_MILLONES = 1e9


@dataclass(frozen=True)
class Palanca:
    """Un parámetro que se puede mover en la simulación."""

    nombre: str
    descripcion: str
    minimo: float
    maximo: float
    actual: float          # valor que reproduce el método tal como se presentó


class MetodoCobro(ABC):
    """Interfaz común de los métodos de cobro."""

    nombre: ClassVar[str]
    descripcion: ClassVar[str]
    palancas: ClassVar[tuple[Palanca, ...]]

    @classmethod
    def palanca(cls, nombre: str) -> Palanca:
        for p in cls.palancas:
            if p.nombre == nombre:
                return p
        raise KeyError(f"{cls.nombre} no tiene la palanca {nombre!r}")

    @classmethod
    def parametros_actuales(cls) -> dict[str, float]:
        return {p.nombre: p.actual for p in cls.palancas}

    @abstractmethod
    def ingreso(self, celdas: pd.DataFrame, params: dict[str, float]) -> np.ndarray:
        """Ingreso neto simulado de cada celda, en pesos."""


class CobroPorCreditos(MetodoCobro):
    """Cobro por créditos de Proyecto_u.R: créditos × T × (1 - beca).

    Con elasticidad e, si la tarifa sube un x %, cada estudiante inscribe
    e·x % menos créditos (y más si baja). Es un supuesto de sensibilidad.
    """

    nombre = "creditos"
    descripcion = "Cobro por créditos inscritos (Proyecto_u.R)"
    palancas = (
        Palanca("factor_tarifa", "Multiplica la tarifa plena por crédito T", 0.5, 2.0, 1.0),
        Palanca("elasticidad", "Respuesta de los créditos inscritos al precio (supuesto)", 0.0, 0.3, 0.0),
    )

    def ingreso(self, celdas: pd.DataFrame, params: dict[str, float]) -> np.ndarray:
        f, e = params["factor_tarifa"], params["elasticidad"]
        ajuste_creditos = max(1 - e * (f - 1), 0.0)
        return f * ajuste_creditos * celdas.CT_NETO_REAL.to_numpy()


class CobroPorBandas(MetodoCobro):
    """Cobro por bandas proporcionales por facultad (metodo_bandas/).

    1-6 y 7-11 pagan F × M, con F = créditos promedio de la banda / créditos
    promedio de 12-18 en la facultad (× k_parcial, tope 1); 12-18 paga M; 19+
    paga M más T por crédito sobre 18. Con elasticidad e, quien inscribe 12-13
    baja a 11 con probabilidad e·(1 - F2), y quien inscribe 19-20 baja a 18
    con probabilidad e·(cobro extra / M).
    """

    nombre = "bandas"
    descripcion = "Cobro por bandas proporcionales por facultad (metodo_bandas/)"
    palancas = (
        Palanca("k_parcial", "Multiplica las fracciones de 1-6 y 7-11 (tope 1)", 0.5, 3.0, 1.0),
        Palanca("ajuste_plena", "Multiplica la matrícula plena M en todas las bandas", 0.8, 1.2, 1.0),
        Palanca("tarifa_extra", "Multiplica T en el cobro por crédito sobre 18", 0.0, 5.0, 1.0),
        Palanca("elasticidad", "Respuesta de los créditos inscritos al precio (supuesto)", 0.0, 0.3, 0.0),
    )

    def __init__(self, fracciones: pd.DataFrame):
        self.fracciones = fracciones.set_index("FACULTAD")

    def ingreso(self, celdas: pd.DataFrame, params: dict[str, float]) -> np.ndarray:
        k, s = params["k_parcial"], params["ajuste_plena"]
        tau, e = params["tarifa_extra"], params["elasticidad"]
        fr = self.fracciones.reindex(celdas.FACULTAD)
        f1 = np.minimum(fr.F1.to_numpy() * k, 1)
        f2 = np.minimum(fr.F2.to_numpy() * k, 1)
        banda = celdas.BANDA.to_numpy()
        m = celdas.M_NETO.to_numpy() * s

        ingreso = np.select(
            [banda == "1-6", banda == "7-11"], [f1 * m, f2 * m],
            default=m + tau * celdas.T_EXTRA_NETO.to_numpy() * (banda == "19+"))
        if e > 0:
            # 12-13 → 11: pierden (1 - F2) de M con probabilidad e (1 - F2)
            ingreso -= (banda == "12-18") * s * celdas.M_NETO_12_13.to_numpy() * e * (1 - f2) ** 2
            # 19-20 → 18: pierden el cobro extra con probabilidad e·extra/M
            ingreso -= (banda == "19+") * e * tau**2 / s * celdas.T2_EXTRA_19_20.to_numpy()
        return ingreso


def fracciones_proporcionales(celdas: pd.DataFrame) -> pd.DataFrame:
    """F1 y F2 por facultad: créditos promedio de la banda / de 12-18."""
    prom = (celdas.groupby(["FACULTAD", "BANDA"])[["SUM_CREDITOS", "N"]].sum()
                  .eval("SUM_CREDITOS / N").unstack())
    return pd.DataFrame({
        "FACULTAD": prom.index,
        "F1": (prom["1-6"] / prom["12-18"]).clip(upper=1).to_numpy(),
        "F2": (prom["7-11"] / prom["12-18"]).clip(upper=1).to_numpy(),
    })


@dataclass
class Resultado:
    ingreso_real: float
    ingreso_simulado: float

    @property
    def brecha(self) -> float:
        return self.ingreso_simulado - self.ingreso_real

    @property
    def brecha_pct(self) -> float:
        return self.brecha / self.ingreso_real * 100


class Simulador:
    """Punto de entrada: simula, compara y busca el equilibrio."""

    def __init__(self, celdas: pd.DataFrame):
        self.celdas = celdas.reset_index(drop=True)
        self.metodos: dict[str, MetodoCobro] = {
            "creditos": CobroPorCreditos(),
            "bandas": CobroPorBandas(fracciones_proporcionales(self.celdas)),
        }

    # -- utilidades ---------------------------------------------------------
    def metodo(self, nombre: str) -> MetodoCobro:
        try:
            return self.metodos[nombre]
        except KeyError:
            raise KeyError(f"Método desconocido: {nombre!r}") from None

    def _filtrar(self, periodos: list[int] | None) -> pd.DataFrame:
        if not periodos:
            return self.celdas
        return self.celdas[self.celdas.PERIODO.isin(periodos)]

    def _completar(self, metodo: MetodoCobro, params: dict[str, float] | None) -> dict[str, float]:
        return {**metodo.parametros_actuales(), **(params or {})}

    # -- simulación -----------------------------------------------------------
    def simular(self, metodo: str, params: dict[str, float] | None = None,
                periodos: list[int] | None = None) -> Resultado:
        m = self.metodo(metodo)
        celdas = self._filtrar(periodos)
        ingreso = m.ingreso(celdas, self._completar(m, params))
        return Resultado(celdas.INGRESO_REAL.sum(), ingreso.sum())

    def simular_por(self, columna: str, metodo: str, params: dict[str, float] | None = None,
                    periodos: list[int] | None = None) -> pd.DataFrame:
        """Real, simulado y brecha agrupados por FACULTAD, PERIODO o BANDA."""
        m = self.metodo(metodo)
        celdas = self._filtrar(periodos)
        tabla = (celdas.assign(SIMULADO=m.ingreso(celdas, self._completar(m, params)))
                       .groupby(columna, observed=True)[["N", "INGRESO_REAL", "SIMULADO"]].sum())
        tabla["BRECHA"] = tabla.SIMULADO - tabla.INGRESO_REAL
        tabla["BRECHA_PCT"] = tabla.BRECHA / tabla.INGRESO_REAL * 100
        return tabla.reset_index()

    def brecha(self, metodo: str, params: dict[str, float] | None = None,
               periodos: list[int] | None = None) -> float:
        """Ingreso simulado menos real, en mil millones."""
        return self.simular(metodo, params, periodos).brecha / MIL_MILLONES

    @medir_tiempo
    def equilibrio(self, metodo: str, palanca: str, fijos: dict[str, float] | None = None,
                   periodos: list[int] | None = None) -> float:
        """Valor de `palanca` que deja la brecha en cero (scipy.optimize.brentq).

        Lanza ValueError si en el rango válido de la palanca no hay equilibrio.
        """
        p = self.metodo(metodo).palanca(palanca)
        fijos = {k: v for k, v in (fijos or {}).items() if k != palanca}

        def g(x: float) -> float:
            return self.brecha(metodo, {**fijos, palanca: x}, periodos)

        # Se recorre el rango en una grilla para encontrar el primer cambio de signo
        grilla = np.linspace(p.minimo, p.maximo, 61)
        valores = np.array([g(x) for x in grilla])
        cambios = np.nonzero(np.sign(valores[:-1]) * np.sign(valores[1:]) <= 0)[0]
        if len(cambios) == 0:
            raise ValueError(
                f"No hay equilibrio moviendo {palanca} entre {p.minimo} y {p.maximo}: "
                f"la brecha va de {valores.min():.2f} a {valores.max():.2f} mil millones")
        i = cambios[0]
        return brentq(g, grilla[i], grilla[i + 1], xtol=1e-8)

    def periodos(self) -> list[int]:
        return sorted(int(p) for p in self.celdas.PERIODO.unique())
