ARG PYTHON_BASE_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_BASE_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY ops/mock-integrations/requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt \
    && groupadd --gid 10002 mock \
    && useradd --uid 10002 --gid 10002 --create-home --shell /usr/sbin/nologin mock \
    && find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod a-s {} + 2>/dev/null || true
COPY --chown=mock:mock ops/mock-integrations/app.py /app/app.py
COPY --chown=mock:mock samples /app/samples
USER 10002:10002
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2).read()"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090", "--no-access-log"]
