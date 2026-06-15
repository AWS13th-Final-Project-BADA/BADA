FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY worker/requirements.txt /tmp/worker-requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install -r /tmp/worker-requirements.txt

COPY worker /app/worker

WORKDIR /app/worker

CMD ["python", "try_case.py", "sample_case.json"]
