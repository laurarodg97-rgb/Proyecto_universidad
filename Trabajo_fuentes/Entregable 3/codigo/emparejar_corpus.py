"""
Nada sin fuente — emparejador de corpus.

Cruza los PDF de una carpeta contra la columna "Referencia" del Excel usando
coincidencia aproximada (primer apellido + anio), y deja el resultado en un
archivo de decisiones. Sirve para dos cosas: con --revision muestra las
coincidencias y se detiene, para que las confirme el equipo a mano; con
--confirmar genera el README, la tabla de trazabilidad y el CSV de exclusiones
usando solo el corpus real.

El script NO adivina en silencio: si un PDF empareja con varias filas o con
ninguna, lo deja marcado para revision manual.

Uso desde la raíz del proyecto:
  # fase 1: revisar emparejamientos
  python "Entregable 3/codigo/emparejar_corpus.py"

  # fase 2: generar después de revisar emparejamiento.csv
  python "Entregable 3/codigo/emparejar_corpus.py" --confirmar

Por defecto usa el Excel de Entregable 2, los PDF incluidos y la salida de Entregable 3.

Opciones:
  --solo-utilizables   ignora filas que no son "Utilizable" (default: si)
  --ocr               no se usa; el texto se lee con pypdf
"""

import argparse
import csv
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import openpyxl
from pypdf import PdfReader

import generar_fuentes as gf

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
EXCEL_PREDETERMINADO = RAIZ_PROYECTO / "Entregable 2" / "Nada_sin_fuente_plantilla_conteo3.xlsx"
PDFS_PREDETERMINADOS = RAIZ_PROYECTO / "Entregable 3" / "corpus" / "incluido"
SALIDA_PREDETERMINADA = RAIZ_PROYECTO / "Entregable 3" / "evidencia_generada"

HOJA = gf.HOJA
PDFS = {".pdf"}


# ------------------------------------------------------------------ texto pdf

def normalizar(texto):
    return gf.normalizar(texto)


def texto_pdf(ruta, paginas=1):
    """Primeras paginas del PDF: por ahi estan autor y titulo."""
    try:
        lector = PdfReader(str(ruta))
        partes = []
        for pagina in lector.pages[:paginas]:
            partes.append(pagina.extract_text() or "")
        return " ".join(partes)
    except Exception as exc:  # PDF corrupto o escaneado
        return f"[sin texto: {type(exc).__name__}]"


def apellido_del_archivo(nombre):
    """
    'Baine-Brakora_ImpactofUpperLower.pdf' -> ['baine', 'brakora', ...]
    Toma el tramo previo al primer '_' como bloque de autores.
    """
    base = Path(nombre).stem
    bloque = re.split(r"[_]+", base, maxsplit=1)[0]
    partes = re.split(r"[-.,;]+|\s+", bloque)
    return [normalizar(p) for p in partes if len(normalizar(p)) > 2]


ANIO = re.compile(r"(1[89]\d{2}|20\d{2})")


def anios_de(texto):
    return set(ANIO.findall(texto or ""))


def primer_apellido(referencia):
    """
    'Curs, B. R., & Singell, L. D. (2009). Impact of block tuition...' -> 'curs'
    Toma la primera palabra antes de la coma inicial; si la celda empieza con
    nombres estilo 'Steven W. Hemelt, ...' cae al primer apellido completo.
    """
    ref = (referencia or "").strip()
    if not ref:
        return None
    antes_del_anio = ANIO.split(ref, maxsplit=1)[0]
    # caso 'Apellido, A. B.'  -> lo que hay antes de la primera coma
    if "," in antes_del_anio:
        candidato = antes_del_anio.split(",", 1)[0]
    else:
        # caso 'Steven W. Hemelt, Kevin M. Stange' -> ultima palabra con letras
        palabras = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'-]+", antes_del_anio)
        if not palabras:
            return None
        candidato = palabras[-1]
    return normalizar(candidato)


def anio_de_referencia(referencia):
    anios = anios_de(referencia)
    return anios.pop() if len(anios) == 1 else None


def apegar(a, b):
    """similitud de cadena, sin dependencias externas."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a.startswith(b) or b.startswith(a):
        return 0.85
    comun = len(set(a) & set(b))
    return comun / max(len(a), len(b))


# ------------------------------------------------------------------- emparejar

def cargar_filas(ruta_excel):
    libro = openpyxl.load_workbook(ruta_excel, data_only=True, read_only=True)
    hoja = libro[HOJA]
    mapa, fila_encabezado = gf.detectar_encabezados(hoja)
    filas = []
    for fila in hoja.iter_rows(min_row=fila_encabezado + 1, values_only=True):
        if not any(fila):
            continue
        registro = {c: gf.texto(fila[p]) if p < len(fila) else "" for c, p in mapa.items()}
        if registro["id"]:
            registro["apellido"] = primer_apellido(registro["referencia"])
            registro["anio"] = anio_de_referencia(registro["referencia"])
            filas.append(registro)
    libro.close()
    return filas


def emparejar_pdf(ruta_pdf, filas, solo_utilizables):
    """
    Devuelve (mejor_id, puntaje, alternativas, senal).
    La senal explica por que se eligio, para que la revision sea possible.
    """
    nombre = ruta_pdf.name
    apellidos_archivo = apellido_del_archivo(nombre)
    anios_archivo = anios_de(Path(nombre).stem)

    muestra = texto_pdf(ruta_pdf)
    normalizada = normalizar(muestra)
    # el anio del PDF sirve de respaldo cuando el nombre no lo trae
    anios_pdf = anios_pdf_reales(muestra) or anios_archivo

    candidatos = []
    for f in filas:
        if solo_utilizables and normalizar(f["clasificacion"]) != gf.CLASIFICACION_OBJETIVO:
            continue
        ape = f["apellido"]
        if not ape:
            continue
        # puntaje por apellido: del nombre del archivo y del propio PDF
        mejor_ape = 0.0
        origen_ape = None
        for a in apellidos_archivo:
            s = apegar(ape, a)
            if s > mejor_ape:
                mejor_ape, origen_ape = s, "nombre de archivo"
        if ape in normalizada:
            mejor_ape, origen_ape = 1.0, "texto del PDF"
        if mejor_ape < 0.5:
            continue

        # puntaje por anio
        mejor_anio = 0.0
        origen_anio = None
        if f["anio"]:
            if f["anio"] in anios_pdf:
                mejor_anio, origen_anio = 1.0, "anio en PDF/nombre"
            elif anios_archivo and f["anio"] in anios_archivo:
                mejor_anio, origen_anio = 1.0, "anio en nombre"

        # el titulo es la senal mas fuerte cuando esta en el PDF
        titulo_texto = titulo_probable(f["referencia"])
        coincide_titulo = bool(titulo_texto) and normalizar(titulo_texto) in normalizada
        puntaje = mejor_ape * 0.5 + mejor_anio * 0.3 + (0.2 if coincide_titulo else 0.0)
        if coincide_titulo:
            puntaje = min(1.0, puntaje + 0.15)

        candidatos.append({
            "id": f["id"],
            "puntaje": round(puntaje, 3),
            "apellido": mejor_ape,
            "anio": mejor_anio,
            "titulo": coincide_titulo,
            "detalle": f"{origen_ape}, {origen_anio or 'anio no encontrado'}"
                       + (", titulo en PDF" if coincide_titulo else ""),
        })

    candidatos.sort(key=lambda c: -c["puntaje"])
    if not candidatos:
        return None, 0.0, [], "sin candidato por apellido"
    mejor = candidatos[0]
    if mejor["puntaje"] < 0.5:
        return None, mejor["puntaje"], candidatos, "puntaje insuficiente"
    if len(candidatos) > 1 and candidatos[1]["puntaje"] >= mejor["puntaje"] - 0.05:
        return mejor["id"], mejor["puntaje"], candidatos, "empate entre filas"
    return mejor["id"], mejor["puntaje"], candidatos, "ok"


def titulo_probable(referencia):
    """la parte de la referencia que viene despues del ano, sin el '(s.f.)'."""
    ref = (referencia or "").strip()
    partes = re.split(r"\(\s*(?:1[89]\d{2}|20\d{2}|s\.?f\.?)\s*\)", ref, maxsplit=1)
    if len(partes) < 2:
        return ref
    return partes[1].strip(" .,")


PALABRAS_VACIAS = {
    "a", "an", "and", "the", "of", "on", "in", "for", "to", "with", "study",
    "evidence", "effects", "effect", "analysis", "using", "case", "new",
    "una", "del", "las", "los", "por", "para", "con", "estudio",
}


def firma_titulo(referencia):
    """
    Firma de articulo: el titulo sin el autor ni el ano, en minusculas y sin
    palabras vacias. Sirve para reunir las filas del Excel que son el mismo
    documento escrito de varias formas ('Baine, N., & Brakora, K. F. (2024).'
    vs 'Nicholas Baine, Karl F. Brakora, 2024, ...').
    """
    ref = str(referencia or "").strip()
    # se descarta el bloque de autores: lo que queda tras el ano es el titulo
    corte = re.split(r"\(?\s*(?:1[89]\d{2}|20\d{2}|s\.?f\.?)\s*\)?", ref, maxsplit=1)
    titulo = corte[1] if len(corte) > 1 else ref
    # se quitan las comillas y el ruido de formato de la celda
    titulo = re.sub(r"^[\"'«“\s\.,:;-]+|[\"'»”\s\.]+$", "", titulo)
    palabras = [p for p in re.findall(r"[a-z]+", titulo.lower()) if p not in PALABRAS_VACIAS and len(p) > 3]
    return frozenset(palabras)


def es_mismo_articulo(fila_a, fila_b):
    """Dos filas son el mismo articulo si sus titulos comparten casi todo."""
    a, b = firma_titulo(fila_a["referencia"]), firma_titulo(fila_b["referencia"])
    if not a or not b:
        return False
    comun = len(a & b)
    if comun == 0:
        return False
    return comun / min(len(a), len(b)) >= 0.8


def hermanos_de(fila, filas):
    """Todas las filas Utilizables que son el mismo articulo que 'fila'."""
    return [f for f in filas
            if f["id"] != fila["id"] and es_mismo_articulo(fila, f)]


def anios_pdf_reales(muestra):
    """
    Anios que aparecen como ano de publicacion ('(c) 2019', '2019'). Se
    filtran los numeros de pagina y de volumen que tambien son de 4 digitos.
    """
    salida = set()
    for coincidencia in re.finditer(r"(1[89]\d{2}|20\d{2})", muestra or ""):
        anio = coincidencia.group(1)
        antes = (muestra[max(0, coincidencia.start() - 12):coincidencia.start()]).lower()
        if any(m in antes for m in ("vol", "no.", "n.", "pp", "p.", "isbn", "doi", "http")):
            continue
        salida.add(anio)
    return salida


# ------------------------------------------------------------------- salidas

def escribir_emparejamiento(filas_decision, ruta):
    gf.asegurar_padre(ruta)
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow([
            "Archivo PDF", "ID Excel", "Referencia", "Puntaje",
            "Estado", "Senal", "Correccion manual",
        ])
        for d in filas_decision:
            escritor.writerow([
                d["pdf"], d["id"] or "", d["referencia"], d["puntaje"],
                d["estado"], d["senal"], "",
            ])
    print(f"Escrito: {ruta}")


def leer_correcciones(ruta):
    """Lee el ID corregido a mano en la columna 'Correccion manual'."""
    correcciones = {}
    if not ruta.is_file():
        return correcciones
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            manual = (fila.get("Correccion manual") or "").strip()
            if manual:
                correcciones[fila["Archivo PDF"]] = manual
    if correcciones:
        print(f"Correcciones manuales leidas: {len(correcciones)}")
    return correcciones


# ------------------------------------------------------------------------ main

def main():
    p = argparse.ArgumentParser(description="Empareja los PDF del corpus con el Excel.")
    p.add_argument("--excel", type=Path, default=EXCEL_PREDETERMINADO)
    p.add_argument("--pdfs", type=Path, default=PDFS_PREDETERMINADOS, help="carpeta con los PDF del corpus")
    p.add_argument("--salida", type=Path, default=SALIDA_PREDETERMINADA)
    p.add_argument("--confirmar", action="store_true", help="genera los archivos finales")
    p.add_argument("--todos", action="store_true", help="empareja tambien las no Utilizables")
    p.add_argument("--crossref", action="store_true", help="verifica los DOI del corpus")
    p.add_argument("--correo", help="correo para el User-Agent de Crossref")
    args = p.parse_args()

    carpeta_pdf = args.pdfs.expanduser()
    if not carpeta_pdf.is_absolute():
        carpeta_pdf = RAIZ_PROYECTO / carpeta_pdf
    if not carpeta_pdf.is_dir():
        raise SystemExit(f"No encuentro la carpeta de PDF: {carpeta_pdf}")

    pdfs = sorted(p for p in carpeta_pdf.iterdir() if p.suffix.lower() in PDFS)
    print(f"Carpeta: {carpeta_pdf}")
    print(f"PDF encontrados: {len(pdfs)}\n")

    ruta_excel = args.excel.expanduser()
    if not ruta_excel.is_absolute():
        ruta_excel = RAIZ_PROYECTO / ruta_excel
    filas = cargar_filas(ruta_excel)
    por_id = {f["id"]: f for f in filas}
    print(f"Filas en el Excel: {len(filas)}\n")

    decisiones = []
    usados = set()
    for pdf in pdfs:
        id_mejor, puntaje, alternativas, senal = emparejar_pdf(pdf, filas, not args.todos)
        referencia = por_id.get(id_mejor, {}).get("referencia", "")
        estado = "emparejado" if id_mejor and senal == "ok" else "REVISAR"
        if id_mejor and id_mejor in usados:
            estado = "REVISAR (ID duplicado)"
            senal += f"; {id_mejor} ya asignado a otro PDF"
        decisiones.append({
            "pdf": pdf.name, "id": id_mejor, "referencia": referencia,
            "puntaje": puntaje, "estado": estado, "senal": senal,
            "alternativas": alternativas,
        })
        if id_mejor and estado == "emparejado":
            usados.add(id_mejor)

    carpeta_salida = args.salida.expanduser()
    if not carpeta_salida.is_absolute():
        carpeta_salida = RAIZ_PROYECTO / carpeta_salida
    ruta_decision = carpeta_salida / "emparejamiento.csv"
    escribir_emparejamiento(decisiones, ruta_decision)

    print("\n--- COINCIDENCIAS (revisar antes de generar) ---")
    for d in decisiones:
        marca = "ok " if d["estado"] == "emparejado" else "!! "
        print(f"{marca}{d['pdf']}")
        print(f"    -> {d['id'] or '(sin emparejar)'}  [{d['puntaje']}]  {d['senal']}")
        if d["estado"] != "emparejado":
            for alt in d["alternativas"][:3]:
                print(f"       alternativa: {alt['id']} ({alt['puntaje']}) {alt['detalle']}")
        print(f"       {d['referencia'][:90]}")

    sin_emparejar = [d for d in decisiones if d["estado"] != "emparejado"]
    print(f"\nPDF: {len(pdfs)} | emparejados: {len(decisiones) - len(sin_emparejar)} | a revisar: {len(sin_emparejar)}")

    if not args.confirmar:
        print("\nFase 1. Revisa la tabla de arriba, corrige 'ID Excel' o 'Correccion manual' en:")
        print(f"  {ruta_decision}")
        print("y despues corre de nuevo con --confirmar.")
        return 1

    correcciones = leer_correcciones(ruta_decision)
    utilizables = [f for f in filas if normalizar(f["clasificacion"]) == gf.CLASIFICACION_OBJETIVO]

    # cada PDF aporta su fila principal y las filas hermanas que son el mismo
    # articulo escrito de otra forma; asi ninguna afirmacion verificada se pierde
    corpus, mostradas = [], set()
    sin_emparejar_final = []
    for d in decisiones:
        id_final = correcciones.get(d["pdf"]) or d["id"]
        if not id_final:
            sin_emparejar_final.append(d["pdf"])
            print(f"  OJO: {d['pdf']} sigue sin emparejar; no entra al corpus")
            continue
        if id_final not in por_id:
            print(f"  OJO: {d['pdf']} apunta a un ID inexistente ({id_final}); se ignora")
            sin_emparejar_final.append(d["pdf"])
            continue

        principal = por_id[id_final]
        grupo = [principal] + hermanos_de(principal, utilizables)
        nuevos = [f for f in grupo if f["id"] not in mostradas]
        if not nuevos:
            print(f"  OJO: {d['pdf']} ya estaba cubierto por otro PDF; se omite")
            continue
        for f in grupo:
            mostradas.add(f["id"])
        d["id"] = id_final
        d["referencia"] = principal["referencia"]
        d["grupo"] = nuevos
        corpus.extend(nuevos)
        if len(nuevos) > 1:
            print(f"  {d['pdf']} -> {id_final} (+{len(nuevos) - 1} filas del mismo articulo: "
                  f"{', '.join(f['id'] for f in nuevos[1:])})")

    print(f"\nCorpus confirmado: {len(corpus)} filas de trazabilidad "
          f"en {len(decisiones) - len(sin_emparejar_final)} PDF")

    exclusiones = [f for f in utilizables if f["id"] not in mostradas]

    etiqueta = (f"corpus real: {len(decisiones) - len(sin_emparejar_final)} PDF de la "
                f"carpeta {carpeta_pdf.name} · {len(corpus)} filas de trazabilidad")
    gf.escribir_readme(corpus, carpeta_salida / "README_PROCEDENCIA.md", etiqueta)
    gf.escribir_csv(corpus, carpeta_salida / "tabla_trazabilidad.csv")

    ruta_excl = carpeta_salida / "excluidas_del_corpus.csv"
    gf.asegurar_padre(ruta_excl)
    with ruta_excl.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow([
            "ID", "Referencia", "DOI o URL", "Clasificacion final",
            "Motivo de exclusion", "Verificado por", "Fecha",
        ])
        for fila in exclusiones:
            escritor.writerow([
                fila["id"], fila["referencia"], fila["doi_url"],
                fila["clasificacion"], "", fila["verificado"], fila["fecha"],
            ])
    print(f"Escrito: {ruta_excl}  ({len(exclusiones)} excluidas)")

    if args.crossref:
        print("\nVerificando DOIs en Crossref (solo el corpus)...")
        resultados = gf.verificar_crossref(corpus, args.correo)
        resueltos = sum(1 for v in resultados.values() if v == "Si")
        sin_doi = sum(1 for v in resultados.values() if v == gf.SIN_DOI)
        print(f"Resolvieron: {resueltos}/{len(resultados)} DOIs"
              + (f" | {sin_doi} sin DOI (solo URL)" if sin_doi else ""))
        gf.escribir_excel_filtrado(
            ruta_excel, corpus, resultados,
            carpeta_salida / "referencias_con_crossref.xlsx",
        )

    if sin_emparejar_final:
        print("\nPDF en la carpeta sin fila en el Excel (no entran al corpus):")
        for nombre in sin_emparejar_final:
            print(f"  - {nombre}")

    print(f"\nResumen: {len(pdfs)} PDF | {len(decisiones) - len(sin_emparejar_final)} emparejados "
          f"| {len(sin_emparejar_final)} sin emparejar | "
          f"{len(corpus)} filas en el corpus | {len(exclusiones)} excluidas de {len(utilizables)} Utilizables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
