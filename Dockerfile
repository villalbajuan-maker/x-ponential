FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY requirements.lock.txt /app/
COPY company /app/company
COPY src /app/src

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.lock.txt \
    && python -m pip install . --no-deps

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "business_bridge.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
