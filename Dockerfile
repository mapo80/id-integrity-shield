# ---------- STAGE 1: build web (React + Vite) ----------
FROM node:20-alpine AS webbuild
WORKDIR /app/web

# Copia solo package.json (niente wildcard che potrebbe non esistere)
COPY web/package.json ./
RUN npm i

# Copia tutto il sorgente web e builda
COPY web/ ./
RUN npm run build

# ---------- STAGE 2: runtime Python + SDK + SPA ----------
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Runtime di sistema per onnxruntime/opencv + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libgomp1 curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install deps (prima i file di lock per cache, se ci sono)
COPY requirements.txt* pyproject.toml* setup.cfg* setup.py* ./
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi && \
    if [ -f pyproject.toml ] || [ -f setup.py ]; then pip install --no-cache-dir . || true; fi

# Minimi per API/SDK (se non già in requirements)
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart pydantic \
    numpy pillow psutil onnxruntime opencv-python starlette

# Codice del progetto
COPY . .

# Copia modelli/profili (sono già nel repo → arrivano con la COPY sopra)
# A runtime verificheremo l’esistenza; se mancassero, i test falliranno.

# Copia la SPA buildata
COPY --from=webbuild /app/web/dist /app/static

# Utente non-root
RUN useradd -m appuser && chown -R appuser:appuser /app

RUN mkdir -p /data/incoming /data/runs && chown -R appuser:appuser /data

USER appuser

# Config
ENV HOST=0.0.0.0 PORT=8000 SERVE_WEB=1 \
    IDS_MODELS_DIR=/app/models IDS_PROFILES_DIR=/app/profiles

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --start-period=10s --retries=5 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# Avvio: riusa la tua FastAPI (come nel repo)
CMD uvicorn app.main:app --host "$HOST" --port "$PORT" --proxy-headers
