#!/usr/bin/env python3
"""Fail closed if a human-facing API route lacks engineer identity enforcement."""
from __future__ import annotations

import ast
from pathlib import Path

ROUTE_FILES = sorted(p for p in Path("backend/app/api").rglob("*.py") if p.name != "context_shared.py")
# Deliberate non-human/public exceptions. Webhook has its own HMAC verifier.
EXEMPT = {
    ("health_routes.py", "/health"),
    ("health_routes.py", "/health/live"),
    ("health_routes.py", "/health/ready"),
    ("health_routes.py", "/health/lb"),
    ("integration_routes.py", "/integrations/webhooks/{system_code}"),
}

failures: list[str] = []
checked = 0

for path in ROUTE_FILES:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        routes: list[str] = []
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if not isinstance(dec.func.value, ast.Name) or dec.func.value.id != "router":
                continue
            if not dec.args or not isinstance(dec.args[0], ast.Constant) or not isinstance(dec.args[0].value, str):
                continue
            routes.append(dec.args[0].value)
        for route in routes:
            if (path.name, route) in EXEMPT:
                print(f"PASS exempt  {path.name}:{route}")
                continue
            checked += 1
            guarded = False
            for arg in [*node.args.args, *node.args.kwonlyargs]:
                default = None
                # Easier/safer: search function subtree for Depends(get_identity).
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                if not isinstance(sub.func, ast.Name) or sub.func.id != "Depends" or not sub.args:
                    continue
                target = sub.args[0]
                if isinstance(target, ast.Name) and target.id == "get_identity":
                    guarded = True
                    break
            if guarded:
                print(f"PASS guarded {path.name}:{route}")
            else:
                failures.append(f"{path.name}:{route} ({node.name})")
                print(f"FAIL unguarded {path.name}:{route}")

if failures:
    raise SystemExit("Engineer-only API preflight failed: " + ", ".join(failures))
print(f"PASS: {checked} human-facing API routes enforce get_identity; {len(EXEMPT)} explicit exceptions")
