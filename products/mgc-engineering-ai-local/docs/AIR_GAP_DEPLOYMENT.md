# Air-gapped deployment

## Definition of "local"

Production runtime is accepted as local only when all of the following are true:

1. LLM/VLM weights are stored inside the corporate network.
2. Embedding and reranker weights are stored inside the corporate network.
3. No request is sent to OpenAI, Anthropic, Google, Hugging Face Inference, or another public AI API.
4. Containers do not download weights or packages at runtime.
5. Docker images are preloaded or pulled only from an internal registry.
6. Public egress from the Engineering AI segment is denied.
7. The application still answers after public internet access is removed.

`docker-compose.airgap.yml` implements this topology. It keeps API/data/model services on an `internal: true` Docker network, does not publish the model server, and places only the reverse proxy on a second host-facing bridge. Public egress must also be denied at the host/VLAN firewall.

## Offline model topology

The default deployment uses one multimodal model for both text synthesis and drawing vision:

```text
FastAPI -> http://model-server:8000/v1 -> vLLM (GPU) OR llama.cpp (CPU) -> local model weights
           ^                                      |
           |                                      X public internet
           +---- PDF/image VLM requests

FastAPI/worker -> /models/embeddings
FastAPI/worker -> /models/reranker
```

This reduces GPU count for a pilot. Larger deployments can split LLM and VLM into separate model servers later.

## Connected staging machine

The runtime server does **not** need internet. A separate approved staging workstation may be used once to obtain approved model weights and container images.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r scripts/requirements-airgap-prep.txt
python scripts/prepare_models.py
./scripts/prepare_airgap_bundle.sh
```

The default preparation profile downloads:

- `Qwen/Qwen3-VL-8B-Instruct` for local text + vision;
- `BAAI/bge-m3` for embeddings;
- `BAAI/bge-reranker-v2-m3` for reranking.

These are only defaults. Security/licensing teams should approve exact repositories and revisions. The preparation script pins the resolved repository commit in `MODEL_MANIFEST.json` and hashes every staged file.

## Transfer to the isolated server

Transfer `dist/mgc-airgap-bundle` using the company's approved media/process. On the target:

```bash
cd mgc-airgap-bundle
./project/scripts/airgap_import.sh .
cd project
cp .env.airgap.example .env
# edit secrets

make up
./scripts/airgap_acceptance.sh
```

## What the acceptance test proves

The acceptance script verifies:

- model manifest SHA-256 checksums;
- required local Docker images exist;
- API health;
- local model server reachability through `/v1/models`;
- local embedding and reranker directories exist;
- `AIR_GAPPED_MODE=true`;
- runtime model downloads are disabled;
- an outbound request from the API container to `huggingface.co` fails.

A production firewall should additionally deny public egress at the host/VLAN/firewall layer. Docker isolation is defense in depth, not a replacement for network policy.


## Image pinning gate (v3.4)

Before `make bundle`, copy `.env.airgap.example` to `.env` and replace all `REPLACE_WITH_APPROVED_*` image placeholders with IT-approved image tags or digests. The bundle script runs `scripts/validate_airgap_image_pins.py` and refuses `:latest` or unresolved placeholders. The exported `docker-images.manifest` records the actual image IDs transferred to the isolated server.


## CPU-only deployment

On the connected staging machine run `make prepare-cpu` and `make bundle-cpu`. On the target set `MGC_RUNTIME=cpu`, then `make up` and `make acceptance`. See `CPU_RUNTIME.md`.
