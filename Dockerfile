FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" --uid 10001 scraper \
    && mkdir -p /app/output /app/logs \
    && chown -R scraper:scraper /app

COPY --chown=scraper:scraper . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
ENV OUTPUT_DIR=/app/output
ENV LOG_DIR=/app/logs

USER scraper

CMD ["python", "main.py"]
