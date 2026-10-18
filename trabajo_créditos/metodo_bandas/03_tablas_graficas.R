library(tidyverse)
library(scales)

# ============================================================
# 03. TABLAS, GRÁFICAS Y RESULTADOS AGREGADOS
# ============================================================
# Requiere 01 y 02. Solo escribe agregados (por escenario,
# facultad, periodo y banda), nunca filas por estudiante.

dir.create("resultados", showWarnings = FALSE)
dir.create("graficas", showWarnings = FALSE)

redondear <- function(df) mutate(df, across(where(is.double), ~ round(.x, 2)))

write_excel_csv2(redondear(balance_global_bandas),   "resultados/balance_global_bandas.csv")
write_excel_csv2(redondear(balance_facultad_bandas), "resultados/balance_facultad_bandas.csv")
write_excel_csv2(redondear(balance_periodo_bandas),  "resultados/balance_periodo_bandas.csv")
write_excel_csv2(redondear(balance_banda),           "resultados/balance_banda.csv")
write_excel_csv2(ganadores_bandas,                   "resultados/ganadores_bandas.csv")
write_excel_csv2(
  parametros_por_facultad %>% mutate(FRACCION_MATRICULA = round(FRACCION_MATRICULA, 3)),
  "resultados/bandas_por_facultad.csv"
)
write_excel_csv2(
  pago_actual_banda %>% mutate(FRACCION_ACTUAL = round(FRACCION_ACTUAL, 3)),
  "resultados/pago_actual_por_banda.csv"
)

# ------------------------------------------------------------
# Paleta y tema de la presentación
# ------------------------------------------------------------
colores_escenario <- c(
  "Cobro por créditos"  = "#C4D2E1",
  "Bandas uniformes"    = "#34506D",
  "Bandas por facultad" = "#0A1B2E"
)

tema_presentacion <- theme_minimal(base_size = 13, base_family = "Times") +
  theme(
    legend.position = "top",
    legend.text = element_text(color = "#000000", family = "Times"),
    plot.title = element_text(face = "bold", size = 14, color = "#000000", margin = margin(b = 4)),
    plot.subtitle = element_text(size = 11, color = "#000000", margin = margin(b = 10)),
    axis.text = element_text(color = "#000000"),
    axis.title = element_text(face = "bold", color = "#000000"),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.x = element_line(color = "#E1E8F0", linewidth = 0.4),
    plot.margin = margin(t = 15, r = 15, b = 10, l = 15)
  )

nombre_corto <- function(x) str_to_sentence(str_remove(x, "^CIENCIAS (DE LA |DE LAS )?"))

# ------------------------------------------------------------
# Gráfica 1: variación del ingreso por facultad
# ------------------------------------------------------------
# Las bandas por facultad no se grafican aquí: están calibradas
# para que cada facultad quede en 0 %.
variacion_facultad <- balance_facultad_bandas %>%
  dplyr::filter(Escenario == "Bandas uniformes") %>%
  transmute(FACULTAD, `Cobro por créditos` = Variacion_Pct_CF,
            `Bandas uniformes` = Variacion_Pct_Bandas) %>%
  pivot_longer(-FACULTAD, names_to = "Escenario", values_to = "Variacion") %>%
  mutate(Escenario = factor(Escenario, levels = names(colores_escenario)[1:2]))

orden_facultad <- variacion_facultad %>%
  dplyr::filter(Escenario == "Cobro por créditos") %>%
  arrange(desc(Variacion)) %>%
  pull(FACULTAD)

grafica_variacion <- variacion_facultad %>%
  mutate(FACULTAD = factor(nombre_corto(FACULTAD), levels = nombre_corto(orden_facultad))) %>%
  ggplot(aes(x = FACULTAD, y = Variacion, fill = Escenario)) +
  geom_col(position = position_dodge2(width = 0.78, reverse = TRUE), width = 0.72) +
  geom_hline(yintercept = 0, color = "#000000", linewidth = 0.6) +
  coord_flip() +
  scale_fill_manual(values = colores_escenario[1:2], name = NULL) +
  scale_y_continuous(labels = label_number(suffix = " %", accuracy = 1)) +
  labs(
    title = "Variación del ingreso por facultad según el esquema de cobro",
    subtitle = "Escenario neto frente al ingreso real, 2021-1 a 2026-1. Las bandas por facultad quedan en 0 % por diseño",
    x = NULL, y = "Variación (%)"
  ) +
  tema_presentacion

ggsave("graficas/variacion_facultad_escenarios.png", grafica_variacion,
       width = 9, height = 5.5, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Gráfica 2: fracción de la matrícula plena por banda y facultad
# ------------------------------------------------------------
fracciones <- bind_rows(
  pago_actual_banda %>% transmute(FACULTAD, BANDA, Esquema = "Pago actual (mediana)",
                                  Fraccion = FRACCION_ACTUAL),
  parametros_por_facultad %>% transmute(FACULTAD, BANDA, Esquema = "Bandas por facultad",
                                        Fraccion = FRACCION_MATRICULA)
) %>%
  dplyr::filter(BANDA %in% bandas_parciales) %>%
  mutate(
    BANDA = factor(paste(BANDA, "créditos"), levels = paste(levels(base_bandas$BANDA), "créditos")),
    Esquema = factor(Esquema, levels = c("Pago actual (mediana)", "Bandas por facultad")),
    FACULTAD = factor(nombre_corto(FACULTAD), levels = nombre_corto(orden_facultad))
  )

grafica_fracciones <- ggplot(fracciones, aes(x = FACULTAD, y = Fraccion, fill = Esquema)) +
  geom_col(position = position_dodge2(width = 0.78, reverse = TRUE), width = 0.72) +
  facet_wrap(~ BANDA) +
  coord_flip() +
  scale_fill_manual(values = c("Pago actual (mediana)" = "#C4D2E1",
                               "Bandas por facultad" = "#0A1B2E"), name = NULL) +
  scale_y_continuous(labels = label_percent(accuracy = 1), limits = c(0, 1)) +
  labs(
    title = "Cobro de la carga parcial como % de la matrícula plena",
    subtitle = "Bandas por facultad calibradas para mantener el ingreso de cada facultad",
    x = NULL, y = "% de la matrícula plena"
  ) +
  tema_presentacion +
  theme(strip.text = element_text(face = "bold", family = "Times"))

ggsave("graficas/fracciones_por_facultad.png", grafica_fracciones,
       width = 10, height = 5.5, dpi = 200, bg = "white")

# ------------------------------------------------------------
# Tablas gt (si el paquete está instalado, como en Proyecto_u.R)
# ------------------------------------------------------------
if (requireNamespace("gt", quietly = TRUE)) {
  library(gt)

  tabla_global_bandas <- balance_global_bandas %>%
    select(Escenario, Ingreso_Real_MM, Ingreso_CF_Neto_MM, Ingreso_Bandas_MM,
           Variacion_Pct_CF, Variacion_Pct_Bandas) %>%
    gt() %>%
    tab_header(
      title = "Balance global: créditos vs. bandas",
      subtitle = "Escenario neto, 2021-1 a 2026-1 (miles de millones COP)"
    ) %>%
    cols_label(
      Escenario = "", Ingreso_Real_MM = "Ingreso real",
      Ingreso_CF_Neto_MM = "Por créditos", Ingreso_Bandas_MM = "Por bandas",
      Variacion_Pct_CF = "Var. % créditos", Variacion_Pct_Bandas = "Var. % bandas"
    ) %>%
    fmt_number(columns = ends_with("_MM"), decimals = 2) %>%
    fmt_percent(columns = starts_with("Variacion"), scale_values = FALSE, decimals = 2) %>%
    opt_table_font(font = "Times new roman")

  tabla_bandas_facultad <- parametros_por_facultad %>%
    select(FACULTAD, BANDA, FRACCION_MATRICULA) %>%
    pivot_wider(names_from = BANDA, values_from = FRACCION_MATRICULA) %>%
    gt() %>%
    tab_header(
      title = "Bandas por facultad",
      subtitle = "Fracción de la matrícula plena; 19+ suma la tarifa por crédito extra"
    ) %>%
    cols_label(FACULTAD = "Facultad") %>%
    fmt_percent(columns = -FACULTAD, decimals = 0) %>%
    opt_table_font(font = "Times new roman")

  print(tabla_global_bandas)
  print(tabla_bandas_facultad)
}
