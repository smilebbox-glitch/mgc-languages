ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NGINX_BASE_IMAGE}
RUN rm -f /etc/nginx/conf.d/default.conf \
    && mkdir -p /tmp/client_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp \
    && chown -R nginx:nginx /tmp /var/cache/nginx /etc/nginx/conf.d \
    && find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod a-s {} + 2>/dev/null || true
COPY ops/enterprise-edge/nginx.conf /etc/nginx/nginx.conf
USER nginx
EXPOSE 8443 9443
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget --no-check-certificate -q -O /dev/null https://127.0.0.1:8443/healthz || exit 1
CMD ["nginx", "-g", "daemon off;"]
