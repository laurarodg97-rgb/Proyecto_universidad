# Método por bandas

Simula cobrar la matrícula por **bandas de créditos** y la compara con el ingreso real y con el cobro por créditos de `../Proyecto_u.R`. No modifica ningún archivo existente.

## Cómo se cobra

Cada estudiante-periodo cae en una banda según `CREDITOS_INSCRITOS` y paga una fracción de la matrícula plena de su programa (M = `MATRICULA_PLENA_BASE`, la misma mediana de `Proyecto_u.R`).

| Banda | Bandas uniformes (`bandas.csv`) | Bandas por facultad |
|---|---|---|
| 1–6 | 0,50 × M | calibrada por facultad |
| 7–11 | 0,75 × M | calibrada por facultad |
| 12–18 | M | M |
| 19+ | M + T × (créditos − 18) | M + T × (créditos − 18) |

T es la tarifa plena por crédito (`TARIFA_PLENA_CREDITO_BASE`).

**Bandas por facultad.** En cada facultad se multiplican las fracciones de 1–6 y 7–11 por un mismo factor hasta que su ingreso neto iguala el ingreso real. El resultado queda en `resultados/bandas_por_facultad.csv`.

**Beca.** El escenario neto descuenta la beca de cada estudiante, pero medida contra lo que hoy paga en mediana un estudiante sin subsidio de su misma facultad y banda (`PCT_BECA_BANDA`). Con `PCT_BECA_REAL` de `Proyecto_u.R`, el menor cobro que ya tiene hoy la carga parcial se tomaría como beca y se descontaría dos veces. En 12–18 créditos las dos medidas coinciden.

Como en el análisis por créditos, el modelo es estático: supone que nadie cambia cuántos créditos inscribe.

## Ejecutar

1. Copiar `matriculas_anon.csv` en `datos/` (o definir `RUTA_DATOS` con la ruta completa). **La base nunca se sube al repositorio**: `datos/` y los CSV están en `.gitignore`.
2. Desde esta carpeta: `Rscript run_all.R`.

Requiere `tidyverse`; las tablas de `03_tablas_graficas.R` usan `gt` si está instalado.

| Archivo | Qué hace |
|---|---|
| `01_preparar_base.R` | Carga y limpieza de `Proyecto_u.R`, tarifas plenas y escenario por créditos |
| `02_cobro_bandas.R` | Asigna bandas, calibra por facultad y calcula balances |
| `03_tablas_graficas.R` | Escribe `resultados/` (solo agregados) y `graficas/` |
| `bandas.csv` | Cortes y fracciones; una fila con `FACULTAD` distinta de `TODAS` reemplaza las generales para esa facultad |
