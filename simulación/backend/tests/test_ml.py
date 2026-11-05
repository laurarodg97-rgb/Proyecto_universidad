"""Modelo de ML: Singleton, /predict y consistencia con el simulador."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.ml.predictor import ModelStore


def test_singleton_devuelve_la_misma_instancia(cliente: TestClient) -> None:
    assert ModelStore.get() is ModelStore.get()


def test_predict_se_parece_al_simulador(cliente: TestClient) -> None:
    for parametros in ({"metodo": "creditos", "factor_tarifa": 1.2, "elasticidad": 0.1},
                       {"metodo": "bandas", "k_parcial": 1.4, "tarifa_extra": 1.5}):
        r = cliente.post("/predict", json={"parametros": parametros})
        assert r.status_code == 201
        cuerpo = r.json()
        assert cuerpo["brecha_predicha_mm"] == pytest.approx(cuerpo["brecha_exacta_mm"], abs=1.0)


def test_predicciones_quedan_registradas(cliente: TestClient) -> None:
    cliente.post("/predict", json={"parametros": {"metodo": "bandas"}})
    assert len(cliente.get("/predicciones").json()) == 1


def test_predict_valida_entradas(cliente: TestClient) -> None:
    r = cliente.post("/predict", json={"parametros": {"metodo": "bandas", "elasticidad": 2}})
    assert r.status_code == 422


def test_sin_modelo_responde_503(cliente: TestClient, tmp_path) -> None:
    ruta_original = ModelStore.ruta
    ModelStore.reset()
    ModelStore.configurar(tmp_path)          # carpeta sin modelos
    try:
        r = cliente.post("/predict", json={"parametros": {"metodo": "bandas"}})
        assert r.status_code == 503
    finally:
        ModelStore.reset()
        ModelStore.configurar(ruta_original)
