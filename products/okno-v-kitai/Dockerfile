FROM node:22-bookworm-slim AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run pilot:preflight && npm run build && node --test tests/*.test.mjs

FROM node:22-bookworm-slim AS runtime

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

COPY --from=build --chown=node:node /app /app
RUN mkdir -p /app/.wrangler /data && chown -R node:node /app/.wrangler /data

USER node
EXPOSE 3000

CMD ["npm", "start"]
