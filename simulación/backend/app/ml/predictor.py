"""Carga del modelo con el patrón Singleton y predicción."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, ClassVar

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline


class ModelStore:
    """Mantiene en memoria una única instancia de los modelos entrenados.

    Se cargan una sola vez (al arrancar el servicio o en la primera
    petición) con doble verificación y cerrojo, como en el módulo 13.
    """

    _modelos: ClassVar[dict[str, Pipeline] | None] = None
    _metadata: ClassVar[dict[str, Any]] = {}
    _lock: ClassVar[Lock] = Lock()
    ruta: ClassVar[Path | None] = None

    @classmethod
    def configurar(cls, ruta: Path) -> None:
        cls.ruta = Path(ruta)

    @classmethod
    def get(cls) -> dict[str, Pipeline]:
        if cls._modelos is None:
            with cls._lock:
                if cls._modelos is None:
                    if cls.ruta is None:
                        raise RuntimeError("ModelStore no está configurado")
                    meta = json.loads((cls.ruta / "metadata.json").read_text(encoding="utf-8"))
                    cls._modelos = {m: joblib.load(cls.ruta / info["archivo"])
                                    for m, info in meta["modelos"].items()}
                    cls._metadata = meta
        return cls._modelos

    @classmethod
    def metadata(cls) -> dict[str, Any]:
        cls.get()
        return cls._metadata

    @classmethod
    def cargados(cls) -> list[str]:
        return sorted(cls._modelos) if cls._modelos else []

    @classmethod
    def reset(cls) -> None:
        """Útil para pruebas: olvida los modelos cargados."""
        with cls._lock:
            cls._modelos = None
            cls._metadata = {}


class ModelPredictor:
    """Predice la brecha de ingreso (mil millones) para unas palancas."""

    def __init__(self, modelos: dict[str, Pipeline], metadata: dict[str, Any]):
        self.modelos = modelos
        self.metadata = metadata

    def version(self, metodo: str) -> str:
        info = self.metadata["modelos"][metodo]
        return f"{info['modelo']} · {self.metadata['entrenado'][:10]}"

    def predecir(self, metodo: str, palancas: dict[str, float]) -> float:
        columnas = self.metadata["modelos"][metodo]["variables"]
        X = pd.DataFrame([[palancas[c] for c in columnas]], columns=columnas)
        return float(self.modelos[metodo].predict(X)[0])
