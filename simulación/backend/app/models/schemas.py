"""Modelos Pydantic de entrada y salida.

Los rangos de cada palanca salen de las clases del simulador, así la
validación de la API y el simulador nunca se contradicen.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.simulador import CobroPorBandas, CobroPorCreditos, MetodoCobro

NombreMetodo = Literal["creditos", "bandas"]
CLASES: dict[str, type[MetodoCobro]] = {"creditos": CobroPorCreditos, "bandas": CobroPorBandas}


def campo(metodo: type[MetodoCobro], nombre: str) -> Any:
    p = metodo.palanca(nombre)
    return Field(p.actual, ge=p.minimo, le=p.maximo, description=p.descripcion)


# --- Parámetros de cada método (unión discriminada por `metodo`) ---------------

class ParametrosCreditos(BaseModel):
    metodo: Literal["creditos"] = "creditos"
    factor_tarifa: float = campo(CobroPorCreditos, "factor_tarifa")
    elasticidad: float = campo(CobroPorCreditos, "elasticidad")

    def palancas(self) -> dict[str, float]:
        return self.model_dump(exclude={"metodo"})


class ParametrosBandas(BaseModel):
    metodo: Literal["bandas"] = "bandas"
    k_parcial: float = campo(CobroPorBandas, "k_parcial")
    ajuste_plena: float = campo(CobroPorBandas, "ajuste_plena")
    tarifa_extra: float = campo(CobroPorBandas, "tarifa_extra")
    elasticidad: float = campo(CobroPorBandas, "elasticidad")

    def palancas(self) -> dict[str, float]:
        return self.model_dump(exclude={"metodo"})


Parametros = Annotated[ParametrosCreditos | ParametrosBandas, Field(discriminator="metodo")]


def validar_periodos(periodos: list[int] | None) -> list[int] | None:
    if periodos is None:
        return None
    for p in periodos:
        if not (20000 <= p <= 20999 and p % 10 in (1, 2)):
            raise ValueError(f"Periodo inválido {p}: use el formato AAAAS, p. ej. 20251")
    return sorted(set(periodos))


# --- Peticiones ----------------------------------------------------------------

class SimulacionRequest(BaseModel):
    parametros: Parametros
    periodos: list[int] | None = Field(None, description="Periodos a incluir (todos si se omite)",
                                       examples=[[20251, 20252]])

    @field_validator("periodos")
    @classmethod
    def periodos_validos(cls, v: list[int] | None) -> list[int] | None:
        return validar_periodos(v)

    model_config = ConfigDict(json_schema_extra={"examples": [
        {"parametros": {"metodo": "bandas", "k_parcial": 1.28}},
        {"parametros": {"metodo": "creditos", "factor_tarifa": 1.1, "elasticidad": 0.1}},
    ]})


class PrediccionRequest(BaseModel):
    parametros: Parametros


class EquilibrioRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"metodo": "bandas", "palanca": "k_parcial", "fijos": {"elasticidad": 0.1}},
        {"metodo": "creditos", "palanca": "factor_tarifa"},
    ]})

    metodo: NombreMetodo
    palanca: str = Field(..., description="Palanca que se mueve para cerrar la brecha",
                         examples=["k_parcial"])
    fijos: dict[str, float] = Field(default_factory=dict,
                                    description="Valores de las demás palancas")
    periodos: list[int] | None = None

    @field_validator("periodos")
    @classmethod
    def periodos_validos(cls, v: list[int] | None) -> list[int] | None:
        return validar_periodos(v)

    @model_validator(mode="after")
    def palancas_validas(self) -> EquilibrioRequest:
        clase = CLASES[self.metodo]
        nombres = {p.nombre for p in clase.palancas}
        if self.palanca not in nombres:
            raise ValueError(f"{self.metodo} no tiene la palanca {self.palanca!r}; "
                             f"opciones: {sorted(nombres)}")
        for nombre, valor in self.fijos.items():
            if nombre not in nombres:
                raise ValueError(f"{self.metodo} no tiene la palanca {nombre!r}")
            p = clase.palanca(nombre)
            if not p.minimo <= valor <= p.maximo:
                raise ValueError(f"{nombre} debe estar entre {p.minimo} y {p.maximo}")
        return self


class MonteCarloRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"metodo": "bandas", "n": 1000, "semilla": 2026}]})

    metodo: NombreMetodo
    n: int = Field(1000, ge=10, le=5000, description="Número de escenarios")
    semilla: int = Field(2026, ge=0)


# --- Respuestas ----------------------------------------------------------------

class PalancaInfo(BaseModel):
    nombre: str
    descripcion: str
    minimo: float
    maximo: float
    actual: float


class MetodoInfo(BaseModel):
    nombre: NombreMetodo
    descripcion: str
    palancas: list[PalancaInfo]


class FilaGrupo(BaseModel):
    grupo: str
    estudiantes: int
    ingreso_real_mm: float
    ingreso_simulado_mm: float
    brecha_mm: float
    brecha_pct: float


class SimulacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    creada: datetime | None = None
    metodo: NombreMetodo
    parametros: dict[str, float]
    periodos: list[int] | None = None
    ingreso_real_mm: float
    ingreso_simulado_mm: float
    brecha_mm: float
    brecha_pct: float
    en_equilibrio: bool = False
    detalle: list[FilaGrupo] = []


class EquilibrioResponse(BaseModel):
    metodo: NombreMetodo
    palanca: str
    valor: float
    parametros: dict[str, float]
    brecha_mm: float
    detalle: list[FilaGrupo]


class PrediccionResponse(BaseModel):
    id: int
    metodo: NombreMetodo
    parametros: dict[str, float]
    brecha_predicha_mm: float
    brecha_exacta_mm: float = Field(description="Lo que da el simulador exacto, para comparar")
    en_equilibrio: bool
    version_modelo: str


class ResumenBrecha(BaseModel):
    minimo: float
    p05: float
    mediana: float
    p95: float
    maximo: float
    media: float


class MonteCarloResponse(BaseModel):
    metodo: NombreMetodo
    n: int
    brecha_mm: ResumenBrecha
    proporcion_equilibrio: float
    ejemplos_equilibrio: list[dict[str, float]]


class FilaPeriodo(BaseModel):
    periodo: int
    muestra: Literal["entrenamiento", "prueba"]
    ingreso_real_mm: float
    brecha_pct_actual: float
    brecha_pct_calibrado: float
    valor_equilibrio_periodo: float | None


class ValidacionTemporalResponse(BaseModel):
    metodo: NombreMetodo
    palanca: str
    ultimo_periodo_entrenamiento: int
    valor_calibrado: float
    brecha_pct_entrenamiento: float
    brecha_pct_prueba: float
    por_periodo: list[FilaPeriodo]


class SaludResponse(BaseModel):
    status: Literal["ok"] = "ok"
    entorno: str
    modelos_cargados: list[str]
    celdas_base: int
