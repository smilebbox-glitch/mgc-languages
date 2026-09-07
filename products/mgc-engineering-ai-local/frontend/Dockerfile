ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NODE_BASE_IMAGE} AS build
WORKDIR /app
COPY package*.json tsconfig.json vite.config.ts index.html ./
COPY npm-cache ./npm-cache
COPY src ./src
ARG VITE_API_URL=http://localhost:8080
ARG VITE_API_KEY=
ARG NPM_DEPENDENCY_MODE=range
ENV VITE_API_URL=$VITE_API_URL VITE_API_KEY=$VITE_API_KEY
RUN case "$NPM_DEPENDENCY_MODE" in \
      locked) test -s package-lock.json \
              && test -d npm-cache/_cacache \
              && npm ci --offline --cache=/app/npm-cache --ignore-scripts --no-audit --no-fund ;; \
      range)  if [ -f package-lock.json ]; then npm ci --ignore-scripts --no-audit --no-fund; else npm install --ignore-scripts --no-audit --no-fund; fi ;; \
      *) echo "Invalid NPM_DEPENDENCY_MODE=$NPM_DEPENDENCY_MODE" >&2; exit 2 ;; \
    esac \
    && npm run build

FROM ${NGINX_BASE_IMAGE}
ARG MGC_BUILD_VERSION=dev
ARG MGC_BUILD_SOURCE_SHA256=unverified
LABEL org.opencontainers.image.title="MGC Engineering AI Frontend" \
      org.opencontainers.image.version="${MGC_BUILD_VERSION}" \
      org.opencontainers.image.revision="${MGC_BUILD_SOURCE_SHA256}"
RUN rm -f /etc/nginx/conf.d/default.conf \
    && mkdir -p /tmp/client_temp /tmp/proxy_temp /tmp/fastcgi_temp /tmp/uwsgi_temp /tmp/scgi_temp \
    && chown -R nginx:nginx /tmp /var/cache/nginx /usr/share/nginx/html \
    && find / -xdev -type f \( -perm -4000 -o -perm -2000 \) -exec chmod a-s {} + 2>/dev/null || true
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
