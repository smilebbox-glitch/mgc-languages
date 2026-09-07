ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NGINX_BASE_IMAGE}
ARG MGC_BUILD_VERSION=dev
ARG MGC_BUILD_SOURCE_SHA256=unverified
LABEL org.opencontainers.image.title="MGC Engineering AI Gateway" \
      org.opencontainers.image.version="${MGC_BUILD_VERSION}" \
      org.opencontainers.image.revision="${MGC_BUILD_SOURCE_SHA256}"
RUN rm -f /etc/nginx/conf.d/default.conf \
    && mkdir -p /etc/nginx/templates /etc/nginx/conf.d /tmp/client_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp \
    && chown -R nginx:nginx /etc/nginx/conf.d /tmp /var/cache/nginx \
    && find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod a-s {} + 2>/dev/null || true
COPY ops/gateway/nginx.conf /etc/nginx/nginx.conf
COPY ops/gateway/templates/default.conf.template /etc/nginx/templates/default.conf.template
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
