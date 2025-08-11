# ---------- STAGE 1: build web (React + Vite) ----------
FROM node:20-alpine AS webbuild
WORKDIR /app/web

# Se la webapp esiste in ./web, la buildiamo; altrimenti creeremo uno stub.
COPY web/package.json web/package-lock.json* web/pnpm-lock.yaml* web/yarn.lock* ./ 2>/dev/null || true
RUN if [ -f package.json ]; then \
      if [ -f package-lock.json ]; then npm ci; else npm i; fi; \
    fi
COPY web/ ./ 2>/dev/null || true
RUN if [ -f package.json ]; then npm run build; else \
      mkdir -p dist && printf '<!doctype html><html><head><meta charset="utf-8"><title>ID Shield</title></head><body><h1>ID Shield</h1><p>SPA not built (web/ missing). API OK.</p></body></html>' > dist/index.html; \
    fi

# ---------- STAGE 2: runtime Python + SDK + SPA ----------
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Runtime di sistema per onnxruntime/opencv + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libgomp1 curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (prima file di lock per cache)
COPY requirements.txt* pyproject.toml* setup.cfg* setup.py* ./
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi && \
    if [ -f pyproject.toml ] || [ -f setup.py ]; then pip install --no-cache-dir . || true; fi

# Minimi per API/SDK (se non già in requirements)
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart pydantic \
    numpy pillow psutil onnxruntime opencv-python starlette

# Copia codice sorgente del progetto
COPY . .

# Copia modelli/profili nel container (certezza di disponibilità)
# Se esistono in repo, finiscono in /app/models e /app/profiles
RUN test -d models && echo "[Docker] models/ found" || (echo "[Docker] WARNING: models/ missing"; true)
RUN test -d profiles && echo "[Docker] profiles/ found" || (echo "[Docker] WARNING: profiles/ missing"; true)

# Copia la SPA buildata
COPY --from=webbuild /app/web/dist /app/static

# Utente non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Config
ENV HOST=0.0.0.0 PORT=8000 SERVE_WEB=1 \
    IDS_MODELS_DIR=/app/models IDS_PROFILES_DIR=/app/profiles

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=3s --start-period=10s --retries=5 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# Avvio: riusa la tua FastAPI (come da README)
CMD uvicorn app.main:app --host "$HOST" --port "$PORT" --proxy-headers
