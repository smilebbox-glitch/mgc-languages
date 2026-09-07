from __future__ import annotations

import ast
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
FRONTEND_PATH = ROOT / "static" / "app.js"
STYLES_PATH = ROOT / "static" / "styles.css"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}
CRITICAL_ROUTES = {
    ("GET", "/health"),
    ("GET", "/health/live"),
    ("GET", "/ready"),
    ("GET", "/health/ready"),
    ("GET", "/metrics"),
    ("GET", "/api/meta"),
    ("POST", "/api/login"),
    ("POST", "/api/logout"),
    ("GET", "/api/me"),
}
EXPECTED_CSRF_EXEMPT = {"/api/login", "/api/register", "/api/auth/oidc/callback"}
HARD_SIZE_BUDGETS = {
    "app.py": 260_000,
    "static/app.js": 145_000,
    "static/styles.css": 60_000,
}
SOFT_SIZE_BUDGETS = {
    "app.py": 220_000,
    "static/app.js": 110_000,
    "static/styles.css": 50_000,
}


def _route_records(tree: ast.AST) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if not isinstance(dec.func.value, ast.Name) or dec.func.value.id != "app":
                continue
            method = dec.func.attr.lower()
            if method not in HTTP_METHODS or not dec.args:
                continue
            path_node = dec.args[0]
            if not isinstance(path_node, ast.Constant) or not isinstance(path_node.value, str):
                continue
            records.append({
                "method": method.upper(),
                "path": path_node.value,
                "function": node.name,
                "line": getattr(dec, "lineno", getattr(node, "lineno", 0)),
                "role_guarded": _has_require_roles(node),
            })
    return records


def _has_require_roles(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    defaults = list(node.args.defaults) + [x for x in node.args.kw_defaults if x is not None]
    for default in defaults:
        for child in ast.walk(default):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == "require_roles":
                return True
    return False


def _csrf_exempt(tree: ast.AST) -> set[str] | None:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "CSRF_EXEMPT" for target in targets):
            continue
        value = node.value
        try:
            parsed = ast.literal_eval(value)
        except Exception:
            return None
        if isinstance(parsed, (set, list, tuple)) and all(isinstance(x, str) for x in parsed):
            return set(parsed)
        return None
    return None


def _root_static_mount_line(tree: ast.AST) -> int | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "app" or node.func.attr != "mount":
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "/":
            return getattr(node, "lineno", None)
    return None


def audit() -> dict[str, Any]:
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(APP_PATH))
    routes = _route_records(tree)
    errors: list[str] = []
    warnings: list[str] = []

    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for route in routes:
        by_key[(route["method"], route["path"])].append(route)
    for key, rows in sorted(by_key.items()):
        if len(rows) > 1:
            locations = ", ".join(f"{row['function']}@{row['line']}" for row in rows)
            errors.append(f"duplicate route {key[0]} {key[1]}: {locations}")

    route_keys = set(by_key)
    missing_critical = sorted(CRITICAL_ROUTES - route_keys)
    if missing_critical:
        errors.append("missing critical routes: " + ", ".join(f"{m} {p}" for m, p in missing_critical))

    unguarded_admin = [r for r in routes if r["path"].startswith("/api/admin/") and not r["role_guarded"]]
    if unguarded_admin:
        errors.append("admin routes without require_roles(): " + ", ".join(f"{r['method']} {r['path']}" for r in unguarded_admin))

    unsafe_mutators = [r for r in routes if r["method"] in STATE_CHANGING and not r["path"].startswith("/api/")]
    if unsafe_mutators:
        errors.append("state-changing routes outside /api/: " + ", ".join(f"{r['method']} {r['path']}" for r in unsafe_mutators))

    csrf = _csrf_exempt(tree)
    if csrf is None:
        errors.append("CSRF_EXEMPT must remain a statically auditable literal collection")
    elif csrf != EXPECTED_CSRF_EXEMPT:
        added = sorted(csrf - EXPECTED_CSRF_EXEMPT)
        removed = sorted(EXPECTED_CSRF_EXEMPT - csrf)
        errors.append(f"CSRF exemption drift detected; added={added}, removed={removed}")

    mount_line = _root_static_mount_line(tree)
    if mount_line is None:
        errors.append("root StaticFiles mount was not found")
    else:
        late_routes = [r for r in routes if r["line"] > mount_line]
        if late_routes:
            errors.append("API routes declared after root StaticFiles mount: " + ", ".join(f"{r['method']} {r['path']}" for r in late_routes))

    files = {
        "app.py": APP_PATH,
        "static/app.js": FRONTEND_PATH,
        "static/styles.css": STYLES_PATH,
    }
    sizes: dict[str, int] = {}
    for label, path in files.items():
        size = path.stat().st_size
        sizes[label] = size
        if size > HARD_SIZE_BUDGETS[label]:
            errors.append(f"{label} is {size} bytes; hard architecture budget is {HARD_SIZE_BUDGETS[label]}")
        elif size > SOFT_SIZE_BUDGETS[label]:
            warnings.append(f"{label} is {size} bytes; new functionality should be extracted into modules")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "route_count": len(routes),
            "admin_route_count": sum(1 for r in routes if r["path"].startswith("/api/admin/")),
            "sizes": sizes,
            "root_static_mount_line": mount_line,
        },
    }


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
