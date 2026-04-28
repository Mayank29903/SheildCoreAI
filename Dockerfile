# Root Dockerfile for Render deployments from the repo root.
# Builds the FastAPI backend located at sportshield-ai/backend.

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY sportshield-ai/backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from transformers import pipeline; \
    p = pipeline('image-classification', \
    model='dima806/deepfake_vs_real_image_detection'); \
    print('SUCCESS: Deepfake model pre-loaded and cached in Docker layer')"

COPY sportshield-ai/backend/ ./

RUN mkdir -p /tmp/sportshield

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
