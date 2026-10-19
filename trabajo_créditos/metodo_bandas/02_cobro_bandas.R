library(tidyverse)

# ============================================================
# 02. COBRO POR BANDAS
# ============================================================
# Requiere 01_preparar_base.R (objetos Matriculas y base_balance).
#
# Cada estudiante-periodo cae en una banda según CREDITOS_INSCRITOS
# y paga FRACCION_MATRICULA × M, con M = MATRICULA_PLENA_BASE. En la
# banda con COBRO_CREDITO_EXTRA = TRUE se suma T por cada crédito
# por encima del tope de la banda anterior (T = TARIFA_PLENA_CREDITO_BASE).
#
# Escenarios:
#   - Ingreso real observado
#   - Cobro por créditos (el de Proyecto_u.R)
#   - Bandas uniformes: bandas.csv, iguales para todas las facultades
#   - Bandas por facultad: misma estructura, con las fracciones de
#     las bandas parciales según los créditos que inscribe cada banda
#     frente a la carga completa de su facultad

parametros_bandas <- read_delim(
  "bandas.csv", delim = ";",
  col_types = cols(
    FACULTAD = col_character(), BANDA = col_character(),
    CREDITOS_MIN = col_double(), CREDITOS_MAX = col_double(),
    FRACCION_MATRICULA = col_double(), COBRO_CREDITO_EXTRA = col_logical()
  )
)

# ------------------------------------------------------------
# Asignar banda: la primera cuyo tope (CREDITOS_MAX) cubre los
# créditos inscritos. Así un valor fraccionario (p. ej. 6.5) cae
# en la banda siguiente y no queda sin banda.
# ------------------------------------------------------------
bandas_base <- parametros_bandas %>%
  dplyr::filter(FACULTAD == "TODAS") %>%
  arrange(CREDITOS_MAX)

asignar_banda <- function(creditos) {
  idx <- findInterval(creditos, bandas_base$CREDITOS_MAX, left.open = TRUE) + 1
  idx <- pmin(idx, nrow(bandas_base))
  factor(bandas_base$BANDA[idx], levels = bandas_base$BANDA)
}

base_bandas <- base_balance %>%
  mutate(BANDA = asignar_banda(CREDITOS_INSCRITOS))

# ------------------------------------------------------------
# Beca relativa a la banda
# ------------------------------------------------------------
# PCT_BECA_REAL (Proyecto_u.R) mide el descuento contra la
# matrícula plena M. Para carga parcial eso confunde descuento con
# el menor cobro que ya existe hoy: quien inscribe 1–6 créditos
# paga en mediana cerca del 20 % de M sin tener beca. Aplicar ese
# "descuento" sobre un cobro por bandas lo descontaría dos veces.
#
# Por eso aquí la beca se mide contra lo que hoy paga, en mediana,
# un estudiante sin subsidio de la misma facultad y banda.
# En 12–18 créditos coincide con PCT_BECA_REAL.

pago_actual_banda <- base_bandas %>%
  dplyr::filter(!SUBSIDIO_EXTERNO, VAL_PAGADO > 0, MATRICULA_PLENA_BASE > 0) %>%
  group_by(FACULTAD, BANDA) %>%
  summarise(
    FRACCION_ACTUAL = median(VAL_PAGADO / MATRICULA_PLENA_BASE),
    n_referencia    = n(),
    .groups = "drop"
  )

base_bandas <- base_bandas %>%
  left_join(pago_actual_banda %>% select(FACULTAD, BANDA, FRACCION_ACTUAL),
            by = c("FACULTAD", "BANDA")) %>%
  mutate(
    PAGO_ACTUAL_ESPERADO = coalesce(FRACCION_ACTUAL, 1) * MATRICULA_PLENA_BASE,
    PCT_BECA_BANDA = case_when(
      PAGO_ACTUAL_ESPERADO <= 0                ~ 0,
      VAL_PAGADO >= PAGO_ACTUAL_ESPERADO       ~ 0,
      TRUE ~ round(1 - VAL_PAGADO / PAGO_ACTUAL_ESPERADO, 4)
    )
  )

# ------------------------------------------------------------
# Cobro por bandas para un juego de parámetros
# ------------------------------------------------------------
# `parametros` tiene una fila por banda y, si se quiere, por
# facultad. Las facultades sin filas propias usan las de "TODAS".
completar_parametros <- function(parametros) {
  facultades <- unique(base_bandas$FACULTAD)
  generales  <- parametros %>% dplyr::filter(FACULTAD == "TODAS")
  propias    <- parametros %>% dplyr::filter(FACULTAD != "TODAS")
  faltantes  <- setdiff(facultades, unique(propias$FACULTAD))
  bind_rows(
    propias,
    tidyr::crossing(FACULTAD = faltantes, generales %>% select(-FACULTAD))
  )
}

calcular_cobro <- function(base, parametros) {
  tope_previo <- bandas_base %>%
    transmute(BANDA, TOPE_PREVIO = lag(CREDITOS_MAX, default = 0))

  base %>%
    select(-any_of(c("FRACCION_MATRICULA", "COBRO_CREDITO_EXTRA"))) %>%
    left_join(
      completar_parametros(parametros) %>%
        mutate(BANDA = factor(BANDA, levels = levels(base$BANDA))) %>%
        select(FACULTAD, BANDA, FRACCION_MATRICULA, COBRO_CREDITO_EXTRA),
      by = c("FACULTAD", "BANDA")
    ) %>%
    left_join(tope_previo %>% mutate(BANDA = factor(BANDA, levels = levels(base$BANDA))),
              by = "BANDA") %>%
    mutate(
      INGRESO_BANDAS_PURO = FRACCION_MATRICULA * MATRICULA_PLENA_BASE +
        ifelse(COBRO_CREDITO_EXTRA,
               TARIFA_PLENA_CREDITO_BASE * pmax(CREDITOS_INSCRITOS - TOPE_PREVIO, 0),
               0),
      INGRESO_BANDAS_NETO = INGRESO_BANDAS_PURO * (1 - PCT_BECA_BANDA)
    ) %>%
    select(-TOPE_PREVIO)
}

# ------------------------------------------------------------
# Escenario 1: bandas uniformes (bandas.csv tal cual)
# ------------------------------------------------------------
bandas_uniformes <- calcular_cobro(base_bandas, parametros_bandas)

# ------------------------------------------------------------
# Escenario 2: bandas por facultad, proporcionales a la carga
# ------------------------------------------------------------
# Se conservan 12–18 = M y el cobro extra en 19+. En cada facultad,
# las bandas parciales (1–6 y 7–11) cobran la proporción de créditos
# que inscriben frente a la carga completa de esa misma facultad:
#   fracción = créditos promedio de la banda / créditos promedio de 12–18
# Así cada facultad tiene bandas propias calculadas con sus datos.
bandas_parciales <- bandas_base %>%
  dplyr::filter(FRACCION_MATRICULA < 1) %>%
  pull(BANDA)

banda_completa <- bandas_base %>%
  dplyr::filter(FRACCION_MATRICULA == 1, !COBRO_CREDITO_EXTRA) %>%
  pull(BANDA)

creditos_banda_facultad <- base_bandas %>%
  group_by(FACULTAD, BANDA) %>%
  summarise(CREDITOS_PROMEDIO = mean(CREDITOS_INSCRITOS), .groups = "drop") %>%
  group_by(FACULTAD) %>%
  mutate(PROPORCION_CARGA = CREDITOS_PROMEDIO / CREDITOS_PROMEDIO[BANDA == banda_completa]) %>%
  ungroup()

parametros_por_facultad <- tidyr::crossing(FACULTAD = sort(unique(base_bandas$FACULTAD)),
                                           bandas_base %>% select(-FACULTAD)) %>%
  left_join(creditos_banda_facultad %>%
              mutate(BANDA = as.character(BANDA)) %>%
              select(FACULTAD, BANDA, PROPORCION_CARGA),
            by = c("FACULTAD", "BANDA")) %>%
  mutate(FRACCION_MATRICULA = ifelse(BANDA %in% bandas_parciales,
                                     pmin(PROPORCION_CARGA, 1),
                                     FRACCION_MATRICULA)) %>%
  select(FACULTAD, BANDA, CREDITOS_MIN, CREDITOS_MAX, FRACCION_MATRICULA, COBRO_CREDITO_EXTRA)

bandas_por_facultad <- calcular_cobro(base_bandas, parametros_por_facultad)

# ------------------------------------------------------------
# Balances (solo agregados; no se escriben filas por estudiante)
# ------------------------------------------------------------
resumir <- function(df, ...) {
  df %>%
    group_by(...) %>%
    summarise(
      Estudiantes          = n(),
      Ingreso_Real_MM      = sum(VAL_PAGADO) / 1e9,
      Ingreso_CF_Neto_MM   = sum(INGRESO_CF_NETO) / 1e9,
      Ingreso_Bandas_MM    = sum(INGRESO_BANDAS_NETO) / 1e9,
      .groups = "drop"
    ) %>%
    mutate(
      Diferencia_CF_MM      = Ingreso_CF_Neto_MM - Ingreso_Real_MM,
      Diferencia_Bandas_MM  = Ingreso_Bandas_MM - Ingreso_Real_MM,
      Variacion_Pct_CF      = Diferencia_CF_MM / Ingreso_Real_MM * 100,
      Variacion_Pct_Bandas  = Diferencia_Bandas_MM / Ingreso_Real_MM * 100
    )
}

escenarios <- list(
  "Bandas uniformes"    = bandas_uniformes,
  "Bandas por facultad" = bandas_por_facultad
)

balance_global_bandas <- imap_dfr(escenarios, ~ resumir(.x) %>% mutate(Escenario = .y, .before = 1))

balance_facultad_bandas <- imap_dfr(escenarios, ~ resumir(.x, FACULTAD) %>% mutate(Escenario = .y, .before = 1))

balance_periodo_bandas <- imap_dfr(escenarios, ~ resumir(.x, PERIODO) %>% mutate(Escenario = .y, .before = 1))

balance_banda <- imap_dfr(escenarios, ~ resumir(.x, BANDA) %>% mutate(Escenario = .y, .before = 1))

# Quién paga más o menos que hoy con cada escenario. Diferencias
# menores a $1.000 cuentan como "igual": VAL_PAGADO está redondeado
# al millar y PCT_BECA_BANDA a 4 decimales.
umbral_igual <- 1000

ganadores_bandas <- imap_dfr(escenarios, ~ .x %>%
  mutate(DIF = INGRESO_BANDAS_NETO - VAL_PAGADO) %>%
  group_by(BANDA) %>%
  summarise(
    Paga_mas   = sum(DIF >= umbral_igual),
    Igual      = sum(abs(DIF) < umbral_igual),
    Paga_menos = sum(DIF <= -umbral_igual),
    .groups = "drop"
  ) %>%
  mutate(Escenario = .y, .before = 1))

print(balance_global_bandas)
