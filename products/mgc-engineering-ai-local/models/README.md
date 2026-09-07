# Offline model directory — v3.7

The runtime never downloads model weights.

```text
models/
  cpu/          # CPU text GGUF + CPU_MODEL_MANIFEST.json
  cpu-vision/   # optional multimodal GGUF + mmproj
  generative/   # GPU/vLLM multimodal model
  embeddings/   # local SentenceTransformers model
  reranker/     # local CrossEncoder reranker
  docling/      # prefetched Docling/OCR artifacts
  MODEL_MANIFEST.json
```

CPU-only staging:

```bash
make prepare-cpu
```

GPU staging:

```bash
make prepare-models
```

No model choice is trusted implicitly. Pin/approve the source and revision, scan it according to company policy, and verify SHA-256 before import into the isolated environment.
