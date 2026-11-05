"""Contrato HTTP de la API (TestClient)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health(cliente: TestClient) -> None:
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_metodos_lista_las_palancas(cliente: TestClient) -> None:
    metodos = {m["nombre"]: m for m in cliente.get("/metodos").json()}
    assert set(metodos) == {"creditos", "bandas"}
    assert "k_parcial" in {p["nombre"] for p in metodos["bandas"]["palancas"]}


def test_balance_por_facultad(cliente: TestClient) -> None:
    r = cliente.get("/balance/bandas").json()
    assert r["brecha_pct"] == pytest.approx(-2.13, abs=0.005)
    assert len(r["detalle"]) == 7


def test_crear_y_consultar_simulacion(cliente: TestClient) -> None:
    r = cliente.post("/simulaciones", json={"parametros": {"metodo": "creditos", "factor_tarifa": 1.1}})
    assert r.status_code == 201
    creada = r.json()
    assert cliente.get(f"/simulaciones/{creada['id']}").json()["brecha_mm"] == pytest.approx(creada["brecha_mm"])
    assert len(cliente.get("/simulaciones").json()) == 1
    assert cliente.delete(f"/simulaciones/{creada['id']}").status_code == 204
    assert cliente.get(f"/simulaciones/{creada['id']}").status_code == 404


def test_simulacion_inexistente_da_404(cliente: TestClient) -> None:
    assert cliente.get("/simulaciones/999").status_code == 404


@pytest.mark.parametrize("cuerpo", [
    {},
    {"parametros": {"metodo": "otro"}},
    {"parametros": {"metodo": "bandas", "k_parcial": 10}},
    {"parametros": {"metodo": "creditos", "factor_tarifa": -1}},
    {"parametros": {"metodo": "creditos"}, "periodos": [20193]},
    {"parametros": {"metodo": "creditos"}, "periodos": [20191]},   # formato válido, sin datos
])
def test_entradas_invalidas_dan_422(cliente: TestClient, cuerpo: dict) -> None:
    assert cliente.post("/simulaciones", json=cuerpo).status_code == 422


def test_equilibrio(cliente: TestClient) -> None:
    r = cliente.post("/equilibrio", json={"metodo": "bandas", "palanca": "k_parcial"})
    assert r.status_code == 200
    assert r.json()["valor"] == pytest.approx(1.2784, abs=1e-4)
    assert r.json()["brecha_mm"] == pytest.approx(0, abs=1e-6)


def test_equilibrio_palanca_ajena_da_422(cliente: TestClient) -> None:
    r = cliente.post("/equilibrio", json={"metodo": "creditos", "palanca": "k_parcial"})
    assert r.status_code == 422


def test_equilibrio_imposible_da_400(cliente: TestClient) -> None:
    r = cliente.post("/equilibrio", json={"metodo": "bandas", "palanca": "tarifa_extra",
                                          "fijos": {"k_parcial": 0.5}})
    assert r.status_code == 400


def test_montecarlo(cliente: TestClient) -> None:
    r = cliente.post("/montecarlo", json={"metodo": "creditos", "n": 200})
    assert r.status_code == 200
    resumen = r.json()["brecha_mm"]
    assert resumen["minimo"] <= resumen["mediana"] <= resumen["maximo"]


def test_validacion_temporal(cliente: TestClient) -> None:
    r = cliente.get("/validacion-temporal/bandas").json()
    assert r["brecha_pct_entrenamiento"] == pytest.approx(0, abs=1e-6)
    assert {f["muestra"] for f in r["por_periodo"]} == {"entrenamiento", "prueba"}
