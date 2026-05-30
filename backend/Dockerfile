# Backend image: FastAPI + extraction toolchain (Tesseract, poppler, OpenCV libs for YOLO).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies for OCR (tesseract), PDF rendering (poppler) and ultralytics/OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# Install CPU-only PyTorch first (from PyTorch's CPU wheel index) so that ultralytics/YOLO
# does NOT pull in the multi-GB NVIDIA CUDA packages. This deployment runs on CPU.
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        torch torchvision
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV UPLOAD_DIR=/app/data/uploads \
    LOG_DIR=/app/logs

EXPOSE 8000

# Apply migrations, then start the API. (DB must be reachable; compose waits for health.)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
