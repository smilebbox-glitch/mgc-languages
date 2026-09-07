#!/usr/bin/env python3
"""v6.3.2 Ports & Adapters and Work Instruction governance verification."""
from __future__ import annotations

import ast
import importlib.abc
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

checks = []
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))

ports = ROOT / "backend/app/ports"
adapters = ROOT / "backend/app/adapters"
for name in ["search.py", "graph.py", "object_storage.py", "ai.py", "translation.py"]:
    check(f"port_{name}_exists", (ports / name).exists())
check("adapter_registry_exists", (adapters / "registry.py").exists())

# Application/delivery layers must not know concrete infrastructure modules.
for rel in [
    "backend/app/services/ingest.py",
    "backend/app/services/rag.py",
    "backend/app/services/engineering_translation.py",
    "backend/app/services/work_instructions.py",
    "backend/app/api/contexts/intelligence_search.py",
]:
    text = (ROOT / rel).read_text()
    concrete = [x for x in ["app.services.vector_store", "app.services.graph_store", "app.services.object_store"] if x in text]
    check(f"no_concrete_infrastructure:{Path(rel).name}", not concrete, ",".join(concrete))

check("rag_has_no_http_client", "import httpx" not in (ROOT / "backend/app/services/rag.py").read_text())
check("translation_has_no_http_client", "import httpx" not in (ROOT / "backend/app/services/engineering_translation.py").read_text())
check("wi_rag_has_no_http_client", "import httpx" not in (ROOT / "backend/app/services/work_instructions.py").read_text())

# Concrete technology imports are allowed only behind adapters/legacy implementation modules.
forbidden_packages = {"qdrant_client", "sentence_transformers", "neo4j", "minio"}
violations = []
for path in (ROOT / "backend/app").rglob("*.py"):
    rel = path.relative_to(ROOT / "backend/app")
    if rel.parts[0] == "adapters" or str(rel) in {"services/vector_store.py", "services/graph_store.py", "services/object_store.py", "services/reranker.py"}:
        continue
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        module = None
        if isinstance(node, ast.ImportFrom): module = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] in forbidden_packages:
                    violations.append(f"{rel}:{alias.name}")
        if module and module.split('.')[0] in forbidden_packages:
            violations.append(f"{rel}:{module}")
check("concrete_packages_behind_adapter_boundary", not violations, "; ".join(violations))

# Core profile must select no-op/deterministic adapters while optional packages are blocked.
BLOCK = {"qdrant_client", "sentence_transformers", "neo4j", "minio"}
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCK:
            raise ImportError(f"blocked optional package: {fullname}")
        return None
sys.meta_path.insert(0, Blocker())
try:
    from app.core.config import Settings
    from app.adapters.registry import get_search_port, get_graph_projection_port, get_object_storage_port, get_ai_analysis_port, get_translation_provider_port
    core = Settings(deployment_profile="core")
    selected = {
        get_search_port(core).mode,
        get_graph_projection_port(core).mode,
        get_object_storage_port(core).mode,
        get_ai_analysis_port(core).mode,
        get_translation_provider_port(core).mode,
    }
    imported = [x for x in sys.modules if x.split('.')[0] in BLOCK]
    check("core_adapter_selection_without_optional_packages", not imported, str(imported))
    check("core_uses_deterministic_noop_adapters", {"core_lexical_postgres", "disabled", "local_evidence_only"} <= selected, str(sorted(selected)))
except Exception as exc:
    check("core_adapter_selection_without_optional_packages", False, repr(exc))
    check("core_uses_deterministic_noop_adapters", False, repr(exc))

wi = (ROOT / "backend/app/services/work_instructions.py").read_text()
route = (ROOT / "backend/app/api/contexts/manufacturing_quality.py").read_text()
check("translation_fingerprint_present", "translation_source_fingerprint" in wi and "translation_is_current" in wi)
check("stale_translation_gate", 'row.translation_status = "stale"' in route)
check("approved_wi_immutable", "Approved work instruction is immutable" in route)
check("approval_requires_current_translation", "Current reviewed Russian translation is required before approval" in route)

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION, runtime_contract
check("release_version", APP_VERSION == "6.3.34", APP_VERSION)
check("schema_current", SCHEMA_VERSION == "6.3.13", SCHEMA_VERSION)
out = runtime_contract(Settings(deployment_profile="core"))
check("runtime_exposes_adapters", out.get("adapters", {}).get("architecture") == "ports_and_adapters")
check("runtime_dependency_inversion_flag", out.get("governance", {}).get("dependency_inversion") is True)

failed = [x for x in checks if not x[1]]
for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed:
    raise SystemExit(1)
