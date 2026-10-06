FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/app/output
ENV LOG_DIR=/app/logs

CMD ["python", "main.py"]
