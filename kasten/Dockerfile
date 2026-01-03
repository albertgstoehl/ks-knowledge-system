FROM python:3.11-slim

WORKDIR /app

COPY kasten/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kasten/src/ src/
COPY kasten/static/ static/
COPY shared/ ./shared/

RUN mkdir -p data

ENV NOTES_PATH=/app/notes

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
