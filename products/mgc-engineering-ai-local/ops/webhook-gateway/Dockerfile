ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NGINX_BASE_IMAGE}
ARG MGC_BUILD_VERSION=dev
ARG MGC_BUILD_SOURCE_SHA256=unverified
LABEL org.opencontainers.image.title="MGC Engineering AI Webhook Edge" \
      org.opencontainers.image.version="${MGC_BUILD_VERSION}" \
      org.opencontainers.image.revision="${MGC_BUILD_SOURCE_SHA256}"
RUN rm -f /etc/nginx/conf.d/default.conf \
    && mkdir -p /tmp/nginx /var/cache/nginx \
    && chown -R nginx:nginx /tmp/nginx /var/cache/nginx /etc/nginx \
    && find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true
COPY ops/webhook-gateway/nginx.conf /etc/nginx/nginx.conf
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
CMD ["nginx", "-g", "daemon off;"]
