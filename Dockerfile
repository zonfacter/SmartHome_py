FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime user (non-root) for least-privilege execution.
RUN groupadd --system --gid 10001 smarthome \
    && useradd --system --uid 10001 --gid 10001 --create-home smarthome

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Writable runtime directories for config/state/stream segments.
RUN mkdir -p /app/config /app/plc_data /app/web/static/hls \
    && chown -R 10001:10001 /app

USER 10001:10001

EXPOSE 5000

CMD ["python", "start_web_hmi.py"]
