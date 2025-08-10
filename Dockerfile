
# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive     PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

# System deps (OpenCV runtime, fonts for reportlab)
RUN apt-get update && apt-get install -y --no-install-recommends \ 
        git curl ca-certificates libgl1 libglib2.0-0 libjpeg62-turbo libpng16-16         tesseract-ocr poppler-utils     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source
COPY idtamper ./idtamper
COPY profiles ./profiles
COPY scripts ./scripts
COPY tests ./tests
COPY app ./app
COPY requirements.txt ./requirements.txt
COPY models ./models

# Python deps
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn onnxruntime opencv-python-headless reportlab \
    && useradd -m app \
    && mkdir -p /data \
    && chown -R app /app /data

# Prepare models (Noiseprint++, ManTraNet)
# The script tries to download from the provided repos and assemble ONNX files.
RUN bash models/prepare_models.sh || true

# Expose API
ENV API_KEY=changeme
EXPOSE 8000
USER app
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
