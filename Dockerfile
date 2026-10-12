FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --no-cache-dir --timeout=300 --retries=10 -r requirements.txt

COPY . .

CMD ["python", "-c", "import cv2, mediapipe, pygame; print('VisionPlay dependencies loaded successfully')"]
