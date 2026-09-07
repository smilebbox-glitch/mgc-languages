#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "models").resolve()
manifest_path = root / "MODEL_MANIFEST.json"
if not manifest_path.exists():
    raise SystemExit(f"missing {manifest_path}")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
errors = []
for role, model in manifest.get("models", {}).items():
    base = root / role
    if not base.is_dir():
        errors.append(f"{role}: missing directory {base}")
        continue
    for item in model.get("files", []):
        p = base / item["path"]
        if not p.is_file():
            errors.append(f"{role}: missing {item['path']}")
            continue
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != item["sha256"]:
            errors.append(f"{role}: checksum mismatch {item['path']}")
if errors:
    print("MODEL MANIFEST: FAILED")
    print("\n".join(errors[:50]))
    raise SystemExit(2)
print("MODEL MANIFEST: OK")
