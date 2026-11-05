"""Tablero del simulador de equilibrio. Solo consume la API; no calcula.

    BACKEND_URL=http://localhost:8000 streamlit run app.py
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
if not BACKEND_URL.startswith("http"):
    BACKEND_URL = f"https://{BACKEND_URL}"   # Render entrega solo el host

NOMBRES = {"creditos": "Cobro por créditos", "bandas": "Cobro por bandas"}

st.set_page_config(page_title="Simulador de equilibrio", page_icon="⚖️", layout="wide")


def api(metodo_http: str, ruta: str, **kwargs: Any) -> Any:
    try:
        r = requests.request(metodo_http, f"{BACKEND_URL}{ruta}", timeout=60, **kwargs)
    except requests.RequestException as e:
        st.error(f"No se pudo conectar con la API en {BACKEND_URL}: {e}")
        st.stop()
    if r.status_code >= 400:
        detalle = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith(
            "application/json") else r.text
        st.warning(f"La API respondió {r.status_code}: {detalle}")
        return None
    return r.json() if r.content else None


@st.cache_data(ttl=600)
def metodos() -> dict[str, dict]:
    return {m["nombre"]: m for m in api("GET", "/metodos")}


def tabla_detalle(detalle: list[dict]) -> pd.DataFrame:
    return (pd.DataFrame(detalle)
              .rename(columns={"grupo": "Grupo", "estudiantes": "Estudiantes",
                               "ingreso_real_mm": "Real (MM)", "ingreso_simulado_mm": "Simulado (MM)",
                               "brecha_mm": "Brecha (MM)", "brecha_pct": "Brecha (%)"})
              .round(2))


st.title("Simulador del punto de equilibrio")
st.caption("Ingreso por matrícula 2021-1 a 2026-1, en miles de millones de pesos (MM). "
           "El equilibrio es el punto donde el ingreso simulado es igual al real.")

catalogo = metodos()
metodo = st.sidebar.radio("Método", list(catalogo), format_func=NOMBRES.get)
st.sidebar.markdown(catalogo[metodo]["descripcion"])

valores: dict[str, float] = {}
for p in catalogo[metodo]["palancas"]:
    valores[p["nombre"]] = st.sidebar.slider(
        p["nombre"], float(p["minimo"]), float(p["maximo"]), float(p["actual"]),
        step=0.001, help=p["descripcion"])

tab_sim, tab_eq, tab_tiempo, tab_hist = st.tabs(
    ["Simular", "Buscar equilibrio", "Estabilidad en el tiempo", "Historial"])

with tab_sim:
    parametros = {"metodo": metodo, **valores}
    sim = api("POST", "/simulaciones", json={"parametros": parametros})
    pred = api("POST", "/predict", json={"parametros": parametros})
    if sim:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingreso real", f"{sim['ingreso_real_mm']:,.2f}")
        c2.metric("Ingreso simulado", f"{sim['ingreso_simulado_mm']:,.2f}",
                  f"{sim['brecha_pct']:+.2f} %")
        c3.metric("Brecha (simulador exacto)", f"{sim['brecha_mm']:+,.2f}")
        if pred:
            c4.metric("Brecha (modelo de ML)", f"{pred['brecha_predicha_mm']:+,.2f}",
                      help=pred["version_modelo"])
        if sim["en_equilibrio"]:
            st.success("Estos parámetros están en equilibrio.")
        detalle = tabla_detalle(sim["detalle"])
        st.subheader("Brecha por facultad")
        st.bar_chart(detalle.set_index("Grupo")["Brecha (%)"], horizontal=True)
        st.dataframe(detalle, hide_index=True, width="stretch")

with tab_eq:
    nombres = [p["nombre"] for p in catalogo[metodo]["palancas"] if p["nombre"] != "elasticidad"]
    palanca = st.selectbox("Palanca que se mueve", nombres)
    fijos = {k: v for k, v in valores.items() if k != palanca}
    st.caption(f"Las demás palancas quedan como en la barra lateral: {fijos}")
    if st.button("Calcular equilibrio", type="primary"):
        eq = api("POST", "/equilibrio", json={"metodo": metodo, "palanca": palanca, "fijos": fijos})
        if eq:
            st.metric(f"{palanca} de equilibrio", f"{eq['valor']:.4f}")
            st.dataframe(tabla_detalle(eq["detalle"]), hide_index=True, width="stretch")

with tab_tiempo:
    vt = api("GET", f"/validacion-temporal/{metodo}")
    if vt:
        st.markdown(f"Calibrando **{vt['palanca']}** solo con los periodos hasta "
                    f"{vt['ultimo_periodo_entrenamiento']} sale **{vt['valor_calibrado']:.4f}**. "
                    f"Con ese valor, la brecha de los periodos siguientes es "
                    f"**{vt['brecha_pct_prueba']:+.2f} %**.")
        periodos = pd.DataFrame(vt["por_periodo"]).set_index("periodo")
        periodos.index = periodos.index.astype(str)
        st.line_chart(periodos[["brecha_pct_actual", "brecha_pct_calibrado"]])
        st.dataframe(periodos.round(3), width="stretch")

with tab_hist:
    historial = api("GET", "/simulaciones", params={"limite": 100})
    if historial:
        st.dataframe(pd.DataFrame(historial).drop(columns=["detalle"], errors="ignore"),
                     hide_index=True, width="stretch")
