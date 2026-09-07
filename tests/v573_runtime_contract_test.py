from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from mgc_core.contracts import RuntimeContractError, inspect_route_contract, validate_route_contract  # noqa: E402

app = FastAPI()

@app.get("/probe")
def probe():
    return {"ok": True}

report = inspect_route_contract(app, required={("GET", "/probe")})
assert report.ok
assert report.route_count == report.unique_route_count
validate_route_contract(app, required={("GET", "/probe")})

try:
    validate_route_contract(app, required={("GET", "/missing")})
except RuntimeContractError as exc:
    assert "GET /missing" in str(exc)
else:
    raise AssertionError("missing required route must fail the runtime contract")

print("OK: v5.7.3 runtime contract validator fails closed when required routes disappear")
