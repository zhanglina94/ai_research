# Isolated experiment sandbox — CPU PyTorch for nanochat-style training
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

ENV PYTHONUNBUFFERED=1
ENV TRAIN_BUDGET_SECONDS=300

# Default: run train.py in mounted workspace
CMD ["python", "train.py"]
