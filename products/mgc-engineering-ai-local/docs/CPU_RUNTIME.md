# CPU Runtime — MGC Engineering AI Local v3.8.0

## Purpose

v3.7 can run the complete engineering service on a server **without an NVIDIA GPU**. The application/API is unchanged; only the local inference backend changes.

### CPU Standard (recommended default on CPU-only servers)

```text
Corporate engineer → SSO → MGC API
                         ├─ llama.cpp / GGUF (text LLM, CPU)
                         ├─ BGE embeddings / reranker (CPU)
                         ├─ Docling/OCR/vector-PDF parser (CPU)
                         ├─ OCCT/CadQuery CAD engine (CPU)
                         └─ PostgreSQL/Qdrant/Redis
```

Available in CPU Standard:

- Engineering RAG / «Спросить ИИ»;
- PDF/DOCX/XLSX/PPTX ingestion;
- vector-PDF parsing and OCR;
- STEP/STP/DXF and native-CAD derivative analysis;
- Drawing ↔ 3D geometry linking;
- BOM / revisions / similarity / Design Review;
- drawing activity history and engineer-only access.

The standalone image VLM is disabled in this profile because multimodal inference can be disproportionately slow on CPU. The UI clearly shows this and keeps deterministic drawing analysis enabled.

### CPU Vision (optional)

If IT stages a llama.cpp-compatible multimodal GGUF and its matching `mmproj` file, run:

```bash
make cpu-vision
```

The vision server is isolated on the internal Docker network, uses one parallel slot, `--gpu-layers 0`, `--no-mmproj-offload`, API-key authentication and `--no-webui`.

## Prepare models on a connected staging machine

Install staging requirements once:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r scripts/requirements-airgap-prep.txt
```

Prepare CPU runtime assets:

```bash
make prepare-cpu
```

The default CPU text baseline is:

```text
Repository: Qwen/Qwen3-4B-GGUF
File:       Qwen3-4B-Q4_K_M.gguf
```

The model choice is not hard-wired. Override it before staging:

```bash
MGC_CPU_MODEL_REPO=approved/repository \
MGC_CPU_MODEL_FILE=approved-model.gguf \
make prepare-cpu
```

`prepare_cpu_model.py` resolves the repository revision, downloads exactly the selected GGUF on the connected machine, calculates SHA-256 and writes `models/cpu/CPU_MODEL_MANIFEST.json`. Runtime containers never download models.

## Launch

### Automatic selection

```bash
make up
```

`MGC_RUNTIME=auto` selects GPU only when `nvidia-smi` is available and GPU model files are staged. Otherwise it selects the staged CPU GGUF.

### Force CPU

```bash
make cpu
```

### Force GPU

```bash
make gpu
```

### Force CPU + Vision

```bash
make cpu-vision
```

For predictable production operation, set one value explicitly in `.env` after hardware acceptance:

```text
MGC_RUNTIME=cpu
```

or:

```text
MGC_RUNTIME=gpu
```


## Capacity check before first start

Run:

```bash
make cpu-check
```

The helper reads the available logical CPUs and RAM and prints conservative `.env` starting values for LLM threads, auxiliary OCR/embedding threads, worker concurrency and context size. It does **not** silently rewrite `.env`; IT remains in control of the final limits. On a very small host the service can still start, but keep CPU Vision disabled and expect slow generative answers.

## CPU sizing

There is no universal performance number because throughput depends on CPU generation, memory bandwidth, quantization, context length and concurrency. Treat these as deployment starting points, not guarantees:

| Profile | Suggested starting point |
|---|---|
| Small pilot | 8 physical cores / 16 GB RAM |
| Normal engineering team | 16+ physical cores / 32 GB RAM |
| Heavier CPU service | 24–32+ physical cores / 64 GB RAM |

A Q4 4B GGUF itself is only part of memory use; allow headroom for KV cache, embeddings/reranker, OCR, CAD parsing, PostgreSQL/Qdrant and concurrent jobs.

Tune:

```text
CPU_THREADS=8
CPU_THREADS_BATCH=8
CPU_AUX_THREADS=4
CPU_WORKER_CONCURRENCY=1
CPU_PARALLEL=1
CPU_CONTEXT_SIZE=8192
```

Start conservatively. Increasing every thread/concurrency setting at once can reduce throughput through CPU oversubscription.

## Security properties

CPU mode does **not** weaken the v3.5 engineer-only controls:

- model-server has no host-published port;
- llama.cpp WebUI is disabled;
- model API requires the internal model API key;
- model files are mounted read-only;
- container root filesystem is read-only;
- `no-new-privileges` and `cap_drop: ALL` are applied;
- only the corporate SSO proxy is exposed to engineers;
- public model downloads are disabled at runtime.

Run after deployment:

```bash
make acceptance
make dockle
```

## Air-gap bundle

CPU-only package:

```bash
make bundle-cpu
```

GPU package:

```bash
make bundle-gpu
```

This avoids transferring the large GPU generative model to a CPU-only server.
