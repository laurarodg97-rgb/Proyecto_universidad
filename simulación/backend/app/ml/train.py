"""Entrenamiento offline del metamodelo de cada método.

Para cada método se simulan escenarios Monte Carlo con el simulador
exacto y se entrena un modelo que aprende palancas → brecha (mil
millones). Se comparan varios modelos con validación cruzada y se
guarda el mejor como Pipeline con joblib, junto con su metadata.

Uso (desde backend/):

    python -m app.ml.train
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from app.config import get_settings
from app.services.datos import cargar_base_agregada
from app.services.simulador import Simulador

SEMILLA = 42
N_ESCENARIOS = 4000


def muestrear(simulador: Simulador, metodo: str, n: int, semilla: int) -> pd.DataFrame:
    """Escenarios uniformes dentro del rango válido de cada palanca, con su brecha exacta."""
    rng = np.random.default_rng(semilla)
    palancas = simulador.metodo(metodo).palancas
    X = pd.DataFrame({p.nombre: rng.uniform(p.minimo, p.maximo, n) for p in palancas})
    X["brecha_mm"] = [simulador.brecha(metodo, fila) for fila in X.to_dict("records")]
    return X


def candidatos() -> dict[str, Pipeline]:
    return {
        "Regresión lineal": Pipeline([("escala", StandardScaler()), ("modelo", LinearRegression())]),
        "Polinómica grado 3 (Ridge)": Pipeline([("escala", StandardScaler()),
                                                ("poli", PolynomialFeatures(3)),
                                                ("modelo", Ridge(alpha=1e-4))]),
        "Random Forest": Pipeline([("modelo", RandomForestRegressor(n_estimators=300, random_state=SEMILLA,
                                                                    n_jobs=-1))]),
        "Gradient Boosting": Pipeline([("modelo", GradientBoostingRegressor(n_estimators=600, learning_rate=0.05,
                                                                            max_depth=4, random_state=SEMILLA))]),
        "Red neuronal (MLP)": Pipeline([("escala", StandardScaler()),
                                        ("modelo", MLPRegressor(hidden_layer_sizes=(64, 64), max_iter=5000,
                                                                random_state=SEMILLA))]),
    }


def entrenar_metodo(simulador: Simulador, metodo: str) -> tuple[Pipeline, dict, pd.DataFrame]:
    datos = muestrear(simulador, metodo, N_ESCENARIOS, SEMILLA)
    X, y = datos.drop(columns="brecha_mm"), datos.brecha_mm
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEMILLA)

    cv = KFold(5, shuffle=True, random_state=SEMILLA)
    filas = []
    for nombre, pipe in candidatos().items():
        r = cross_validate(pipe, X_tr, y_tr, cv=cv, scoring=("r2", "neg_mean_absolute_error"))
        filas.append({"modelo": nombre, "r2_cv": r["test_r2"].mean(),
                      "mae_cv_mm": -r["test_neg_mean_absolute_error"].mean()})
    comparacion = pd.DataFrame(filas).sort_values("mae_cv_mm").reset_index(drop=True)

    mejor_nombre = comparacion.modelo[0]
    mejor = candidatos()[mejor_nombre].fit(X_tr, y_tr)
    pred = mejor.predict(X_te)
    info = {
        "modelo": mejor_nombre,
        "variables": list(X.columns),
        "r2_cv": float(comparacion.r2_cv[0]),
        "mae_cv_mm": float(comparacion.mae_cv_mm[0]),
        "r2_prueba": float(r2_score(y_te, pred)),
        "mae_prueba_mm": float(mean_absolute_error(y_te, pred)),
        "n_escenarios": N_ESCENARIOS,
    }
    # Para servir se reentrena con todos los escenarios
    mejor = candidatos()[mejor_nombre].fit(X, y)
    return mejor, info, comparacion.assign(metodo=metodo)


def main() -> None:
    settings = get_settings()
    simulador = Simulador(cargar_base_agregada(settings.ruta_base_agregada))
    salida = settings.ruta_modelos
    salida.mkdir(parents=True, exist_ok=True)

    metadata = {"entrenado": datetime.now(timezone.utc).isoformat(),
                "sklearn_version": sklearn.__version__, "semilla": SEMILLA, "modelos": {}}
    comparaciones = []
    for metodo in simulador.metodos:
        modelo, info, comparacion = entrenar_metodo(simulador, metodo)
        archivo = f"modelo_{metodo}.joblib"
        joblib.dump(modelo, salida / archivo, compress=3)
        metadata["modelos"][metodo] = {"archivo": archivo, **info}
        comparaciones.append(comparacion)
        print(f"{metodo}: {info['modelo']} · R² prueba {info['r2_prueba']:.5f} · "
              f"MAE {info['mae_prueba_mm']:.4f} mil millones")

    (salida / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                                          encoding="utf-8")
    pd.concat(comparaciones).to_csv(salida / "comparacion_modelos.csv", index=False,
                                    sep=";", decimal=",", float_format="%.6f")


if __name__ == "__main__":
    main()
