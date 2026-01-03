FROM python:3.11-slim

WORKDIR /app

COPY canvas/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY canvas/src/ src/
COPY canvas/static/ static/
COPY shared/ ./shared/

RUN mkdir -p data

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
