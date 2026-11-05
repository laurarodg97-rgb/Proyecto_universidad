"""Prepara la base agregada que usa la API a partir de matriculas_anon.csv.

La base de estudiantes NUNCA se sube al repositorio ni a la imagen Docker.
Este script se corre una vez, en local, y escribe una tabla por
FACULTAD × PERIODO × BANDA con las sumas que necesita el simulador.
Como el cobro de los dos métodos es lineal dentro de cada celda, las
sumas reproducen exactamente los totales calculados fila a fila
(ver ``verificar_exactitud``).

Uso (desde simulacion_ml/):

    RUTA_DATOS=/ruta/matriculas_anon.csv python scripts/preparar_agregados.py

Repite la preparación de ``Proyecto_u.R`` y ``metodo_bandas/01_preparar_base.R``
y ``02_cobro_bandas.R`` para que los totales cuadren con lo ya presentado.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI.parent / "backend" / "app" / "data" / "base_agregada.csv"

CORTES = (6, 11, 18)
BANDAS = ("1-6", "7-11", "12-18", "19+")
MINIMO_POR_CELDA = 5   # ninguna celda publicada describe a menos de 5 estudiantes


def buscar_base() -> Path:
    candidatas = [
        os.environ.get("RUTA_DATOS", ""),
        AQUI.parent / "datos" / "matriculas_anon.csv",
        AQUI.parent.parent / "metodo_bandas" / "datos" / "matriculas_anon.csv",
    ]
    for ruta in candidatas:
        if ruta and Path(ruta).is_file():
            return Path(ruta)
    sys.exit("No se encontró matriculas_anon.csv. Póngala en datos/ o defina RUTA_DATOS.")


def cargar_matriculas(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, sep=";", encoding="utf-8-sig", na_values=["", "NA", "NULL"],
                     dtype={"ID_EST": str, "ID_PROGRAMA_EST": str,
                            "PER_INGRESO": str, "N_REINTEGROS": str})
    df["CREDITOS_INSCRITOS"] = df["CREDITOS_INSCRITOS"].astype(float)
    # Misma imputación de VAL_PAGADO que Proyecto_u.R
    mediana_derecho = df.loc[(df.PROGRAMA_ACADEMICO == "DERECHO") & (df.PERIODO == 20212),
                             "VAL_PAGADO"].median()
    df["VAL_PAGADO"] = df["VAL_PAGADO"].fillna(mediana_derecho)
    return df


def agregar_tarifas_plenas(df: pd.DataFrame) -> pd.DataFrame:
    """T (tarifa plena por crédito) y M (matrícula plena) por programa-periodo,
    con la facultad-periodo como respaldo."""
    ref = df[~df.MATRICULA_SIMBOLICA & ~df.SUBSIDIO_EXTERNO
             & (df.CREDITOS_INSCRITOS >= 12) & (df.VAL_PAGADO > 0)].copy()
    ref["VAL_CRED"] = ref.VAL_PAGADO / ref.CREDITOS_INSCRITOS

    def medianas(clave: str, sufijo: str) -> pd.DataFrame:
        return (ref.groupby([clave, "PERIODO"])
                   .agg(**{f"T_{sufijo}": ("VAL_CRED", "median"),
                           f"M_{sufijo}": ("VAL_PAGADO", "median")})
                   .reset_index())

    df = (df.merge(medianas("PROGRAMA_ACADEMICO", "PROG"), how="left",
                   on=["PROGRAMA_ACADEMICO", "PERIODO"])
            .merge(medianas("FACULTAD", "FAC"), how="left", on=["FACULTAD", "PERIODO"]))
    df["T"] = df.T_PROG.fillna(df.T_FAC)
    df["M"] = df.M_PROG.fillna(df.M_FAC)
    return df.drop(columns=["T_PROG", "T_FAC", "M_PROG", "M_FAC"])


def preparar_base(ruta: Path) -> pd.DataFrame:
    """Base del balance (no simbólica, créditos > 0) con banda y las dos becas."""
    df = agregar_tarifas_plenas(cargar_matriculas(ruta))

    # Beca del cobro por créditos (Proyecto_u.R): descuento frente a M
    df["PCT_BECA_REAL"] = np.select(
        [df.MATRICULA_SIMBOLICA | (df.M == 0), df.VAL_PAGADO >= df.M],
        [0.0, 0.0], default=np.round(1 - df.VAL_PAGADO / df.M, 4))

    base = df[~df.MATRICULA_SIMBOLICA & (df.CREDITOS_INSCRITOS > 0)].copy()
    base["BANDA_IDX"] = np.searchsorted(np.asarray(CORTES, float),
                                        base.CREDITOS_INSCRITOS.to_numpy(), side="left")

    # Beca del cobro por bandas (02_cobro_bandas.R): descuento frente a la
    # mediana de lo que hoy paga un estudiante sin subsidio de su facultad y banda
    ref = base[~base.SUBSIDIO_EXTERNO & (base.VAL_PAGADO > 0) & (base.M > 0)]
    fraccion_actual = ((ref.VAL_PAGADO / ref.M)
                       .groupby([ref.FACULTAD, ref.BANDA_IDX]).median()
                       .rename("FRACCION_ACTUAL").reset_index())
    base = base.merge(fraccion_actual, how="left", on=["FACULTAD", "BANDA_IDX"])
    esperado = base.FRACCION_ACTUAL.fillna(1) * base.M
    base["PCT_BECA_BANDA"] = np.select(
        [esperado <= 0, base.VAL_PAGADO >= esperado], [0.0, 0.0],
        default=np.round(1 - base.VAL_PAGADO / esperado, 4))
    return base


def agregar(base: pd.DataFrame) -> pd.DataFrame:
    """Sumas por FACULTAD × PERIODO × BANDA.

    Columnas (todas en pesos salvo N y SUM_CREDITOS):
      N               estudiantes-periodo
      SUM_CREDITOS    créditos inscritos
      INGRESO_REAL    VAL_PAGADO
      M_NETO          Σ M (1 - beca banda)
      M_NETO_12_13    lo mismo, solo quienes inscriben 12 o 13 créditos
      T_EXTRA_NETO    Σ T (créditos - 18) (1 - beca banda), créditos > 18
      T2_EXTRA_19_20  Σ T² (créditos - 18)² (1 - beca banda) / M, 19 o 20 créditos
      CT_NETO_REAL    Σ créditos × T (1 - beca real)   (cobro por créditos)
    """
    c, M, T = base.CREDITOS_INSCRITOS, base.M, base["T"]
    neto_banda = 1 - base.PCT_BECA_BANDA
    extra = np.maximum(c - CORTES[-1], 0)
    columnas = pd.DataFrame({
        "FACULTAD": base.FACULTAD,
        "PERIODO": base.PERIODO,
        "BANDA": pd.Categorical.from_codes(base.BANDA_IDX, BANDAS),
        "N": 1,
        "SUM_CREDITOS": c,
        "INGRESO_REAL": base.VAL_PAGADO,
        "M_NETO": M * neto_banda,
        "M_NETO_12_13": np.where(c.between(12, 13), M * neto_banda, 0.0),
        "T_EXTRA_NETO": T * extra * neto_banda,
        "T2_EXTRA_19_20": np.where(c.between(19, 20), T**2 * extra**2 * neto_banda / M, 0.0),
        "CT_NETO_REAL": c * T * (1 - base.PCT_BECA_REAL),
    })
    agregada = (columnas.groupby(["FACULTAD", "PERIODO", "BANDA"], observed=True)
                        .sum().reset_index())
    pequenas = agregada[agregada.N < MINIMO_POR_CELDA]
    if not pequenas.empty:
        sys.exit(f"Hay {len(pequenas)} celdas con menos de {MINIMO_POR_CELDA} estudiantes; "
                 "revise la agregación antes de publicar.")
    return agregada


def verificar_exactitud(base: pd.DataFrame, agregada: pd.DataFrame) -> None:
    """Los totales de la base agregada deben ser los mismos que fila a fila."""
    esperados = {
        "INGRESO_REAL": base.VAL_PAGADO.sum(),
        "CT_NETO_REAL": (base.CREDITOS_INSCRITOS * base["T"] * (1 - base.PCT_BECA_REAL)).sum(),
    }
    for col, valor in esperados.items():
        assert np.isclose(agregada[col].sum(), valor, rtol=1e-12), col
    print(f"Ingreso real:        {agregada.INGRESO_REAL.sum() / 1e9:,.2f} mil millones")
    print(f"Cobro por créditos:  {agregada.CT_NETO_REAL.sum() / 1e9:,.2f} mil millones")


def main() -> None:
    base = preparar_base(buscar_base())
    agregada = agregar(base)
    verificar_exactitud(base, agregada)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    agregada.to_csv(SALIDA, index=False, sep=";", float_format="%.6f")
    print(f"{len(agregada)} celdas (mínimo {agregada.N.min()} estudiantes) → {SALIDA}")


if __name__ == "__main__":
    main()
