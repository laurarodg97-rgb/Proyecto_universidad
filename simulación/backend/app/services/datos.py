"""Carga de la base agregada (FACULTAD × PERIODO × BANDA)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNAS = ["FACULTAD", "PERIODO", "BANDA", "N", "SUM_CREDITOS", "INGRESO_REAL", "M_NETO",
            "M_NETO_12_13", "T_EXTRA_NETO", "T2_EXTRA_19_20", "CT_NETO_REAL"]


def cargar_base_agregada(ruta: Path | str) -> pd.DataFrame:
    """Lee la base agregada y comprueba que tenga las columnas esperadas."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe la base agregada: {ruta}. "
                                "Genérela con scripts/preparar_agregados.py")
    celdas = pd.read_csv(ruta, sep=";", encoding="utf-8")
    faltantes = set(COLUMNAS) - set(celdas.columns)
    if faltantes:
        raise ValueError(f"A la base agregada le faltan columnas: {sorted(faltantes)}")
    celdas["BANDA"] = celdas.BANDA.astype(str)
    return celdas[COLUMNAS]
