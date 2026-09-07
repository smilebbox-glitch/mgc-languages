#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="/tmp/os-packages/runtime")
    ap.add_argument("--expected-base-image", default="")
    ap.add_argument("--require-install-receipt", action="store_true")
    args=ap.parse_args()
    root=Path(args.root); manifest=root/"OS_PACKAGE_MANIFEST.json"
    if not manifest.is_file(): raise SystemExit("OS package manifest missing")
    data=json.loads(manifest.read_text())
    if data.get("schema") != "mgc.os-package-bundle.v1": raise SystemExit("Unsupported OS package manifest schema")
    if args.expected_base_image and data.get("base_image") != args.expected_base_image:
        raise SystemExit("OS bundle base image does not match approved PYTHON_BASE_IMAGE")
    files=data.get("files") or []
    if not files: raise SystemExit("OS package manifest has no files")
    seen=set()
    for item in files:
        name=item.get("name", "")
        if not name.endswith(".deb") or "/" in name or "\\" in name: raise SystemExit(f"Invalid bundle filename: {name!r}")
        fp=root/name
        if not fp.is_file(): raise SystemExit(f"Missing OS package: {name}")
        if sha256(fp) != item.get("sha256"):
            raise SystemExit(f"Hash mismatch: {name}")
        if item.get("bytes") is not None and fp.stat().st_size != int(item["bytes"]):
            raise SystemExit(f"Size mismatch: {name}")
        seen.add(name)
    extra={x.name for x in root.glob("*.deb")}-seen
    if extra: raise SystemExit("Unmanifested OS packages: "+",".join(sorted(extra)))
    if args.require_install_receipt:
        receipt_path=root/"OS_PACKAGE_INSTALL_RECEIPT.json"
        if not receipt_path.is_file(): raise SystemExit("OS package offline install receipt missing")
        receipt=json.loads(receipt_path.read_text())
        if receipt.get("schema") != "mgc.os-package-install-receipt.v1": raise SystemExit("Unsupported OS package install receipt schema")
        if receipt.get("result") != "pass" or receipt.get("network_mode") != "none": raise SystemExit("OS package install receipt is not an offline PASS")
        if receipt.get("base_image") != data.get("base_image"): raise SystemExit("OS package install receipt base image mismatch")
        if args.expected_base_image and receipt.get("base_image") != args.expected_base_image: raise SystemExit("OS package install receipt does not match approved PYTHON_BASE_IMAGE")
        if receipt.get("manifest_sha256") != sha256(manifest): raise SystemExit("OS package install receipt manifest hash mismatch")
        if int(receipt.get("package_count", -1)) != len(files): raise SystemExit("OS package install receipt package count mismatch")
    print(f"OS package bundle verified: {len(files)} files" + (" + offline install receipt" if args.require_install_receipt else ""))

if __name__=="__main__": main()
