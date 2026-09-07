# Docker build — MGC Engineering AI Local v4.0.0

## Connected build workstation

Copy environment template:

```bash
cp .env.airgap.example .env
```

Build the application images:

```bash
make build
```

Equivalent direct Docker Compose command:

```bash
docker compose \
  -f docker-compose.airgap.yml \
  -f docker-compose.build.yml \
  build api frontend gateway webhook-edge
```

Clean rebuild:

```bash
make build-no-cache
```

Start after the local model files exist under `./models/`:

```bash
make up
```

Check:

```bash
make ps
make logs
```

## Prepare the offline package

On the connected staging/build workstation:

```bash
make bundle
```

This builds the MGC application images and exports them together with the approved infrastructure images and local model files/checksums.

## Air-gapped target server

Do **not** rebuild Python/npm dependencies against the internet on the isolated target. Import the prepared bundle, then run:

```bash
cd project
cp .env.airgap.example .env
# set local secrets in .env
make up
make acceptance
```

Direct start command:

```bash
make up
```

## Image names

```text
mgc-engineering-ai-api:5.3.0-local
mgc-engineering-ai-frontend:5.3.0-local
```

The `worker` service reuses the API image.
