FROM python:3.12-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASHCARDS_HOST=0.0.0.0 \
    FLASHCARDS_PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python3", "tools/flashcards_app.py", "--host", "0.0.0.0", "--port", "8000"]
