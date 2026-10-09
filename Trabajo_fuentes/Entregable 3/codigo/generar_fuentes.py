"""
Nada sin fuente — generador de procedencia y trazabilidad.

Lee el Excel del experimento y produce, en una carpeta de salida:
  1. README_PROCEDENCIA.md    -> una seccion por referencia "Utilizable"
  2. tabla_trazabilidad.csv   -> Afirmacion, Fuente, Ubicacion, Verificado por, Fecha
  3. referencias_con_crossref.xlsx -> copia del Excel con "DOI verificado (Crossref)"

Nunca modifica el Excel original ni los PDF.

Uso desde la raíz del proyecto:
  python "Entregable 3/codigo/generar_fuentes.py"
  python "Entregable 3/codigo/generar_fuentes.py" --crossref --correo a@b.com

Por defecto lee el Excel de Entregable 2 y escribe en Entregable 3/evidencia_generada.
"""

import argparse
import csv
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import openpyxl

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
EXCEL_PREDETERMINADO = RAIZ_PROYECTO / "Entregable 2" / "Nada_sin_fuente_plantilla_conteo3.xlsx"
SALIDA_PREDETERMINADA = RAIZ_PROYECTO / "Entregable 3" / "evidencia_generada"

# ---------------------------------------------------------------- configuracion

HOJA = "Referencias"
CLASIFICACION_OBJETIVO = "utilizable"

# Palabras clave para ubicar cada columna sin depender del texto exacto.
COLUMNAS = {
    "id": ("id",),
    "referencia": ("referencia",),
    "doi_url": ("doi o url", "doi/url", "doi"),
    "afirmacion": ("afirmacion",),
    "clasificacion": ("clasificacion final",),
    "ubicacion": ("ubicacion",),
    "verificado": ("verificado por",),
    "fecha": ("fecha",),
}

NO_DISPONIBLE = "no verificado"
SIN_DOI = "no aplica (URL o sin DOI)"
NO_CORRESPONDE = "No"


# ---------------------------------------------------------------------- utileria

def normalizar(texto):
    """minusculas, sin acentos y sin signos: para comparar encabezados."""
    if texto is None:
        return ""
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", sin_acentos.lower()).strip()


def texto(valor):
    """celda -> string limpio; los espacios que se cuelan en la hoja se van."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return re.sub(r"\s+", " ", str(valor)).strip()


def escapar_markdown(valor):
    """los corchetes rompen los enlaces de Markdown dentro de una seccion."""
    return valor.replace("[", "(").replace("]", ")")


def asegurar_padre(ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------- lectura xlsx

def detectar_encabezados(hoja):
    """Devuelve {clave: indice de columna} locating la fila de encabezados."""
    for indice, fila in enumerate(hoja.iter_rows(min_row=1, max_row=hoja.max_row, values_only=True), 1):
        normalizados = [normalizar(c) for c in fila]
        if "id" in normalizados and "clasificacion final" in normalizados:
            mapa = {}
            for clave, alias in COLUMNAS.items():
                # el alias mas largo gana: "doi o url" antes que "doi",
                # para no confundirse con la columna "doi url resuelve".
                candidatos = [
                    (len(a), posicion)
                    for a in alias
                    for posicion, nombre in enumerate(normalizados)
                    if nombre == a or nombre.startswith(a + " ")
                ]
                if candidatos:
                    mapa[clave] = sorted(candidatos, key=lambda t: (-t[0], t[1]))[0][1]
            faltan = [c for c in ("referencia", "clasificacion", "ubicacion", "verificado", "fecha")
                      if c not in mapa]
            if faltan:
                raise SystemExit(
                    f"No encontre las columnas {faltan} en '{HOJA}'. "
                    f"Encabezados leidos: {normalizados}"
                )
            return mapa, indice
    raise SystemExit(f"No encontre la fila de encabezados en la hoja '{HOJA}'.")


def leer_filas(ruta_excel):
    libro = openpyxl.load_workbook(ruta_excel, data_only=True, read_only=True)
    if HOJA not in libro.sheetnames:
        raise SystemExit(
            f"La hoja '{HOJA}' no existe. Hojas disponibles: {libro.sheetnames}"
        )
    hoja = libro[HOJA]
    mapa, fila_encabezado = detectar_encabezados(hoja)
    print(f"Hoja '{HOJA}' · encabezados en la fila {fila_encabezado}")

    filas = []
    sin_id = 0
    for indice, fila in enumerate(hoja.iter_rows(min_row=fila_encabezado + 1, values_only=True), fila_encabezado + 1):
        if not any(fila):
            continue
        registro = {
            clave: texto(fila[pos]) if pos < len(fila) else ""
            for clave, pos in mapa.items()
        }
        if not registro["id"]:
            sin_id += 1
            continue
        filas.append(registro)

    libro.close()
    print(f"Referencias leidas: {len(filas)}" + (f" ({sin_id} filas sin ID, ignoradas)" if sin_id else ""))
    return filas


def seleccionar_utilizables(filas):
    seleccion = [f for f in filas if normalizar(f["clasificacion"]) == CLASIFICACION_OBJETIVO]
    vacias = [f for f in seleccion if not f["fecha"] or not f["verificado"] or not f["ubicacion"]]
    print(f"Clasificacion 'Utilizable': {len(seleccion)}")
    if vacias:
        print(f"Aviso: {len(vacias)} utilizables sin Fecha, Verificado por o Ubicacion -> se marcan como pendientes")
        for f in vacias:
            print(f"  - {f['id']}")
    return seleccion


# ----------------------------------------------------------------- 1. readme .md

def escribir_readme(seleccion, ruta_salida, verificacion):
    lineas = [
        "# README de procedencia",
        "",
        "Una seccion por referencia clasificada como **Utilizable** en el experimento.",
        "El documento original no se modifica: este archivo solo responde de donde sale cada referencia.",
        "",
        f"- Generado: {date.today().isoformat()}",
        f"- Referencias incluidas: {len(seleccion)}",
        f"- Verificacion de DOI: {verificacion}",
        "",
    ]
    for f in seleccion:
        # si la celda trae una URL de busqueda con el DOI embebido, se deja
        # el DOI canonico: es lo que un lector puede abrir y comprobar.
        doi = extraer_doi(f["doi_url"])
        origen = f"https://doi.org/{doi}" if doi else (f["doi_url"] or NO_DISPONIBLE)
        lineas += [
            f"## {escapar_markdown(f['referencia'])}",
            f"- ID: {escapar_markdown(f['id'])}",
            f"- Origen: {escapar_markdown(origen)}",            f"- Fecha de obtencion: {escapar_markdown(f['fecha']) or NO_DISPONIBLE}",
            f"- Verificado por: {escapar_markdown(f['verificado']) or NO_DISPONIBLE}",
            f"- Ubicacion de la afirmacion: {escapar_markdown(f['ubicacion']) or NO_DISPONIBLE}",
            "",
        ]
    asegurar_padre(ruta_salida)
    ruta_salida.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Escrito: {ruta_salida}")


# ------------------------------------------------------------------- 2. csv

def escribir_csv(seleccion, ruta_salida):
    asegurar_padre(ruta_salida)
    with ruta_salida.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["Afirmacion", "Fuente", "Ubicacion", "Verificado por", "Fecha"])
        for fila in seleccion:
            escritor.writerow([
                fila["afirmacion"] or NO_DISPONIBLE,
                fila["referencia"] or fila["id"],
                fila["ubicacion"] or NO_DISPONIBLE,
                fila["verificado"] or NO_DISPONIBLE,
                fila["fecha"] or NO_DISPONIBLE,
            ])
    print(f"Escrito: {ruta_salida}")


# --------------------------------------------------------------- 3. crossref

def extraer_doi(valor):
    """saca el DOI de un campo que puede venir solo o embebido en una URL."""
    if not valor:
        return None
    candidato = None
    if "doi.org/" in valor.lower():
        # puede venir envuelto en una URL de busqueda, con parametros al final
        candidato = valor.lower().split("doi.org/", 1)[1].split()[0]
    elif re.search(r"10\.\d{4,9}/\S+", valor):
        candidato = re.search(r"10\.\d{4,9}/\S+", valor).group(0)
    if candidato is None:
        return None
    # "?utm_source=..." o "&utm_source=..." no son parte del DOI
    candidato = re.split(r"[?&]", candidato)[0]
    candidato = candidato.rstrip("/.,;")
    return candidato if re.fullmatch(r"10\.\d{4,9}/\S+", candidato) else None


def verificar_crossref(filas, correo=None, espera=0.4, intentos=3):
    """Consulta api.crossref.org por DOI. Devuelve {id: 'Si'|'No'|'...'}."""
    import requests

    if correo:
        sesion = requests.Session()
        sesion.headers.update({
            "User-Agent": f"NadaSinFuente/1.0 (correo: {correo})",
            "Referer": f"mailto:{correo}",
        })
    else:
        sesion = requests.Session()
        sesion.headers["User-Agent"] = "NadaSinFuente/1.0 (proyecto universitario)"

    resultados = {}
    pendientes = {f["id"]: extraer_doi(f["doi_url"]) for f in filas}
    import time
    for identificador, doi in pendientes.items():
        if not doi:
            resultados[identificador] = SIN_DOI
            continue
        estado = NO_CORRESPONDE
        for intento in range(intentos):
            try:
                r = sesion.get(f"https://api.crossref.org/works/{doi}", timeout=20)
                if r.status_code == 200:
                    estado = "Si"
                    break
                if r.status_code == 404:
                    estado = NO_CORRESPONDE
                    break
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** intento + 1)
                    continue
                estado = f"No (HTTP {r.status_code})"
                break
            except requests.RequestException as exc:
                if intento == intentos - 1:
                    estado = f"No (error de red: {type(exc).__name__})"
                else:
                    time.sleep(2 ** intento + 1)
        resultados[identificador] = estado
        print(f"  {identificador:<10} {doi:<45} {estado}")
        time.sleep(espera)
    return resultados


def escribir_excel_copia(ruta_excel, resultados, ruta_salida):
    """Copia el libro y anade la columna, sin tocar el archivo original."""
    import shutil

    asegurar_padre(ruta_salida)
    shutil.copyfile(ruta_excel, ruta_salida)
    libro = openpyxl.load_workbook(ruta_salida)
    hoja = libro[HOJA]
    mapa, fila_encabezado = detectar_encabezados(hoja)

    columna = hoja.max_column + 1
    hoja.cell(row=fila_encabezado, column=columna, value="DOI verificado (Crossref)")

    for indice in range(fila_encabezado + 1, hoja.max_row + 1):
        id_fila = texto(hoja.cell(row=indice, column=mapa["id"] + 1).value)
        if not id_fila:
            continue
        clasificacion = normalizar(texto(hoja.cell(row=indice, column=mapa["clasificacion"] + 1).value))
        if clasificacion != CLASIFICACION_OBJETIVO:
            continue
        hoja.cell(row=indice, column=columna, value=resultados.get(id_fila, NO_DISPONIBLE))

    libro.save(ruta_salida)
    print(f"Escrito: {ruta_salida}  (copia; el Excel original quedo intacto)")


# ------------------------------------------------------------------------- main

def escribir_excel_filtrado(ruta_excel, filas, resultados, ruta_salida):
    """
    Libro nuevo con SOLO las filas dadas (el corpus), mas la columna de
    Crossref. Se construye de cero en vez de borrar filas de una copia a
    proposito: la hoja 'Conteo' usa COUNTIFS sobre Referencias!$B$6:$B$50, y
    al filtrar esas referencias apuntarian a otras filas y darian conteos
    equivocados sin avisar. Aqui se copian valores ya calculados, no formulas.
    """
    import openpyxl as ox

    origen_valores = ox.load_workbook(ruta_excel, data_only=True)
    origen_formulas = ox.load_workbook(ruta_excel, data_only=False)
    if HOJA not in origen_valores.sheetnames:
        raise SystemExit(f"La hoja '{HOJA}' no existe en {ruta_excel}")

    hoja_valores = origen_valores[HOJA]
    hoja_formulas = origen_formulas[HOJA]
    mapa, fila_encabezado = detectar_encabezados(hoja_valores)

    destinos = []
    libro = ox.Workbook()
    salida = libro.active
    salida.title = HOJA

    encabezados = [hoja_valores.cell(row=fila_encabezado, column=c).value
                   for c in range(1, hoja_valores.max_column + 1)]
    encabezados.append("DOI verificado (Crossref)")
    salida.append(encabezados)

    for fila in filas:
        indice = indice_fila_de_id(hoja_valores, mapa["id"], fila["id"], fila_encabezado)
        valores = []
        for c in range(1, hoja_valores.max_column + 1):
            celda = hoja_valores.cell(row=indice, column=c)
            if isinstance(celda.value, str) and celda.value.startswith("="):
                celda = hoja_formulas.cell(row=indice, column=c)
            valores.append(celda.value)
        valores.append(resultados.get(fila["id"], NO_DISPONIBLE))
        salida.append(valores)
        destinos.append(fila["id"])

    asegurar_padre(ruta_salida)
    libro.save(ruta_salida)
    origen_valores.close()
    origen_formulas.close()
    print(f"Escrito: {ruta_salida}  ({len(destinos)} filas del corpus; "
          f"el Excel original quedo intacto)")
    return destinos


def indice_fila_de_id(hoja, columna_id, id_buscado, fila_encabezado):
    for indice in range(fila_encabezado + 1, hoja.max_row + 1):
        if texto(hoja.cell(row=indice, column=columna_id + 1).value) == id_buscado:
            return indice
    raise SystemExit(f"No encontre el ID {id_buscado} en la hoja '{HOJA}'")


def main():
    analizador = argparse.ArgumentParser(description="Nada sin fuente: procedencia y trazabilidad.")
    analizador.add_argument("--excel", type=Path, default=EXCEL_PREDETERMINADO, help="ruta del .xlsx del experimento")
    analizador.add_argument("--salida", type=Path, default=SALIDA_PREDETERMINADA, help="carpeta de salida")
    analizador.add_argument("--crossref", action="store_true", help="verificar DOIs contra Crossref")
    analizador.add_argument("--correo", help="correo para el User-Agent de Crossref (recomendado)")
    args = analizador.parse_args()

    ruta_excel = args.excel.expanduser()
    if not ruta_excel.is_absolute():
        ruta_excel = RAIZ_PROYECTO / ruta_excel
    if not ruta_excel.is_file():
        raise SystemExit(f"No encuentro el Excel: {ruta_excel}")

    carpeta = args.salida.expanduser()
    if not carpeta.is_absolute():
        carpeta = RAIZ_PROYECTO / carpeta
    asegurar_padre(carpeta)
    print(f"Excel: {ruta_excel}\nSalida: {carpeta}\n")

    filas = leer_filas(ruta_excel)
    seleccion = seleccionar_utilizables(filas)

    resultados = {}
    if args.crossref:
        print("\nVerificando DOIs en Crossref...")
        resultados = verificar_crossref(seleccion, args.correo)
        resueltos = sum(1 for v in resultados.values() if v == "Si")
        print(f"Resolvieron: {resueltos}/{len(resultados)}")
    etiqueta = "Si/No por DOI (Crossref)" if args.crossref else "no solicitada en esta corrida"

    escribir_readme(seleccion, carpeta / "README_PROCEDENCIA.md", etiqueta)
    escribir_csv(seleccion, carpeta / "tabla_trazabilidad.csv")
    if args.crossref:
        escribir_excel_copia(ruta_excel, resultados, carpeta / "referencias_con_crossref.xlsx")

    print("\nListo.")


if __name__ == "__main__":
    sys.exit(main())
