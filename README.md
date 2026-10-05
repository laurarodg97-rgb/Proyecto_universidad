# Nada sin fuente

Proyecto evaluativo de la materia **Consultoria e Investigación**, Universidad Santo Tomás. El equipo estudia los efectos de cobrar matrícula por crédito frente a una tarifa plana sobre los créditos matriculados y los resultados financieros institucionales.

**Equipo:** Juan Roa, Gabriel Aldana y Laura Rodríguez  
**Docente:** Javier Mauricio Sierra

## Entregables

Las carpetas corresponden a los cinco entregables del enunciado:

| Carpeta | Producto | Archivo principal |
|---|---|---|
| `Entregable 1/` | Inventarios individuales de fallos | Tres documentos, uno por integrante |
| `Entregable 2/` | Experimento y decisión (Semana 1) | Excel del experimento y `SEMANA 1.docx` con visto bueno recibido |
| `Entregable 3/` | Corpus, protocolo y trazabilidad | Procedencia, trazabilidad, protocolo v1/v2, pruebas y scripts de apoyo |
| `Entregable 4/` | Banco y evaluación de fidelidad | `Banco_y_evaluacion_fidelidad_v4.xlsx` y transcripción de respuestas |
| `Entregable 5/` | Memoria final | `Memoria_Nada_sin_fuente_v2.docx` |

El estado, límites y pendientes están en [ESTADO_ENTREGABLES.md](ESTADO_ENTREGABLES.md). Cada carpeta contiene su propio README.

## Corpus y datos de publicación

El equipo trabajó localmente con 10 PDF. Por precaución, Git **excluye los PDF del corpus**: el permiso de redistribución no se verificó para cada archivo. El manifiesto de `Entregable 3/corpus/incluido/README.md` identifica las fuentes y explica cómo recuperar legalmente los textos. No se deben retirar las reglas de exclusión hasta confirmar licencias o permisos.

La exclusión afecta la reproducción local de NotebookLM: para reconstruirla, cada integrante debe obtener legalmente los documentos, comprobarlos contra el manifiesto y cargar los 10 PDF, incluidos Eickhoff (2026) y Klempin (2014), en el cuaderno autorizado por el equipo.

## Reproducir los scripts de procedencia

Desde la raíz del proyecto, instalar dependencias con `python -m pip install -r requirements.txt`. Los scripts de `Entregable 3/codigo/` toman sus rutas predeterminadas relativas a esta raíz. El emparejamiento exige revisión humana antes de generar decisiones finales; no verifica ni sustituye la clasificación académica.

```powershell
python "Entregable 3/codigo/emparejar_corpus.py"
python "Entregable 3/codigo/generar_fuentes.py"
```

La primera orden muestra emparejamientos para revisión. Solo después de confirmar las decisiones documentadas, ejecutar `python "Entregable 3/codigo/emparejar_corpus.py" --confirmar`. El script de Crossref puede hacer una consulta de red y es opcional.

## Estado de cierre

El visto bueno de Semana 1 está recibido y el equipo reporta la prueba del sistema y las 20 preguntas ejecutadas. Quedan actos que requieren intervención humana: firmas individuales, revisión del equipo del caso Q19 y auditoría cruzada, que no pudo realizarse. El Entregable 5 declara esta limitación. No se presenta como completado lo que depende de firmas o de un equipo externo.
