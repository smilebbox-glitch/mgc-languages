FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Offline pronunciation fallback for pilot runtime. No Internet is required to synthesize audio after the image is built.
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 mgc \
    && mkdir -p /data /var/cache/mgc-tts \
    && chown -R mgc:mgc /data /var/cache/mgc-tts /app

COPY --chown=mgc:mgc . .

USER mgc

ENV APP_ENV=development \
    DATABASE_URL=sqlite:////data/mgc.db \
    AUTO_CREATE_SCHEMA=true \
    AUTH_MODE=local \
    REGISTRATION_ENABLED=true \
    COOKIE_SECURE=false \
    OIDC_STATE_SECRET=dev-only-change-me

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)" || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
