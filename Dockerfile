FROM python:3.12-slim

WORKDIR /app

# Solo las dependencias de runtime (ver requirements-runtime.txt). Las de
# desarrollo/experimentos (torch, transformers, prophet, spacy...) no se usan
# en el proyecto y multiplicaban el tamaño de la imagen.
COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

# .dockerignore excluye .env, .git y data/ (montada como volumen)
COPY . .

ENV PYTHONUNBUFFERED=1 \
    TZ=America/Caracas

EXPOSE 8090 8501

# Bootstrap del esquema. Los servicios runner y dashboard sobreescriben el CMD.
CMD ["python", "main.py"]
