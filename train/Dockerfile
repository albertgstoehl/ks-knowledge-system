# Build from project root: docker build -f train/Dockerfile -t train .
FROM python:3.11-slim

WORKDIR /app

COPY train/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY train/src/ ./src/
COPY train/plan/ ./plan/
COPY shared/ ./shared/

ENV DATABASE_URL=/app/data/train.db

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
