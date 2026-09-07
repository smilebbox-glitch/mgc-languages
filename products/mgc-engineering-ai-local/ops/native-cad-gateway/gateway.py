from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

app = FastAPI(title="MGC Native CAD Gateway", version="1.0")

VENDOR = os.getenv("CAD_GATEWAY_VENDOR", "generic").strip().lower()
PRODUCT = os.getenv("CAD_GATEWAY_PRODUCT", "Approved Native CAD").strip()
SDK = os.getenv("CAD_GATEWAY_SDK", PRODUCT).strip()
SDK_VERSION = os.getenv("CAD_GATEWAY_SDK_VERSION", "unknown").strip()
BUILD = os.getenv("CAD_GATEWAY_BUILD", "reference-1.0").strip()
API_KEY = os.getenv("CAD_GATEWAY_API_KEY", "").strip()
REQUIRE_API_KEY = os.getenv("CAD_GATEWAY_REQUIRE_API_KEY", "true").strip().lower() not in {"0", "false", "no"}
if REQUIRE_API_KEY and not API_KEY:
    raise RuntimeError("CAD_GATEWAY_API_KEY must be configured unless CAD_GATEWAY_REQUIRE_API_KEY=false is explicitly set")
MAX_MB = max(int(os.getenv("CAD_GATEWAY_MAX_MB", "1000")), 1)
TIMEOUT = max(int(os.getenv("CAD_GATEWAY_TIMEOUT_SECONDS", "300")), 5)
EXTENSIONS = {x.strip().lower() for x in os.getenv("CAD_GATEWAY_EXTENSIONS", "").split(",") if x.strip()}
TARGETS = {x.strip().lower().lstrip(".") for x in os.getenv("CAD_GATEWAY_TARGETS", "step,pdf,dxf").split(",") if x.strip()}
CONVERTER_EXE = os.getenv("CAD_CONVERTER_EXE", "").strip()
try:
    CONVERTER_ARGS = json.loads(os.getenv("CAD_CONVERTER_ARGS_JSON", "[]"))
except json.JSONDecodeError as exc:
    raise RuntimeError(f"CAD_CONVERTER_ARGS_JSON is invalid JSON: {exc}") from exc
if not isinstance(CONVERTER_ARGS, list) or not all(isinstance(x, str) for x in CONVERTER_ARGS):
    raise RuntimeError("CAD_CONVERTER_ARGS_JSON must be a JSON array of strings")


def _auth(x_api_key: str | None) -> None:
    if REQUIRE_API_KEY and (not x_api_key or not secrets.compare_digest(API_KEY, x_api_key)):
        raise HTTPException(401, "Invalid gateway API key")
    if API_KEY and x_api_key and not secrets.compare_digest(API_KEY, x_api_key):
        raise HTTPException(401, "Invalid gateway API key")


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if not ext or (EXTENSIONS and ext not in EXTENSIONS):
        raise HTTPException(415, f"Unsupported native CAD extension: {ext or 'none'}")
    return ext


def _media_type(target: str) -> str:
    return {
        "step": "application/step",
        "stp": "application/step",
        "pdf": "application/pdf",
        "dxf": "application/dxf",
        "stl": "model/stl",
        "x_t": "application/octet-stream",
        "txt": "text/plain",
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(target, "application/octet-stream")


def _run_converter(source: Path, target_format: str, work: Path) -> tuple[Path, str]:
    if not CONVERTER_EXE:
        raise HTTPException(503, "CAD_CONVERTER_EXE is not configured")
    if not Path(CONVERTER_EXE).exists():
        raise HTTPException(503, "Configured CAD converter executable does not exist")
    requested = target_format.lower().lstrip(".")
    if requested != "auto" and requested not in TARGETS:
        raise HTTPException(400, f"Unsupported target format: {requested}")

    output_base = work / "converted"
    output = output_base.with_suffix("." + requested) if requested != "auto" else output_base
    substitutions = {
        "{input}": str(source),
        "{output}": str(output),
        "{output_base}": str(output_base),
        "{target}": requested,
    }
    args: list[str] = []
    for raw in CONVERTER_ARGS:
        value = raw
        for marker, replacement in substitutions.items():
            value = value.replace(marker, replacement)
        args.append(value)
    try:
        proc = subprocess.run(
            [CONVERTER_EXE, *args],
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            shell=False,
            check=False,
            env={**{k: v for k, v in os.environ.items() if k != "CAD_GATEWAY_API_KEY"}, "MGC_CAD_SOURCE_EXTENSION": source.suffix.lower()},
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "CAD conversion timed out")
    if proc.returncode != 0:
        # Vendor stdout/stderr may contain filenames, local paths or license details; keep it out of API responses.
        raise HTTPException(502, f"CAD converter failed with exit code {proc.returncode}")

    if requested == "auto":
        candidates = [p for p in work.glob("converted.*") if p.suffix.lower().lstrip(".") in TARGETS and p.is_file()]
        if len(candidates) != 1:
            raise HTTPException(502, f"Auto conversion must produce exactly one supported derivative, got {len(candidates)}")
        result = candidates[0]
        actual = result.suffix.lower().lstrip(".")
    else:
        result = output
        actual = requested
    if not result.exists() or result.stat().st_size == 0:
        raise HTTPException(502, "CAD converter produced no usable derivative")
    return result, actual


@app.get("/health")
def health(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _auth(x_api_key)
    return {"status": "ok", "vendor": VENDOR, "product": PRODUCT, "converter_configured": bool(CONVERTER_EXE)}


@app.get("/capabilities")
def capabilities(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _auth(x_api_key)
    return {
        "vendor": VENDOR,
        "product": PRODUCT,
        "formats": sorted(EXTENSIONS),
        "targets": sorted(TARGETS),
        "supports_auto_target": True,
        "sdk": SDK,
        "sdk_version": SDK_VERSION,
        "gateway_build": BUILD,
    }


@app.post("/convert")
async def convert(
    target_format: str = Form(default="auto"),
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    _auth(x_api_key)
    filename = Path(file.filename or "source.bin").name
    _safe_ext(filename)
    max_bytes = MAX_MB * 1024 * 1024
    with tempfile.TemporaryDirectory(prefix="mgc-cad-") as td:
        work = Path(td)
        source = work / filename
        size = 0
        with source.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(413, f"Native CAD file exceeds {MAX_MB} MB")
                out.write(chunk)
        try:
            result, actual = _run_converter(source, target_format, work)
            payload = result.read_bytes()
        finally:
            # TemporaryDirectory removes source and derivative. Explicit overwrite
            # reduces accidental recovery on simple local filesystems; full secure
            # erase is storage/OS policy, not something Python can guarantee.
            try:
                if source.exists() and source.stat().st_size:
                    with source.open("r+b", buffering=0) as fh:
                        fh.write(b"\0" * min(source.stat().st_size, 1024 * 1024))
            except Exception:
                pass
    return Response(
        content=payload,
        media_type=_media_type(actual),
        headers={
            "X-CAD-Vendor": VENDOR,
            "X-CAD-SDK": SDK,
            "X-CAD-SDK-Version": SDK_VERSION,
            "X-CAD-Gateway-Build": BUILD,
            "X-CAD-Target-Format": actual,
        },
    )
