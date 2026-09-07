#!/usr/bin/env bash
set -euo pipefail
BUNDLE="${1:-.}"
cd "$BUNDLE"
sha256sum -c docker-images.tar.sha256
sha256sum -c models.sha256
docker load -i docker-images.tar
mkdir -p project/models
cp -a models/. project/models/
echo "Images and models imported. Configure project/.env, then launch docker-compose.airgap.yml."
