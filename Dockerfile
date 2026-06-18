FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

COPY app ./app
COPY config ./config
COPY start.sh ./start.sh
COPY README.md ./README.md

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/bin/sh", "/app/start.sh"]
