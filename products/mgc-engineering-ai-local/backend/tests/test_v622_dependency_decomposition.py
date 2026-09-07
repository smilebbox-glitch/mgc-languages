from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION, RuntimeConfigurationError, runtime_contract, validate_build_profile

ROOT = Path(__file__).resolve().parents[2]


def test_v622_is_no_schema_change_patch():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_build_profile_fails_closed_when_runtime_is_wider():
    assert validate_build_profile("core", "core")["compatible"] is True
    assert validate_build_profile("core", "ai")["compatible"] is True
    assert validate_build_profile("ai", "advanced")["compatible"] is True
    with pytest.raises(RuntimeConfigurationError):
        validate_build_profile("ai", "core")
    with pytest.raises(RuntimeConfigurationError):
        runtime_contract(Settings(deployment_profile="advanced", mgc_build_profile="ai"))


def test_context_shared_has_no_eager_service_imports():
    tree = ast.parse((ROOT / "backend/app/api/context_shared.py").read_text())
    eager = [
        n.module for n in tree.body
        if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("app.services.")
    ]
    assert eager == []


def test_registry_does_not_eagerly_import_context_modules():
    tree = ast.parse((ROOT / "backend/app/api/context_registry.py").read_text())
    modules = [n.module for n in tree.body if isinstance(n, ast.ImportFrom) and n.module]
    assert not any(x.startswith("app.api.contexts.") for x in modules)


def test_optional_ai_graph_storage_packages_are_not_top_level_vector_store_imports():
    tree = ast.parse((ROOT / "backend/app/services/vector_store.py").read_text())
    forbidden = {"qdrant_client", "sentence_transformers", "neo4j", "minio"}
    top = set()
    for n in tree.body:
        if isinstance(n, ast.Import):
            top |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            top.add(n.module.split(".")[0])
    assert not (top & forbidden)


def test_dependency_manifests_are_monotonic():
    core = (ROOT / "backend/requirements-core.txt").read_text()
    ai = (ROOT / "backend/requirements-ai.txt").read_text()
    advanced = (ROOT / "backend/requirements-advanced.txt").read_text()
    assert "qdrant-client" not in core and "sentence-transformers" not in core
    assert "neo4j" not in core and "minio" not in core
    assert "-r requirements-core.txt" in ai and "qdrant-client" in ai and "sentence-transformers" in ai
    assert "-r requirements-ai.txt" in advanced and "neo4j" in advanced and "minio" in advanced


def test_docker_build_selects_dependency_profile_from_deployment_profile():
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    assert 'ARG DEPLOYMENT_PROFILE=core' in dockerfile
    assert 'requirements-${DEPLOYMENT_PROFILE}.txt' in dockerfile
    assert 'MGC_BUILD_PROFILE=${DEPLOYMENT_PROFILE}' in dockerfile
    assert 'DEPLOYMENT_PROFILE: ${DEPLOYMENT_PROFILE:-core}' in compose
