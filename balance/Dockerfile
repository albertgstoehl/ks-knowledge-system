# Build from project root: docker build -f balance/Dockerfile -t balance .
FROM python:3.11-slim

WORKDIR /app

COPY balance/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY balance/src/ ./src/
COPY shared/ ./shared/

ENV DATABASE_URL=/app/data/balance.db

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Force rebuild 1768075786
