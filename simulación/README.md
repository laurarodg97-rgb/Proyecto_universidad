# Simulador del punto de equilibrio: cobro por créditos vs. cobro por bandas

Busca con qué parámetros cada método de cobro deja el ingreso de la universidad **igual al actual** (394,56 mil millones, 2021-1 a 2026-1), usando simulación, *machine learning* y un servicio web con lo visto en *Python para Desarrollo de APIs e Inteligencia Artificial*. No modifica ningún archivo existente del repositorio y **no contiene datos de estudiantes**.

## Resultado

| Método | Tal como se presentó | Para llegar al equilibrio (una sola palanca) |
|---|---|---|
| Créditos (`Proyecto_u.R`) | 353,90 (−10,30 %) | subir la tarifa por crédito **11,49 %** |
| Bandas (`metodo_bandas/`) | 386,14 (−2,13 %) | subir las fracciones de 1–6 y 7–11 **27,8 %** (≈ 0,32 y 0,75 de M), o la matrícula plena **2,2 %**, o cobrar el crédito sobre 18 a **2,45 × T** |

Con el mismo ingreso total, el cobro por créditos baja mucho lo que pagan quienes inscriben pocos créditos (−69 % en 1–6) y lo carga a quienes inscriben 19 o más (+20 %). El cobro por bandas se parece más a lo que se paga hoy. Si los parámetros se calibran con 2021–2024, en 2025–2026 los dos métodos quedan ≈ 1,9 % por debajo del ingreso real, así que habría que recalibrarlos cada año. Las conclusiones completas están en el cuaderno ([`notebooks/simulacion_equilibrio.html`](notebooks/simulacion_equilibrio.html)).

## Arquitectura

```
simulacion_ml/
├── backend/                     API FastAPI
│   ├── app/
│   │   ├── main.py              app, lifespan (carga del modelo), /health
│   │   ├── config.py            BaseSettings + .env
│   │   ├── dependencies.py      Depends(): BD, simulador, modelo
│   │   ├── database.py          SQLAlchemy (SQLite)
│   │   ├── decoradores.py       @medir_tiempo
│   │   ├── models/              ORM (simulaciones, predicciones) y esquemas Pydantic
│   │   ├── services/            simulador de los dos métodos (POO) y carga de datos
│   │   ├── ml/                  train.py (offline), predictor.py (Singleton), artifacts/
│   │   ├── routers/             simulaciones, equilibrio, ml
│   │   └── data/base_agregada.csv
│   ├── tests/                   pytest + TestClient (BD en memoria)
│   ├── Dockerfile               multi-stage
│   └── requirements*.txt        versiones fijas
├── frontend/app.py              tablero Streamlit (solo consume la API)
├── notebooks/                   análisis completo (.ipynb y .html ya ejecutado)
├── scripts/preparar_agregados.py  base de estudiantes → base agregada (solo en local)
├── resultados/ · graficas/      salidas agregadas del cuaderno
├── docker-compose.yml · render.yaml · .env.example
└── ../../.github/workflows/simulacion_ml.yml   CI: pruebas + imágenes Docker
```

| Módulo del curso | Dónde está |
|---|---|
| 1 · Python para APIs | type hints, decorador `@medir_tiempo`, venv y `requirements.txt` fijos |
| 2 · HTTP | códigos 200, 201, 204, 400 (sin equilibrio en el rango), 404, 422, 503 (sin modelo) |
| 3 · POO | `MetodoCobro` (abstracta) → `CobroPorCreditos`, `CobroPorBandas`; `Simulador`; `ModelStore`; `ModelPredictor` |
| 4 y 7 · Pydantic y validación | rangos de cada palanca tomados de las clases, unión discriminada por `metodo`, validadores de periodos y palancas |
| 5 y 6 · FastAPI | routers, `response_model`, `/docs` y `/redoc` |
| 8 · Dependencias y configuración | `Depends`, `BaseSettings`, `lru_cache`, `.env` |
| 9 · SQLAlchemy | historial de simulaciones y log de predicciones |
| 10 · Testing | 32 pruebas: cuadre con R, equilibrio, contrato HTTP, Singleton y `/predict` |
| 11 y 12 · Docker, PaaS, CI/CD | Dockerfile multi-stage, docker-compose, `render.yaml`, GitHub Actions |
| 13 · ML en producción | metamodelo entrenado offline, `joblib`, Singleton con cerrojo, `/predict` |

### Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/health` | Estado, entorno y modelos cargados |
| GET | `/metodos` | Métodos y sus palancas (rango y valor presentado) |
| GET | `/periodos` | Periodos con datos |
| GET | `/balance/{metodo}` | Balance tal como se presentó, por facultad, periodo o banda |
| POST | `/simulaciones` | Simula unas palancas y guarda el resultado |
| GET/DELETE | `/simulaciones`, `/simulaciones/{id}` | Historial |
| POST | `/equilibrio` | Valor de una palanca que deja la brecha en cero |
| POST | `/montecarlo` | Sortea escenarios y resume la brecha |
| GET | `/validacion-temporal/{metodo}` | Calibra en 2021–2024 y prueba en 2025–2026 |
| POST | `/predict` | Brecha predicha por el modelo de ML (y la exacta, para comparar) |
| GET | `/modelo`, `/predicciones` | Metadata del modelo y log de predicciones |

Ejemplo:

```bash
curl -X POST localhost:8000/equilibrio -H "Content-Type: application/json" \
     -d '{"metodo": "bandas", "palanca": "k_parcial", "fijos": {"elasticidad": 0.1}}'
```

## Ejecutar

Requiere Python 3.12.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest                                      # pruebas
uvicorn app.main:app --reload                         # API en http://localhost:8000/docs

# en otra terminal
cd frontend && pip install -r requirements.txt
streamlit run app.py                                  # tablero en http://localhost:8501
```

O todo con Docker: `docker compose up --build`.

**Despliegue.** `render.yaml` define la API y el tablero para Render (*New → Blueprint*). El historial vive en SQLite dentro del contenedor, así que en el plan gratuito se borra al reiniciar; para conservarlo, defina `DATABASE_URL` con una base PostgreSQL.

**Variables de entorno.** Ver `.env.example`: `ENTORNO`, `LOG_LEVEL`, `DATABASE_URL`, `TOLERANCIA_EQUILIBRIO_MM`, `MAX_ESCENARIOS_MONTECARLO`, `BACKEND_URL` (tablero) y `RUTA_DATOS` (solo para el script de preparación).

### Regenerar datos, modelo y cuaderno

Solo con la base de estudiantes en local (nunca se sube):

```bash
RUTA_DATOS=/ruta/matriculas_anon.csv python scripts/preparar_agregados.py   # base agregada
cd backend && python -m app.ml.train                                        # modelos de ML
cd ../notebooks && RUTA_DATOS=/ruta/matriculas_anon.csv jupyter nbconvert --to notebook --execute --inplace simulacion_equilibrio.ipynb
```

## Datos y privacidad

`base_agregada.csv` tiene una fila por facultad × periodo × banda (308 celdas, mínimo 7 estudiantes cada una; el script se detiene si alguna tiene menos de 5) con sumas de pagos, matrícula plena y tarifa netas de beca. Como el cobro de los dos métodos es lineal dentro de cada celda, reproduce exactamente los totales calculados estudiante por estudiante (las pruebas lo verifican contra las cifras de los scripts en R).

La **elasticidad** (cuántos estudiantes inscriben menos créditos si sube el precio) es un supuesto de sensibilidad: la base no permite estimarla.
