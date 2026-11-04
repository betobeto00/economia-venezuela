FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# .dockerignore excluye .env, .git y data/ (montada como volumen)
COPY . .

EXPOSE 8090 8501

# Scheduler legado; el servicio runner lo sobreescribe con uvicorn.
CMD ["python", "main.py"]
