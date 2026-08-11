FROM python:3.10-slim

WORKDIR /app

# System deps needed by torch/pillow wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src ./src
COPY web ./web
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "narrately.api:app", "--host", "0.0.0.0", "--port", "8000"]
