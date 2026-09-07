#!/usr/bin/env python3
"""v6.2.2 dependency-envelope and lazy-import verification."""
from __future__ import annotations

import ast
import importlib.abc
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

checks = []
def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))

# Static dependency-envelope checks.
core = (ROOT / "backend/requirements-core.txt").read_text()
ai = (ROOT / "backend/requirements-ai.txt").read_text()
advanced = (ROOT / "backend/requirements-advanced.txt").read_text()
check("core_has_no_qdrant", "qdrant-client" not in core)
check("core_has_no_sentence_transformers", "sentence-transformers" not in core)
check("core_has_no_neo4j", "neo4j" not in core)
check("core_has_no_minio", "minio" not in core)
check("ai_extends_core", "-r requirements-core.txt" in ai)
check("ai_semantic_deps", "qdrant-client" in ai and "sentence-transformers" in ai)
check("advanced_extends_ai", "-r requirements-ai.txt" in advanced)
check("advanced_projection_deps", "neo4j" in advanced and "minio" in advanced)

shared_tree = ast.parse((ROOT / "backend/app/api/context_shared.py").read_text())
shared_services = [n.module for n in shared_tree.body if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("app.services.")]
check("shared_no_eager_services", not shared_services, str(shared_services))

registry_tree = ast.parse((ROOT / "backend/app/api/context_registry.py").read_text())
context_imports = [n.module for n in registry_tree.body if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("app.api.contexts.")]
check("registry_lazy_context_import", not context_imports, str(context_imports))

vector_tree = ast.parse((ROOT / "backend/app/services/vector_store.py").read_text())
forbidden = {"qdrant_client", "sentence_transformers", "neo4j", "minio"}
top = set()
for n in vector_tree.body:
    if isinstance(n, ast.Import): top |= {a.name.split('.')[0] for a in n.names}
    elif isinstance(n, ast.ImportFrom) and n.module: top.add(n.module.split('.')[0])
check("vector_store_optional_imports_lazy", not (top & forbidden), str(sorted(top & forbidden)))

dockerfile=(ROOT/'backend/Dockerfile').read_text()
check("docker_profile_arg", 'ARG DEPLOYMENT_PROFILE=core' in dockerfile)
check("docker_profile_requirements", 'requirements-${DEPLOYMENT_PROFILE}.txt' in dockerfile)
check("docker_bakes_build_profile", 'MGC_BUILD_PROFILE=${DEPLOYMENT_PROFILE}' in dockerfile)
compose=(ROOT/'docker-compose.yml').read_text()
check("compose_build_profile_arg", compose.count('DEPLOYMENT_PROFILE: ${DEPLOYMENT_PROFILE:-core}') >= 4)

# Runtime contract fail-closed check.
from app.core.runtime_contract import RuntimeConfigurationError, validate_build_profile
check("core_image_core_runtime", validate_build_profile("core", "core")["compatible"])
try:
    validate_build_profile("ai", "core")
    blocked=False
except RuntimeConfigurationError:
    blocked=True
check("core_image_rejects_ai_runtime", blocked)

# Import the most AI-sensitive route while hard-blocking optional third-party packages.
BLOCK={"qdrant_client","sentence_transformers","neo4j","minio"}
class Blocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCK:
            raise ImportError(f"blocked optional package during Core import: {fullname}")
        return None
sys.meta_path.insert(0, Blocker())
try:
    import app.services.vector_store  # noqa
    import app.api.contexts.intelligence_search  # noqa
    imported=[x for x in sys.modules if x.split('.')[0] in BLOCK]
    check("core_sensitive_import_without_optional_packages", not imported, str(imported))
except Exception as exc:
    check("core_sensitive_import_without_optional_packages", False, repr(exc))

failed=[x for x in checks if not x[1]]
for name,ok,detail in checks:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f" — {detail}" if detail else ""))
print(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
