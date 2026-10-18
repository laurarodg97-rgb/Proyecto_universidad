library(tidyverse)

# ============================================================
# 01. PREPARAR LA BASE
# ============================================================
# Repite la carga y la limpieza de Proyecto_u.R sin modificarlo,
# para que el ingreso real y la tarifa plena cuadren con el
# análisis por créditos ya presentado.
#
# La base NO está en el repositorio. Se busca en:
#   1. la variable de entorno RUTA_DATOS (ruta completa al CSV), o
#   2. datos/matriculas_anon.csv (o .csv.gz) dentro de esta carpeta.

buscar_base <- function() {
  ruta_env <- Sys.getenv("RUTA_DATOS")
  candidatas <- c(
    if (nzchar(ruta_env)) ruta_env,
    "datos/matriculas_anon.csv",
    "datos/matriculas_anon.csv.gz"
  )
  ruta <- candidatas[file.exists(candidatas)][1]
  if (is.na(ruta)) {
    stop("No se encontró matriculas_anon.csv. Póngala en datos/ o defina RUTA_DATOS.")
  }
  ruta
}

cols_matriculas <- cols(
  ID_EST              = col_character(),
  ID_PROGRAMA_EST     = col_character(),
  PERIODO             = col_integer(),
  PROGRAMA_ACADEMICO  = col_character(),
  FACULTAD            = col_character(),
  COD_UNIDAD          = col_integer(),
  PENSUM_ESTUDIANTE   = col_character(),
  NIVEL_EST           = col_integer(),
  PER_INGRESO         = col_character(),
  ESTADO              = col_character(),
  ES_NUEVO            = col_logical(),
  SUBSIDIO_EXTERNO    = col_logical(),
  REINTEGRO           = col_logical(),
  N_REINTEGROS        = col_character(),
  VAL_PAGADO          = col_double(),
  PAGO                = col_character(),
  MATRICULA_SIMBOLICA = col_logical(),
  CREDITOS_INSCRITOS  = col_double(),
  N_MATERIAS          = col_integer(),
  N_MATERIAS_REPITE   = col_integer()
)

Matriculas <- read_delim(
  file = buscar_base(),
  delim = ";",
  locale = locale(decimal_mark = "."),
  col_types = cols_matriculas,
  na = c("", "NA", "NULL"),
  trim_ws = TRUE
)

# Misma imputación de VAL_PAGADO que Proyecto_u.R
mediana_derecho_20212 <- Matriculas %>%
  dplyr::filter(PROGRAMA_ACADEMICO == "DERECHO", PERIODO == 20212, !is.na(VAL_PAGADO)) %>%
  summarise(mediana = median(VAL_PAGADO)) %>%
  pull(mediana)

Matriculas <- Matriculas %>%
  mutate(VAL_PAGADO = ifelse(is.na(VAL_PAGADO), mediana_derecho_20212, VAL_PAGADO))

# Grupo de referencia: pagadores completos, sin descuento conocido
referencia_tarifa_plena <- Matriculas %>%
  dplyr::filter(
    !MATRICULA_SIMBOLICA,
    !SUBSIDIO_EXTERNO,
    CREDITOS_INSCRITOS >= 12,
    VAL_PAGADO > 0
  ) %>%
  mutate(val_cred_individual = VAL_PAGADO / CREDITOS_INSCRITOS)

tarifas_programa_periodo <- referencia_tarifa_plena %>%
  group_by(PROGRAMA_ACADEMICO, PERIODO) %>%
  summarise(
    TARIFA_PLENA_PROGRAMA    = median(val_cred_individual, na.rm = TRUE),
    MATRICULA_PLENA_PROGRAMA = median(VAL_PAGADO, na.rm = TRUE),
    .groups = "drop"
  )

tarifas_facultad_periodo <- referencia_tarifa_plena %>%
  group_by(FACULTAD, PERIODO) %>%
  summarise(
    TARIFA_PLENA_FACULTAD    = median(val_cred_individual, na.rm = TRUE),
    MATRICULA_PLENA_FACULTAD = median(VAL_PAGADO, na.rm = TRUE),
    .groups = "drop"
  )

Matriculas <- Matriculas %>%
  left_join(tarifas_programa_periodo, by = c("PROGRAMA_ACADEMICO", "PERIODO")) %>%
  left_join(tarifas_facultad_periodo, by = c("FACULTAD", "PERIODO")) %>%
  mutate(
    TARIFA_PLENA_CREDITO_BASE = coalesce(TARIFA_PLENA_PROGRAMA, TARIFA_PLENA_FACULTAD),
    MATRICULA_PLENA_BASE      = coalesce(MATRICULA_PLENA_PROGRAMA, MATRICULA_PLENA_FACULTAD)
  ) %>%
  select(-TARIFA_PLENA_PROGRAMA, -TARIFA_PLENA_FACULTAD,
         -MATRICULA_PLENA_PROGRAMA, -MATRICULA_PLENA_FACULTAD)

# Escenario por créditos y % de beca, igual que Proyecto_u.R,
# para comparar los tres escenarios sobre la misma base
Matriculas <- Matriculas %>%
  mutate(
    INGRESO_CF_PURO = ifelse(
      !MATRICULA_SIMBOLICA & CREDITOS_INSCRITOS > 0,
      CREDITOS_INSCRITOS * TARIFA_PLENA_CREDITO_BASE,
      0
    ),
    PCT_BECA_REAL = case_when(
      MATRICULA_SIMBOLICA | MATRICULA_PLENA_BASE == 0 ~ 0,
      VAL_PAGADO >= MATRICULA_PLENA_BASE              ~ 0,
      TRUE ~ round(1 - (VAL_PAGADO / MATRICULA_PLENA_BASE), 4)
    ),
    INGRESO_CF_NETO = INGRESO_CF_PURO * (1 - PCT_BECA_REAL)
  )

# Universo del balance: el mismo filtro de Proyecto_u.R
base_balance <- Matriculas %>%
  dplyr::filter(!MATRICULA_SIMBOLICA, CREDITOS_INSCRITOS > 0)
