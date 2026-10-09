# Entregable 3 — El sistema de fuentes

## Corpus y NotebookLM

El corpus local final contiene diez documentos académicos. Ocho PDF sostienen las once filas históricas de trazabilidad del experimento. Eickhoff (2026) y Klempin (2014) se incorporaron después como fuentes complementarias con aval docente reportado por el equipo; no se suman retroactivamente a las referencias ni a los conteos de Semana 1. El equipo confirmó que NotebookLM está actualizado con los diez documentos y que se ejecutó allí el banco de preguntas del Entregable 4.

- `corpus/incluido/`: diez documentos consultables.
- `codigo/`: scripts de emparejamiento y generación de artefactos de procedencia y trazabilidad.
- `evidencia_generada/`: artefactos derivados de las once filas históricas y registro separado de fuentes adicionales.
- `protocolo/`: versiones del protocolo de consulta.
- `pruebas/`: diseño y evidencia de la prueba piloto de NotebookLM.

## Verificación de Eickhoff para el anteproyecto

El 2026-10-02, Juan Roa detectó que el anteproyecto citaba Eickhoff sin una fila de verificación formal. El PDF sí respalda el coeficiente de +0,462 créditos por periodo en la regresión (PDF p. 90; página impresa 77; p < 0,001). La discusión presupuestal informa +3,25 % a partir de un incremento medio de 0,43 créditos (PDF p. 108; página impresa 95). Ambas cifras aparecen, pero el porcentaje no se calcula directamente del coeficiente +0,462.

El documento usa “equitable lift” para indicar que las brechas de créditos entre grupos no se ampliaron; las brechas persisten y no se afirma que cada grupo recibiera exactamente el mismo aumento. También explica el subsidio cruzado y el mayor costo por crédito para estudiantes cercanos a la parte baja del plateau (PDF pp. 18 y 56; páginas impresas 5 y 43). Se registraron verificador, fecha y localizadores en `evidencia_generada/fuentes_adicionales_corpus.csv`. Eickhoff permanece separado de las once filas experimentales.

## Procedencia, versiones bibliográficas y límites

La tabla `tabla_trazabilidad.csv` conserva solo las once filas ligadas al experimento; no debe inflarse con fuentes añadidas después. La ficha `fuentes_adicionales_corpus.csv` documenta Eickhoff y Klempin aparte. El sistema contiene el estudio de Baine y Brakora sobre tarifas upper/lower division, pero no el artículo “Disparate Impacts of Block Tuition”.

La discrepancia de metadatos se resolvió identificando la versión del archivo local, sin reescribir los registros históricos de Semana 1: (1) `HemeltStangeMarginalPricing2016.pdf` es la versión de revista de 2016 (DOI 10.1002/pam.21891), no el working paper de 2014; (2) el PDF de *Resetting Prices* lista a James Dean Ward y Daniel Corral: “Dean” es segundo nombre; la publicación en línea fue en 2022 y el volumen es de 2023; (3) `KevinStange_DifferencialPricing2013.pdf` es NBER WP 19183 (2013), mientras que la versión de revista de 2015 tiene DOI 10.1002/pam.21803; (4) `MarcB-JanM_EffectOfTuitionFees2025.pdf` es un manuscrito/discussion paper de 2025 y no debe citarse como si fuera el PDF de la versión de revista de 2026. Fuentes de contraste: [Wiley, Hemelt–Stange](https://onlinelibrary.wiley.com/doi/10.1002/pam.21891), [Springer, Ward–Corral](https://link.springer.com/article/10.1007/s11162-022-09723-6), [NBER, Stange WP 19183](https://www.nber.org/papers/w19183), [Wiley, Stange 2015](https://onlinelibrary.wiley.com/doi/10.1002/pam.21803).

El manifiesto [`corpus/incluido/README.md`](corpus/incluido/README.md) identifica los diez archivos locales, la versión usada, el registro de obtención/verificación y el estado de los permisos. Los PDF se excluyen de Git hasta confirmar el permiso de redistribución para cada copia; un clon debe volver a obtenerlos de las fuentes editoriales/institucionales autorizadas. No se afirma una licencia cuando no fue comprobada.

El acta de datos de contraparte no aplica al corpus actual: el equipo no reporta documentos no públicos entregados por una contraparte. Si esto cambia, registrar origen, uso, acceso y tratamiento en el acta antes de incorporarlos a un servicio en la nube.
