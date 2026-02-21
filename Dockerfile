FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime user (non-root) for least-privilege execution.
RUN groupadd --system --gid 10001 smarthome \
    && useradd --system --uid 10001 --gid 10001 --create-home smarthome

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ffmpeg nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY package.json /app/package.json
COPY package-lock.json /app/package-lock.json
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && npm ci --omit=dev --ignore-scripts

COPY . /app

# Writable runtime directories for config/state/stream segments.
RUN mkdir -p /app/config /app/plc_data /app/web/static/hls \
    && chown -R 10001:10001 /app

USER 10001:10001

EXPOSE 5000

CMD ["python", "start_web_hmi.py"]
