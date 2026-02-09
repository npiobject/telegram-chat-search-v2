# =============================================================
# Dockerfile - Telegram Chat Search V2.0
# Multi-stage build optimizado para Railway
# =============================================================

# ---- Etapa 1: Builder ----
# Instala dependencias y pre-descarga el modelo de embeddings
FROM python:3.10-slim AS builder

WORKDIR /app

# Dependencias del sistema para compilar lxml y otras libs C
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libxml2-dev \
        libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python (PyTorch CPU-only)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Pre-descargar el modelo de embeddings (~100 MB)
# Se bakea en la imagen para evitar descargarlo en cada arranque
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# ---- Etapa 2: Runtime ----
# Imagen final ligera sin herramientas de compilacion
FROM python:3.10-slim

WORKDIR /app

# Solo librerias runtime (sin gcc/g++)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 && \
    rm -rf /var/lib/apt/lists/*

# Copiar site-packages y binarios instalados desde builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar cache del modelo HuggingFace desde builder
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

# Copiar codigo fuente y datos
COPY . .

# Variables de entorno
ENV GRADIO_SERVER_NAME=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface

# Puerto por defecto (Railway sobreescribe con $PORT)
EXPOSE 7860

# Comando de inicio
CMD ["python", "app.py"]
