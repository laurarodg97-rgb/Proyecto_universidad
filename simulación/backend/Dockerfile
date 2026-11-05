# --- Etapa 1: instalar dependencias en un entorno virtual ---------------------
FROM python:3.12-slim AS constructor
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Etapa 2: imagen final, sin compiladores ni caché de pip ------------------
FROM python:3.12-slim
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENTORNO=produccion \
    DATABASE_URL=sqlite:////data/simulaciones.db
RUN useradd --create-home app && mkdir /data && chown app /data
COPY --from=constructor /opt/venv /opt/venv
WORKDIR /srv
# Solo el código, la base agregada y los modelos: nunca la base de estudiantes
COPY app ./app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8000\")}/health')"
# Render y Railway definen PORT; en local se usa 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
