library(tidyverse)

cols_inscripciones <- cols(
  ID_EST              = col_character(),
  ID_PROGRAMA_EST     = col_character(),
  PERIODO             = col_integer(),
  C_MAT               = col_integer(),
  NOM_MATERIA         = col_character(),
  MAT_PENSUM          = col_integer(),
  MAT_PENSUM_1        = col_character(),
  PENSUM_OFERTA       = col_character(),
  COD_UNIDAD_OFERTA   = col_integer(),
  PROGRAMA_OFERTA     = col_character(),
  FAC_OFERTA          = col_character(),
  NIVEL_MAT           = col_integer(),
  CREDITOS            = col_double(),
  VEZVISTA            = col_character()
)

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

Inscripciones <- read_delim(
  file = "inscripciones_anon.csv",
  delim = ";",
  locale = locale(decimal_mark = "."),
  col_types = cols_inscripciones,
  na = c("", "NA", "NULL"),
  trim_ws = TRUE
)

Matriculas <- read_delim(
  file = "matriculas_anon.csv",
  delim = ";",
  locale = locale(decimal_mark = "."),
  col_types = cols_matriculas,
  na = c("", "NA", "NULL"),
  trim_ws = TRUE
)



#####################################################################
Matriculas <- Matriculas %>%
  mutate(
    N_REINTEGROS_CLEAN = ifelse(N_REINTEGROS == "4+", "4", N_REINTEGROS),
    N_REINTEGROS_NUM   = coalesce(as.numeric(N_REINTEGROS_CLEAN), 0)
  ) %>%
  select(-N_REINTEGROS_CLEAN)

Matriculas <- Matriculas %>%
  group_by(ID_EST, ID_PROGRAMA_EST) %>%
  mutate(PERIODO_PRIMERA_OBSERVACION = min(PERIODO)) %>%
  ungroup()

mediana_derecho_20212 <- Matriculas %>% 
  dplyr::filter(PROGRAMA_ACADEMICO == "DERECHO", PERIODO == 20212, !is.na(VAL_PAGADO)) %>% 
  summarise(mediana = median(VAL_PAGADO)) %>% 
  pull(mediana)


Matriculas <- Matriculas %>%
  mutate(VAL_PAGADO = ifelse(is.na(VAL_PAGADO), mediana_derecho_20212, VAL_PAGADO))

# (Se eliminó aquí el cálculo de VALOR_IMPLICITO_CREDITO a nivel de
# toda la base: no se usaba en ningún cálculo posterior. El precio
# implícito por crédito que sí se usa en el análisis se calcula más
# abajo como val_cred_individual, solo dentro del grupo de
# referencia de "pagadores completos".)

referencia_tarifa_plena <- Matriculas %>%
  dplyr::filter(
    !MATRICULA_SIMBOLICA,
    !SUBSIDIO_EXTERNO,
    CREDITOS_INSCRITOS >= 12,
    VAL_PAGADO > 0
  ) %>%
  mutate(val_cred_individual = VAL_PAGADO / CREDITOS_INSCRITOS)


nrow(referencia_tarifa_plena)

###Tarifa por programa y facultad

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




library(gt)

# ============================================================
# TABLA 1: TARIFA PLENA POR FACULTAD (periodo más reciente)
# ============================================================

tabla_facultad <- tarifas_facultad_periodo %>%
  filter(PERIODO == 20261) %>%
  arrange(desc(TARIFA_PLENA_FACULTAD)) %>%
  select(FACULTAD, TARIFA_PLENA_FACULTAD, MATRICULA_PLENA_FACULTAD)

tabla_facultad %>%
  gt() %>%
  tab_header(
    title = "Tarifa plena por crédito, por facultad",
    subtitle = "Periodo 2026-1 (mediana de estudiantes sin descuento, carga completa)"
  ) %>%
  cols_label(
    FACULTAD = "Facultad",
    TARIFA_PLENA_FACULTAD = "Tarifa por crédito",
    MATRICULA_PLENA_FACULTAD = "Matrícula plena"
  ) %>%
  fmt_currency(
    columns = c(TARIFA_PLENA_FACULTAD, MATRICULA_PLENA_FACULTAD),
    currency = "COP",
    decimals = 0
  ) %>%
  opt_table_font(font = "Times new roman")


# ============================================================
# TABLA 2: TARIFA PLENA POR PROGRAMA (selección de carreras)
# ============================================================
# Se excluye ADMINISTRACIÓN DE EMPRESAS (mix shift sin resolver).
# ESTADÍSTICA incluida de forma obligatoria.

programas_seleccionados <- c(
  "ESTADÍSTICA",
  "DERECHO",
  "INGENIERÍA DE SISTEMAS",       # ajusta el nombre exacto según tu base
  "ECONOMÍA",                     # ajusta el nombre exacto según tu base
  "CONTADURÍA PÚBLICA",
  "PSICOLOGÍA"                    # ajusta el nombre exacto según tu base
)

tabla_programa <- tarifas_programa_periodo %>%
  filter(PERIODO == 20261, PROGRAMA_ACADEMICO %in% programas_seleccionados) %>%
  arrange(desc(TARIFA_PLENA_PROGRAMA)) %>%
  select(PROGRAMA_ACADEMICO, TARIFA_PLENA_PROGRAMA, MATRICULA_PLENA_PROGRAMA)

tabla_programa %>%
  gt() %>%
  tab_header(
    title = "Tarifa plena por crédito, programas seleccionados",
    subtitle = "Periodo 2026-1 (mediana de estudiantes sin descuento, carga completa)"
  ) %>%
  cols_label(
    PROGRAMA_ACADEMICO = "Programa académico",
    TARIFA_PLENA_PROGRAMA = "Tarifa por crédito",
    MATRICULA_PLENA_PROGRAMA = "Matrícula plena"
  ) %>%
  fmt_currency(
    columns = c(TARIFA_PLENA_PROGRAMA, MATRICULA_PLENA_PROGRAMA),
    currency = "COP",
    decimals = 0
  ) %>%
  opt_table_font(font = "Times new roman")







Matriculas <- Matriculas %>%
  left_join(tarifas_programa_periodo, by = c("PROGRAMA_ACADEMICO", "PERIODO")) %>%
  left_join(tarifas_facultad_periodo, by = c("FACULTAD", "PERIODO")) %>%
  mutate(
    TARIFA_PLENA_CREDITO_BASE = coalesce(TARIFA_PLENA_PROGRAMA, TARIFA_PLENA_FACULTAD),
    MATRICULA_PLENA_BASE      = coalesce(MATRICULA_PLENA_PROGRAMA, MATRICULA_PLENA_FACULTAD)
  ) %>%
  select(-TARIFA_PLENA_PROGRAMA, -TARIFA_PLENA_FACULTAD, 
         -MATRICULA_PLENA_PROGRAMA, -MATRICULA_PLENA_FACULTAD)




##si a todos los estudiantes se les cobrara la tarifa plena por crédito, sin importar 
##becas o subsidios, ¿cuánto pagarían?" Es un escenario extremo (sin ningún tipo de descuento)

Matriculas <- Matriculas %>%
  mutate(
    INGRESO_CF_PURO = ifelse(
      !MATRICULA_SIMBOLICA & CREDITOS_INSCRITOS > 0,
      CREDITOS_INSCRITOS * TARIFA_PLENA_CREDITO_BASE,
      0
    ),
    DIFERENCIA_PURO = INGRESO_CF_PURO - VAL_PAGADO,
    
    PCT_BECA_REAL = case_when(
      MATRICULA_SIMBOLICA | MATRICULA_PLENA_BASE == 0 ~ 0,
      VAL_PAGADO >= MATRICULA_PLENA_BASE              ~ 0,
      TRUE ~ round(1 - (VAL_PAGADO / MATRICULA_PLENA_BASE), 4)
    ),
    
    INGRESO_CF_NETO = INGRESO_CF_PURO * (1 - PCT_BECA_REAL),
    DIFERENCIA_NETO = INGRESO_CF_NETO - VAL_PAGADO
  )




Matriculas %>%
  dplyr::filter(!MATRICULA_SIMBOLICA, CREDITOS_INSCRITOS > 0) %>%
  summarise(
    Total_Estudiantes = n(),
    Ganancia_CF_Neto  = sum(DIFERENCIA_NETO > 0),  #¿este estudiante pagaría más en el escenario por créditos que en la realidad?
    Igual_CF_Neto     = sum(DIFERENCIA_NETO == 0),
    Perdida_CF_Neto   = sum(DIFERENCIA_NETO < 0)
  )

balance_global_corregido <- Matriculas %>%
  dplyr::filter(!MATRICULA_SIMBOLICA, CREDITOS_INSCRITOS > 0) %>%
  summarise(
    Ingreso_Real_Observado_MM = round(sum(VAL_PAGADO) / 1e9, 2),
    Ingreso_CF_Puro_MM        = round(sum(INGRESO_CF_PURO) / 1e9, 2),
    Diferencia_Puro_MM        = round(sum(DIFERENCIA_PURO) / 1e9, 2),
    Ingreso_CF_Neto_MM        = round(sum(INGRESO_CF_NETO) / 1e9, 2),
    Diferencia_Neto_MM        = round(sum(DIFERENCIA_NETO) / 1e9, 2),
    Variacion_Pct_Neto        = round((sum(DIFERENCIA_NETO) / sum(VAL_PAGADO)) * 100, 2)
  )

print(balance_global_corregido)

balance_facultad_corregido <- Matriculas %>%
  dplyr::filter(!MATRICULA_SIMBOLICA, CREDITOS_INSCRITOS > 0) %>%
  group_by(FACULTAD) %>%
  summarise(
    Estudiantes            = n(),
    Creditos_Totales       = sum(CREDITOS_INSCRITOS),
    Ingreso_Real_MM        = round(sum(VAL_PAGADO) / 1e9, 2),
    Ingreso_CF_Puro_MM     = round(sum(INGRESO_CF_PURO) / 1e9, 2),
    Ingreso_CF_Neto_MM     = round(sum(INGRESO_CF_NETO) / 1e9, 2),
    Diferencia_Neto_MM     = round(sum(DIFERENCIA_NETO) / 1e9, 2),
    Variacion_Pct_Neto     = round((sum(DIFERENCIA_NETO) / sum(VAL_PAGADO)) * 100, 2),
    .groups = "drop"
  ) %>%
  arrange(desc(abs(Diferencia_Neto_MM)))

print(balance_facultad_corregido, n = 15)

balance_periodo_corregido <- Matriculas %>%
  dplyr::filter(!MATRICULA_SIMBOLICA, CREDITOS_INSCRITOS > 0) %>%
  group_by(PERIODO) %>%
  summarise(
    Estudiantes            = n(),
    Creditos_Promedio      = round(mean(CREDITOS_INSCRITOS), 2),
    Ingreso_Real_MM        = round(sum(VAL_PAGADO) / 1e9, 2),
    Ingreso_CF_Puro_MM     = round(sum(INGRESO_CF_PURO) / 1e9, 2),
    Ingreso_CF_Neto_MM     = round(sum(INGRESO_CF_NETO) / 1e9, 2),
    Diferencia_Neto_MM     = round(sum(DIFERENCIA_NETO) / 1e9, 2),
    Variacion_Pct_Neto     = round((sum(DIFERENCIA_NETO) / sum(VAL_PAGADO)) * 100, 2),
    .groups = "drop"
  )

print(balance_periodo_corregido, n = 15)







library(gt)
library(dplyr)

# ============================================================
# TABLA 1: BALANCE GLOBAL (resumen ejecutivo — la cifra central)
# ============================================================

tabla_balance_global <- balance_global_corregido %>%
  tidyr::pivot_longer(
    cols = everything(),
    names_to = "Indicador",
    values_to = "Valor"
  ) %>%
  mutate(
    Indicador = recode(Indicador,
                       "Ingreso_Real_Observado_MM" = "Ingreso real observado",
                       "Ingreso_CF_Puro_MM"        = "Escenario puro (sin becas)",
                       "Diferencia_Puro_MM"        = "Diferencia — escenario puro",
                       "Ingreso_CF_Neto_MM"        = "Escenario neto (con becas)",
                       "Diferencia_Neto_MM"        = "Diferencia — escenario neto",
                       "Variacion_Pct_Neto"        = "Variación % (neto)"
    )
  )

tabla_balance_global %>%
  gt() %>%
  tab_header(
    title = "Balance financiero global",
    subtitle = "Comparación: esquema actual vs. cobro por créditos (2021-1 a 2026-1)"
  ) %>%
  cols_label(
    Indicador = "",
    Valor = "Valor"
  ) %>%
  fmt_number(
    rows = Indicador != "Variación % (neto)",
    columns = Valor,
    decimals = 2,
    pattern = "{x} mil millones COP"
  ) %>%
  fmt_percent(
    rows = Indicador == "Variación % (neto)",
    columns = Valor,
    scale_values = FALSE,
    decimals = 2
  ) %>%
  tab_style(
    style = list(cell_text(weight = "bold")),
    locations = cells_body(rows = Indicador %in% c("Ingreso real observado", "Escenario neto (con becas)"))
  ) %>%
  opt_table_font(font = "Times new roman")


# ============================================================
# TABLA 2: BALANCE POR FACULTAD (el resultado central del proyecto)
# ============================================================
tabla_balance_facultad <- balance_facultad_corregido %>%
  select(FACULTAD, Estudiantes, Ingreso_Real_MM, Ingreso_CF_Neto_MM,
         Diferencia_Neto_MM, Variacion_Pct_Neto) %>%
  arrange(Variacion_Pct_Neto)

tabla_balance_facultad %>%
  gt() %>%
  tab_header(
    title = md("**Impacto financiero por facultad**"),
    subtitle = "Escenario neto (con becas proporcionales) — 2021-1 a 2026-1"
  ) %>%
  cols_label(
    FACULTAD = "Facultad",
    Estudiantes = "Estudiantes",
    Ingreso_Real_MM = "Ingreso real (MM)",
    Ingreso_CF_Neto_MM = "Ingreso CF neto (MM)",
    Diferencia_Neto_MM = "Diferencia (MM)",
    Variacion_Pct_Neto = "Variación %"
  ) %>%
  fmt_number(
    columns = c(Ingreso_Real_MM, Ingreso_CF_Neto_MM, Diferencia_Neto_MM),
    decimals = 2
  ) %>%
  fmt_number(
    columns = Estudiantes,
    decimals = 0,
    use_seps = TRUE
  ) %>%
  fmt_percent(
    columns = Variacion_Pct_Neto,
    scale_values = FALSE,
    decimals = 2
  ) %>%
  # Paleta de color elegante: Rojo Burdeos -> Blanco -> Azul Storm (#34506D)
  data_color(
    columns = Variacion_Pct_Neto,
    fn = scales::col_numeric(
      palette = c("#B91C1C", "#FFFFFF", "#1E6B3C"), #
      domain = range(tabla_balance_facultad$Variacion_Pct_Neto)
    )
  ) %>%
  tab_source_note(
    source_note = "Nota: escenario neto aplica el porcentaje de beca histórico de cada estudiante sobre el cobro simulado por créditos."
  ) %>%
  opt_table_font(font = list(google_font(name = "Times New Roman"), "serif")) %>%
  # Estilo visual ejecutivo (bordes limpios y encabezado azul oscuro)
  tab_options(
    heading.align = "left",
    column_labels.background.color = "#0A1B2E", # Deep Navy de la paleta
    column_labels.font.weight = "bold",
    table.border.top.color = "#0A1B2E", #
    table.border.bottom.color = "#0A1B2E", #[cite: 1]
    table_body.hlines.color = "#E1E8F0" #[cite: 1]
  ) %>%
  tab_style(
    style = cell_text(color = "#FFFFFF", font = "Times New Roman"),
    locations = cells_column_labels()
  )







################################################################################################################
################################################################################################################

#####Verificación por qué admin baja de precio el crédito


referencia_tarifa_plena %>%
  dplyr::filter(ESTADO == "Activo") %>%
  group_by(FACULTAD, PERIODO) %>%
  summarise(
    n = n(),
    mediana_val_credito = median(val_cred_individual, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(FACULTAD, PERIODO) %>%
  print(n = Inf)
(qnorm(0.99)*0.029-0.0012)*100


referencia_tarifa_plena %>%
  dplyr::filter(FACULTAD == "CIENCIAS ECONÓMICAS Y ADMINISTRATIVAS", ESTADO == "Activo") %>%
  group_by(PROGRAMA_ACADEMICO, PERIODO) %>%
  summarise(
    n = n(),
    mediana_val_credito = median(val_cred_individual, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(PROGRAMA_ACADEMICO, PERIODO) %>%
  print(n = Inf)


#¿Hubo un cambio de pensum o de código de programa reciente?
Matriculas %>%
  dplyr::filter(PROGRAMA_ACADEMICO == "ADMINISTRACIÓN DE EMPRESAS") %>%
  count(PERIODO, COD_UNIDAD) %>%
  arrange(PERIODO)

#¿Hay más de un ID_PROGRAMA_EST o COD_UNIDAD bajo el mismo nombre "Administración de Empresas"?

Matriculas %>%
  dplyr::filter(PROGRAMA_ACADEMICO == "ADMINISTRACIÓN DE EMPRESAS") %>%
  count(PERIODO, PENSUM_ESTUDIANTE) %>%
  arrange(PERIODO)


# Precio por COD_UNIDAD a través del tiempo
referencia_tarifa_plena %>%
  dplyr::filter(PROGRAMA_ACADEMICO == "ADMINISTRACIÓN DE EMPRESAS", ESTADO == "Activo") %>%
  group_by(COD_UNIDAD, PERIODO) %>%
  summarise(
    n = n(),
    mediana_val_credito = median(val_cred_individual, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(COD_UNIDAD, PERIODO) %>%
  print(n = Inf)

# Precio por PENSUM_ESTUDIANTE a través del tiempo
referencia_tarifa_plena %>%
  dplyr::filter(PROGRAMA_ACADEMICO == "ADMINISTRACIÓN DE EMPRESAS", ESTADO == "Activo") %>%
  group_by(PENSUM_ESTUDIANTE, PERIODO) %>%
  summarise(
    n = n(),
    mediana_val_credito = median(val_cred_individual, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(PENSUM_ESTUDIANTE, PERIODO) %>%
  print(n = Inf)


#La mediana general de "Administración de Empresas" cae con el tiempo no porque nadie esté 
#pagando menos individualmente por lo mismo, sino porque la composición del programa cambió r
#adicalmente: en 2021 casi todos los estudiantes pertenecían al subprograma caro (12095/12096); 
#para 2026, casi la mitad son del subprograma nuevo y barato (86512/pensum 4), y otra parte grande 
#del otro barato (68212/pensum 3). Es un efecto de mezcla (mix shift), no de que la universidad esté 
#cobrando menos por lo mismo — es más bien que está vendiendo, cada vez más, un producto distinto
#(y más económico) bajo el mismo nombre de programa.
#Qué es probablemente 86512/pensum 4


################################################################################################################
################################################################################################################



library(ggplot2)
library(scales)

# ============================================================
# 9. GRÁFICAS PARA PRESENTACIÓN
# ============================================================

library(tidyverse)
library(scales)


ggplot(balance_facultad_corregido,
       aes(x = reorder(FACULTAD, Diferencia_Neto_MM),
           y = Diferencia_Neto_MM,
           fill = Diferencia_Neto_MM > 0)) +
  geom_col(width = 0.68) +
  geom_hline(yintercept = 0, color = "#000000", linewidth = 0.6) +
  coord_flip() +
  scale_fill_manual(
    values = c("TRUE" = "#0A1B2E", "FALSE" = "#1B3B5A"),
    labels = c("TRUE" = "Ganancia", "FALSE" = "Pérdida"),
    name = NULL
  ) +
  labs(
    # Agregamos salto de línea (\n) para que el título no se corte a la derecha
    title = "Impacto financiero por facultad:\ncobro por créditos vs. esquema actual",
    subtitle = "Diferencia neta (miles de millones de pesos)",
    x = NULL,
    y = "Diferencia (miles de millones $)"
  ) +
  theme_minimal(base_size = 13, base_family = "Times") +
  theme(
    legend.position = "top",
    legend.text = element_text(color = "#000000", family = "Times"),
    
    # Ajustamos tamaño y espacio entre líneas (lineheight)
    plot.title = element_text(
      face = "bold", 
      size = 13, 
      color = "#000000", 
      lineheight = 1.1,
      margin = margin(b = 4)
    ),
    plot.subtitle = element_text(size = 10.5, color = "#000000", margin = margin(b = 10)),
    
    axis.text.x = element_text(color = "#000000"),
    axis.text.y = element_text(color = "#000000"),
    axis.title = element_text(face = "bold", color = "#000000"),
    
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(color = "#E1E8F0", linewidth = 0.4),
    
    plot.margin = margin(t = 15, r = 15, b = 10, l = 15)
  )



################################################################################################
#Variación porcentual por facultad

ggplot(balance_facultad_corregido,
       aes(x = reorder(FACULTAD, Variacion_Pct_Neto),
           y = Variacion_Pct_Neto,
           fill = Variacion_Pct_Neto > 0)) +
  geom_col(width = 0.68) +
  geom_hline(yintercept = 0, color = "#000000", linewidth = 0.6) +
  coord_flip() +
  scale_fill_manual(
    values = c("TRUE" = "#0A1B2E", "FALSE" = "#1B3B5A"),
    labels = c("TRUE" = "Ganancia", "FALSE" = "Pérdida"),
    name = NULL
  ) +
  labs(
    title = "Variación porcentual del ingreso por facultad",
    subtitle = "% de cambio frente al ingreso real observado",
    x = NULL,
    y = "Variación (%)"
  ) +
  theme_minimal(base_size = 13, base_family = "Times") +
  theme(
    legend.position = "top",
    legend.text = element_text(color = "#000000", family = "Times"),
    plot.title = element_text(face = "bold", size = 15, color = "#000000", margin = margin(b = 4)),
    plot.subtitle = element_text(size = 11, color = "#000000", margin = margin(b = 10)),
    
    axis.text.x = element_text(color = "#000000"),
    axis.text.y = element_text(color = "#000000"),
    axis.title = element_text(face = "bold", color = "#000000"),
    
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(color = "#E1E8F0", linewidth = 0.4),
    
    plot.margin = margin(t = 15, r = 15, b = 10, l = 15)
  )



######################################################################################################

#Gráfico pastel 
library(tidyverse)
library(scales)

resumen_ganadores <- Matriculas %>%
  dplyr::filter(!MATRICULA_SIMBOLICA, CREDITOS_INSCRITOS > 0) %>%
  summarise(
    Ganancia = sum(DIFERENCIA_NETO > 0),
    Igual    = sum(DIFERENCIA_NETO == 0),
    Perdida  = sum(DIFERENCIA_NETO < 0)
  ) %>%
  pivot_longer(everything(), names_to = "Categoria", values_to = "n") %>%
  mutate(
    pct = n / sum(n),
    # Forzar el orden exacto de las categorías
    Categoria = factor(Categoria, levels = c("Ganancia", "Igual", "Perdida"))
  )

ggplot(resumen_ganadores, aes(x = "", y = n, fill = Categoria)) +
  geom_col(width = 1, color = "#FFFFFF", linewidth = 1.2) +
  coord_polar(theta = "y", start = 0) +
  geom_text(
    aes(
      label = percent(pct, accuracy = 0.1),
      color = Categoria
    ),
    position = position_stack(vjust = 0.5), 
    size = 4.5, 
    fontface = "bold",
    family = "Times"
  ) +
  # Paleta de 3 azules bien diferenciados de la imagen
  scale_fill_manual(
    values = c(
      "Ganancia" = "#0A1B2E", # Deep Navy (Muy oscuro)
      "Igual"    = "#34506D", # Storm Blue (Azul medio)
      "Perdida"  = "#C4D2E1"  # Cloud Blue (Azul claro)
    )
  ) +
  # Color del texto de cada porcentaje para máxima legibilidad
  scale_color_manual(
    values = c(
      "Ganancia" = "#FFFFFF",
      "Igual"    = "#FFFFFF",
      "Perdida"  = "#000000"
    ),
    guide = "none"
  ) +
  labs(
    title = "Estudiantes: ganancia, pérdida o igual con el cobro por créditos",
    fill = NULL
  ) +
  theme_void(base_size = 13, base_family = "Times") +
  theme(
    plot.title = element_text(
      face = "bold", 
      size = 14, 
      color = "#000000", 
      hjust = 0.5, 
      margin = margin(b = 15)
    ),
    legend.position = "right",
    legend.text = element_text(color = "#000000", size = 11, family = "Times"),
    plot.margin = margin(t = 15, r = 15, b = 10, l = 15)
  )
