# Construcción reproducible de la API propia CorePulse AI (sin modelo GPU incluido).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8765
# Sin logs HTTP de acceso; no se deben registrar preguntas ni telemetría.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765", "--no-access-log"]
