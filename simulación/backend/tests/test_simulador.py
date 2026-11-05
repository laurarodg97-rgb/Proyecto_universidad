"""El simulador reproduce lo ya presentado y encuentra el equilibrio."""

from __future__ import annotations

import pytest

from app.models.schemas import ParametrosBandas, ParametrosCreditos
from app.services.simulador import CobroPorBandas, CobroPorCreditos, Simulador


def test_cuadra_con_los_scripts_en_r(simulador: Simulador) -> None:
    creditos = simulador.simular("creditos")
    bandas = simulador.simular("bandas")
    assert creditos.ingreso_real / 1e9 == pytest.approx(394.56, abs=0.005)
    assert creditos.ingreso_simulado / 1e9 == pytest.approx(353.90, abs=0.005)
    assert bandas.ingreso_simulado / 1e9 == pytest.approx(386.14, abs=0.005)
    assert bandas.brecha_pct == pytest.approx(-2.13, abs=0.005)


@pytest.mark.parametrize("metodo, palanca", [
    ("creditos", "factor_tarifa"),
    ("bandas", "k_parcial"),
    ("bandas", "ajuste_plena"),
    ("bandas", "tarifa_extra"),
])
def test_equilibrio_deja_brecha_cero(simulador: Simulador, metodo: str, palanca: str) -> None:
    valor = simulador.equilibrio(metodo, palanca)
    assert simulador.brecha(metodo, {palanca: valor}) == pytest.approx(0, abs=1e-6)


def test_equilibrio_creditos_es_cociente_de_ingresos(simulador: Simulador) -> None:
    # Sin elasticidad el cobro es lineal en la tarifa: el factor es real / simulado
    r = simulador.simular("creditos")
    assert simulador.equilibrio("creditos", "factor_tarifa") == pytest.approx(
        r.ingreso_real / r.ingreso_simulado, rel=1e-9)


def test_elasticidad_exige_mas_ajuste(simulador: Simulador) -> None:
    for metodo, palanca in (("creditos", "factor_tarifa"), ("bandas", "k_parcial")):
        sin = simulador.equilibrio(metodo, palanca)
        con = simulador.equilibrio(metodo, palanca, {"elasticidad": 0.2})
        assert con > sin


def test_sin_equilibrio_lanza_error(simulador: Simulador) -> None:
    with pytest.raises(ValueError):
        simulador.equilibrio("bandas", "tarifa_extra", {"k_parcial": 0.5})


def test_suma_por_facultad_igual_al_total(simulador: Simulador) -> None:
    tabla = simulador.simular_por("FACULTAD", "bandas", {"k_parcial": 1.3})
    assert tabla.SIMULADO.sum() == pytest.approx(
        simulador.simular("bandas", {"k_parcial": 1.3}).ingreso_simulado)


@pytest.mark.parametrize("esquema, clase", [(ParametrosCreditos, CobroPorCreditos),
                                            (ParametrosBandas, CobroPorBandas)])
def test_esquema_y_simulador_comparten_rangos(esquema, clase) -> None:
    for p in clase.palancas:
        restricciones = {type(m).__name__: m for m in esquema.model_fields[p.nombre].metadata}
        assert restricciones["Ge"].ge == p.minimo
        assert restricciones["Le"].le == p.maximo
