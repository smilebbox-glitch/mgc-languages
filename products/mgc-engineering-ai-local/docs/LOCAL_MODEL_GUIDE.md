# Local model guide — v3.7 CPU/GPU

## CPU runtime

The supported CPU backend is `llama.cpp` serving a local GGUF through an OpenAI-compatible `/v1` API. The default staging example is `Qwen/Qwen3-4B-GGUF` / `Qwen3-4B-Q4_K_M.gguf`; replace it with any internally approved compatible GGUF.

```bash
make prepare-cpu
make cpu
```

CPU Standard keeps VLM disabled but retains deterministic drawing parsing/OCR/CAD. Optional CPU Vision can be enabled with a compatible multimodal model + matching `mmproj`:

```bash
make cpu-vision
```

## GPU runtime

The GPU profile retains vLLM and the approved local multimodal model:

```bash
make prepare-models
make gpu
```

## Automatic mode

`make up` uses `MGC_RUNTIME=auto`: GPU is selected only when NVIDIA hardware is visible and GPU model assets exist; otherwise the staged CPU GGUF is used.

For production, set `MGC_RUNTIME=cpu` or `MGC_RUNTIME=gpu` explicitly after acceptance testing.

## Shared retrieval models

Both runtimes use local `/models/embeddings` and `/models/reranker`; both are executed locally. Docling/OCR assets are also local.

## Security / supply chain

Before importing any model:

1. approve source repository and license;
2. resolve/pin exact revision;
3. scan files according to company policy;
4. record SHA-256;
5. import through the approved supply-chain path;
6. never enable public model downloads in production.

Runtime containers mount model directories read-only and do not expose model-server ports to users.
