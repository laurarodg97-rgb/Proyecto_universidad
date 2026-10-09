# Estado final de los entregables

Actualizado: 2026-10-02. El estado se basa en los archivos de esta carpeta y en lo que reportó el equipo. No se atribuyen firmas, revisiones externas ni ejecuciones que no estén documentadas.

## Semana 1

| Requisito | Estado | Evidencia / límite |
|---|---|---|
| Experimento con tres consultas y tres tratamientos | Completo | Excel maestro en `Entregable 2/Nada_sin_fuente_plantilla_conteo3.xlsx` |
| Conteos finales | A: 4/15 (26,7 %); B: 11/15 (73,3 %); C: 7/7 (100 %) | Excel conserva clasificaciones, desacuerdos y dos correcciones de citas |
| Selección de herramienta y seis criterios | Completo | Excel de Semana 1; se eligió NotebookLM |
| Visto bueno docente | Recibido | `Entregable 2/SEMANA 1.docx` |
| Inventario individual, mínimo tres fallos | Preparado | Un DOCX para Juan, Gabriel y Laura en `Entregable 1/`; las firmas las debe poner cada integrante |

## Semana 2

| Requisito | Estado | Evidencia / límite |
|---|---|---|
| Corpus final | 10 PDF usados localmente | 8 sostienen 11 filas históricas del experimento; Eickhoff (2026) y Klempin (2014) se agregaron luego con aval docente reportado por el equipo |
| Metadatos, trazabilidad y verificación adicional | Registrados | `Entregable 3/evidencia_generada/`; los dos documentos adicionales se mantienen separados de las 11 filas de Semana 1 |
| Versiones bibliográficas | Aclaradas para los cuatro casos detectados | Ver README de Entregable 3 y manifiesto del corpus; se conservaron las citas históricas del experimento |
| Protocolo de consulta | v1 preservado y v2 vigente | `Entregable 3/protocolo/` |
| Sistema NotebookLM | Preparado y probado por el equipo | 10 documentos cargados según informa el equipo; el cuaderno no se incluye en Git |
| Prueba piloto de funcionamiento | Exitosa según el equipo | Evidencia en `Entregable 3/pruebas/` |
| Acta de datos de contraparte | No aplica al corpus reportado | No se reportan documentos no públicos suministrados por contraparte; si esto cambia, debe completarse antes de cargar/publicar esos datos |

## Semana 3

| Requisito | Estado | Evidencia / límite |
|---|---|---|
| Banco de preguntas | 20 preguntas y salidas registradas | `Entregable 4/Banco_y_evaluacion_fidelidad_v4.xlsx` más la transcripción de NotebookLM |
| Preguntas sin respuesta completa esperada | Q16, Q19 y Q20 | Q16 requiere abstención parcial; Q19–Q20 requieren no inventar dato no medido |
| Citas y páginas | Evaluadas en el libro | El equipo reporta que abrió una cita por cada uno de los 10 PDF; no existe una captura independiente para cada corrida |
| Caso de fallo | Q19, observado una vez | El sistema contestó “$0” como cifra anual y no se abstuvo; se registró que la fuente no informa ingresos brutos anuales. No se afirma que el fallo se haya reproducido |
| Auditoría cruzada con otro equipo | No realizada | El equipo informa que no fue posible coordinarla; el formato sigue disponible y la memoria declara la limitación |
| Memoria de 2–4 páginas y seis apartados | Redactada | `Entregable 5/Memoria_Nada_sin_fuente_v2.docx`; declara la auditoría no realizada y el caso Q19 |
| Declaración de uso de IA | Incluida en la memoria | Identifica Consensus, Gemini, NotebookLM, OpenCode y ChatGPT/Codex, su función y correcciones humanas. Las versiones exactas no se registraron |

## Preparación para Git

- `.gitignore` excluye los 10 PDF hasta confirmar permiso de redistribución, cachés, archivos de construcción, versiones intermedias y salidas de inspección. El manifiesto mantiene rastreables las fuentes sin publicar los archivos fuente.
- El corpus seguirá disponible localmente en la carpeta de trabajo; un clon necesita obtener cada PDF desde un origen autorizado y reconstruir NotebookLM.
- Los únicos pendientes del equipo antes de declarar cierre completo son: (1) las tres firmas de los inventarios; (2) revisión/firma interna del registro de Q19; (3) auditoría cruzada, solo si se logra coordinar otro equipo. La auditoría no se sustituye por una afirmación ficticia.
- La tabla de evaluación del enunciado limita el nivel de C3 para un servicio administrado como NotebookLM y fija un techo global asociado; la nota final también depende de la sustentación individual.
- La memoria se revisó estructuralmente, pero no se logró la inspección visual final: el renderizador no encuentra LibreOffice (`soffice.exe`) en este entorno.
