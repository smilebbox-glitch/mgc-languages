#!/usr/bin/env python3
"""Download approved models on a CONNECTED staging machine, then seal them for offline use."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stage(repo_id: str, target: Path, revision: str | None) -> dict:
    api = HfApi()
    info = api.model_info(repo_id, revision=revision)
    resolved = info.sha
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo_id, revision=resolved, local_dir=str(target))
    files = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and ".cache" not in path.parts:
            files.append({
                "path": str(path.relative_to(target)),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            })
    return {
        "repo_id": repo_id,
        "revision": resolved,
        "target": str(target),
        "file_count": len(files),
        "files": files,
    }



def stage_docling(target: Path) -> dict:
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mgc-docling-") as tmp:
        home = Path(tmp) / "home"
        home.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["HOME"] = str(home)
        subprocess.run(["docling-tools", "models", "download"], check=True, env=env)
        source = home / ".cache" / "docling" / "models"
        if not source.exists():
            raise RuntimeError(f"docling-tools completed but no artifacts found at {source}")
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    files = []
    for path in sorted(target.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(target)), "size": path.stat().st_size, "sha256": sha256(path)})
    return {"source": "docling-tools models download", "target": str(target), "file_count": len(files), "files": files}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="models")
    ap.add_argument("--generative", default=os.getenv("MGC_GENERATIVE_MODEL", "Qwen/Qwen3-VL-8B-Instruct"))
    ap.add_argument("--embeddings", default=os.getenv("MGC_EMBEDDING_MODEL", "BAAI/bge-m3"))
    ap.add_argument("--reranker", default=os.getenv("MGC_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"))
    ap.add_argument("--generative-revision", default=os.getenv("MGC_GENERATIVE_REVISION") or None)
    ap.add_argument("--embeddings-revision", default=os.getenv("MGC_EMBEDDING_REVISION") or None)
    ap.add_argument("--reranker-revision", default=os.getenv("MGC_RERANKER_REVISION") or None)
    ap.add_argument("--skip-generative", action="store_true", help="Stage only embeddings/reranker/Docling for CPU runtime")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runtime_policy": "offline-only; no model downloads permitted at runtime",
        "models": {
            **({} if args.skip_generative else {"generative": stage(args.generative, root / "generative", args.generative_revision)}),
            "embeddings": stage(args.embeddings, root / "embeddings", args.embeddings_revision),
            "reranker": stage(args.reranker, root / "reranker", args.reranker_revision),
            "docling": stage_docling(root / "docling"),
        },
    }
    out = root / "MODEL_MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
