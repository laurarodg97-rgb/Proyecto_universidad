# Ejecuta el método por bandas completo.
# Correr desde esta carpeta (trabajo_créditos/metodo_bandas/):
#   Rscript run_all.R
# La base va en datos/matriculas_anon.csv o en la variable RUTA_DATOS.

source("01_preparar_base.R")
source("02_cobro_bandas.R")

# Tablas, gráficas y resultados agregados
if (file.exists("03_tablas_graficas.R")) source("03_tablas_graficas.R")
