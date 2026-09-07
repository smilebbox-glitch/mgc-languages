ARG PYTHON_BASE_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_BASE_IMAGE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
ARG DEPLOYMENT_PROFILE=core
ARG PYTHON_DEPENDENCY_MODE=range
RUN if [ "$PYTHON_DEPENDENCY_MODE" = "range" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends build-essential \
      && rm -rf /var/lib/apt/lists/*; \
    elif [ "$PYTHON_DEPENDENCY_MODE" != "locked" ]; then \
      echo "Invalid PYTHON_DEPENDENCY_MODE=$PYTHON_DEPENDENCY_MODE" >&2; exit 2; \
    fi
COPY requirements*.txt ./
COPY locks ./locks
COPY wheelhouse ./wheelhouse
RUN case "$DEPLOYMENT_PROFILE" in core|ai|advanced) ;; *) echo "Invalid DEPLOYMENT_PROFILE=$DEPLOYMENT_PROFILE" >&2; exit 2 ;; esac \
    && case "$PYTHON_DEPENDENCY_MODE" in \
         locked) test -s "locks/requirements-${DEPLOYMENT_PROFILE}.lock.txt" \
                 && test -f "wheelhouse/${DEPLOYMENT_PROFILE}/WHEELHOUSE_MANIFEST.json" \
                 && mkdir -p /wheels \
                 && cp -a "wheelhouse/${DEPLOYMENT_PROFILE}/." /wheels/ ;; \
         range)  python -m pip wheel --wheel-dir /wheels -r "requirements-${DEPLOYMENT_PROFILE}.txt" ;; \
         *) echo "Invalid PYTHON_DEPENDENCY_MODE=$PYTHON_DEPENDENCY_MODE" >&2; exit 2 ;; \
       esac

FROM ${PYTHON_BASE_IMAGE}
ARG PYTHON_BASE_IMAGE
ARG DEPLOYMENT_PROFILE=core
ARG PYTHON_DEPENDENCY_MODE=range
ARG OS_DEPENDENCY_MODE=apt
ARG MGC_BUILD_VERSION=dev
ARG MGC_BUILD_SOURCE_SHA256=unverified
LABEL org.opencontainers.image.title="MGC Engineering AI Backend" \
      org.opencontainers.image.version="${MGC_BUILD_VERSION}" \
      org.opencontainers.image.revision="${MGC_BUILD_SOURCE_SHA256}"
ENV MGC_BUILD_PROFILE=${DEPLOYMENT_PROFILE} \
    MGC_DEPENDENCY_MODE=${PYTHON_DEPENDENCY_MODE} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/mgc
RUN groupadd --gid 10001 mgc \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/mgc --shell /usr/sbin/nologin mgc \
    && find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod a-s {} + 2>/dev/null || true
COPY --from=builder /wheels /wheels
COPY requirements*.txt /tmp/requirements/
COPY locks /tmp/locks/
COPY os-packages /tmp/os-packages/
COPY verify_os_package_bundle.py /tmp/verify_os_package_bundle.py
RUN if [ "$OS_DEPENDENCY_MODE" = "bundle" ]; then \
      python /tmp/verify_os_package_bundle.py /tmp/os-packages/runtime --expected-base-image "$PYTHON_BASE_IMAGE" --require-install-receipt \
      && dpkg -i /tmp/os-packages/runtime/*.deb; \
    elif [ "$OS_DEPENDENCY_MODE" = "apt" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 libgomp1 libegl1 libopengl0 \
      && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "Invalid OS_DEPENDENCY_MODE=$OS_DEPENDENCY_MODE" >&2; exit 2; \
    fi \
    && if [ "$MGC_DEPENDENCY_MODE" = "locked" ]; then \
      python -m pip install --no-index --no-cache-dir --find-links=/wheels --require-hashes -r "/tmp/locks/requirements-${MGC_BUILD_PROFILE}.lock.txt"; \
    else \
      python -m pip install --no-index --no-cache-dir --find-links=/wheels -r "/tmp/requirements/requirements-${MGC_BUILD_PROFILE}.txt"; \
    fi \
    && python -m pip check \
    && rm -rf /wheels /tmp/requirements /tmp/locks /tmp/os-packages /tmp/verify_os_package_bundle.py
WORKDIR /app
COPY --chown=mgc:mgc app ./app
RUN mkdir -p /data/storage /data/inbox /tmp/mgc \
    && chown -R mgc:mgc /data /tmp/mgc /app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health/ready', timeout=3).read()"]
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080","--no-access-log"]
