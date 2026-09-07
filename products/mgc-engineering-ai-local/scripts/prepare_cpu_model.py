#!/usr/bin/env python3
"""Stage one approved GGUF for the llama.cpp CPU runtime on a CONNECTED machine."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil
from datetime import datetime, timezone
from pathlib import Path
from huggingface_hub import HfApi, hf_hub_download

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.getenv('MGC_CPU_MODEL_REPO','Qwen/Qwen3-4B-GGUF'))
    ap.add_argument('--filename', default=os.getenv('MGC_CPU_MODEL_FILE','Qwen3-4B-Q4_K_M.gguf'))
    ap.add_argument('--revision', default=os.getenv('MGC_CPU_MODEL_REVISION') or None)
    ap.add_argument('--target', default='models/cpu')
    args=ap.parse_args()
    api=HfApi(); info=api.model_info(args.repo, revision=args.revision); resolved=info.sha
    target=Path(args.target).resolve(); target.mkdir(parents=True, exist_ok=True)
    path=Path(hf_hub_download(repo_id=args.repo, filename=args.filename, revision=resolved, local_dir=str(target)))
    shutil.rmtree(target/'.cache', ignore_errors=True)
    manifest={
      'schema':1,'created_at':datetime.now(timezone.utc).isoformat(),'runtime':'llama.cpp-cpu',
      'repo_id':args.repo,'revision':resolved,'filename':path.name,'size':path.stat().st_size,'sha256':sha256(path),
      'runtime_policy':'offline-only; no model download at runtime'
    }
    out=target/'CPU_MODEL_MANIFEST.json'; out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(out)
if __name__=='__main__': main()
