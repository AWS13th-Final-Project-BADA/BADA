FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY worker/requirements.txt /tmp/worker-requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libmagic1 \
       # WeasyPrint 의존성
       libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev libcairo2 \
       # 폰트 (slim 이미지에서 사용 가능한 패키지)
       fonts-noto-cjk \
       fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install -r /tmp/worker-requirements.txt

# 추가 폰트 (크메르, 데바나가리 등)
COPY worker/fonts/ /usr/share/fonts/truetype/bada/
RUN fc-cache -fv 2>/dev/null || true

COPY worker /app/worker
COPY backend/app /app/backend/app

WORKDIR /app/worker

CMD ["python", "consumer.py"]
