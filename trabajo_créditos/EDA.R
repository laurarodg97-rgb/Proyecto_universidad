library(tidyverse)
library(scales)
library(gt)

# ============================================================
# 1. CARGA DE DATOS
# ============================================================

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

Matriculas <- readxl::read_excel("matriculas_anon.xlsx", col_types = "text") %>%
  mutate(
    PERIODO             = as.integer(PERIODO),
    NIVEL_EST           = as.integer(NIVEL_EST),
    ES_NUEVO            = as.logical(ES_NUEVO),
    SUBSIDIO_EXTERNO    = as.logical(SUBSIDIO_EXTERNO),
    REINTEGRO           = as.logical(REINTEGRO),
    VAL_PAGADO          = as.numeric(VAL_PAGADO),
    MATRICULA_SIMBOLICA = as.logical(MATRICULA_SIMBOLICA),
    CREDITOS_INSCRITOS  = as.numeric(CREDITOS_INSCRITOS),
    N_MATERIAS          = as.integer(N_MATERIAS),
    N_MATERIAS_REPITE   = as.integer(N_MATERIAS_REPITE)
  )


# ============================================================
# 2. TABLA 1 — FICHA GENERAL DE LA BASE
# ============================================================

ficha_general <- tibble(
  Indicador = c(
    "Registros (estudiante-periodo)",
    "Estudiantes únicos",
    "Programas académicos",
    "Facultades",
    "Periodos analizados",
    "Rango de periodos"
  ),
  Valor = c(
    format(nrow(Matriculas), big.mark = ","),
    format(n_distinct(Matriculas$ID_EST), big.mark = ","),
    format(n_distinct(Matriculas$PROGRAMA_ACADEMICO), big.mark = ","),
    format(n_distinct(Matriculas$FACULTAD), big.mark = ","),
    format(n_distinct(Matriculas$PERIODO), big.mark = ","),
    paste(min(Matriculas$PERIODO), "-", max(Matriculas$PERIODO))
  )
)

ficha_general %>%
  gt() %>%
  tab_header(title = "Ficha general de la base de matrículas") %>%
  cols_label(Indicador = "", Valor = "") %>%
  opt_table_font(font = "Arial")



# ============================================================
# 4. GRÁFICA — DISTRIBUCIÓN DE ESTUDIANTES POR FACULTAD
# ============================================================

Matriculas %>%
  count(FACULTAD) %>%
  mutate(pct = n / sum(n)) %>%
  ggplot(aes(x = reorder(FACULTAD, pct), y = pct)) +
  geom_col(fill = "#1B3B5A", width = 0.68) +
  geom_text(
    aes(label = percent(pct, accuracy = 0.1)),
    hjust = -0.15,
    size = 3.8,
    fontface = "bold",
    family = "Times",
    color = "#000000"
  ) +
  coord_flip() +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.18)),
    labels = percent
  ) +
  labs(
    title = "Registros por facultad (2021-1 a 2026-1)",
    x = NULL,
    y = "% de estudiantes-periodo"
  ) +
  theme_minimal(base_size = 13, base_family = "Times") +
  theme(
    plot.title = element_text(face = "bold", size = 16, color = "#000000", margin = margin(b = 10)),
    axis.text.x = element_text(color = "#000000"),
    axis.text.y = element_text(color = "#000000"),
    axis.title = element_text(face = "bold", color = "#000000"),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(color = "#E1E8F0", linewidth = 0.4),
    plot.margin = margin(t = 15, r = 15, b = 10, l = 15)
  )


# ============================================================
# 6. GRÁFICA — CRÉDITOS INSCRITOS: DISTRIBUCIÓN Y PROMEDIO POR PERIODO
# ============================================================

library(tidyverse)

Matriculas %>%
  filter(CREDITOS_INSCRITOS > 0) %>%
  group_by(PERIODO) %>%
  summarise(Creditos_Promedio = mean(CREDITOS_INSCRITOS)) %>%
  ggplot(aes(x = factor(PERIODO), y = Creditos_Promedio, group = 1)) +
  # Usamos Ocean Depth (#1B3B5A) de la paleta
  geom_line(color = "#1B3B5A", linewidth = 1) +
  geom_point(color = "#1B3B5A", size = 2.5) +
  
  # Umbral de tiempo completo y anotación en negro
  geom_hline(yintercept = 12, linetype = "dashed", color = "#000000", linewidth = 0.5) +
  annotate(
    "text", x = 1, y = 12.4, 
    label = "Umbral tiempo completo (12)",
    hjust = 0, size = 3.5, color = "#000000", family = "Times"
  ) +
  labs(
    title = "Créditos promedio matriculados por periodo",
    x = "Periodo", 
    y = "Créditos promedio"
  ) +
  theme_minimal(base_size = 13, base_family = "Times") +
  theme(
    # Título en negro
    plot.title = element_text(face = "bold", size = 16, color = "#000000", margin = margin(b = 10)),
    
    # Ejes en negro
    axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1, color = "#000000"),
    axis.text.y = element_text(color = "#000000"),
    axis.title = element_text(face = "bold", color = "#000000"),
    
    # Grilla limpia
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(color = "#E1E8F0", linewidth = 0.4), #[cite: 1]
    
    plot.margin = margin(t = 15, r = 15, b = 10, l = 15)
  )

# 7. TABLA 2 — RESUMEN DE VARIABLES CLAVE POR FACULTAD
# ============================================================

resumen_facultad <- Matriculas %>%
  filter(!MATRICULA_SIMBOLICA, VAL_PAGADO > 0) %>%
  group_by(FACULTAD) %>%
  summarise(
    Estudiantes        = n(),
    Creditos_Promedio  = round(mean(CREDITOS_INSCRITOS, na.rm = TRUE), 1),
    Pago_Mediana       = round(median(VAL_PAGADO, na.rm = TRUE), 0),
    Pct_Subsidio       = round(mean(SUBSIDIO_EXTERNO, na.rm = TRUE) * 100, 1),
    .groups = "drop"
  ) %>%
  arrange(desc(Estudiantes))

resumen_facultad %>%
  gt() %>%
  tab_header(title = "Resumen por facultad") %>%
  cols_label(
    FACULTAD          = "Facultad",
    Estudiantes        = "Estudiantes",
    Creditos_Promedio  = "Créditos prom.",
    Pago_Mediana       = "Pago mediana (COP)",
    Pct_Subsidio       = "% con subsidio"
  ) %>%
  fmt_number(columns = Estudiantes, decimals = 0, use_seps = TRUE) %>%
  fmt_currency(columns = Pago_Mediana, currency = "COP", decimals = 0) %>%
  fmt_percent(columns = Pct_Subsidio, scale_values = FALSE, decimals = 1) %>%
  opt_table_font(font = "Times new roman")
