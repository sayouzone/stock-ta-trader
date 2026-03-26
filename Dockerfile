FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[all]"

# App code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "ta_trader.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
