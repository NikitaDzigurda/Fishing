FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# системные зависимости для psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

# CMD: выполнить миграции (с повторами до успешного выполнения), затем запустить uvicorn
CMD ["sh", "-c", "until alembic upgrade head; do echo 'alembic upgrade failed, retrying in 2s'; sleep 2; done && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
