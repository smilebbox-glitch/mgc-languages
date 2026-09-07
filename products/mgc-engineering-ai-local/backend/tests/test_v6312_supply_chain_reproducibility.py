from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[2]


def test_v6312_app_version_without_db_migration():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"


def test_frontend_direct_dependencies_are_exact_pins():
    data = json.loads((ROOT / "frontend/package.json").read_text())
    for section in ("dependencies", "devDependencies"):
        for spec in data[section].values():
            assert not str(spec).startswith(("^", "~", ">", "<", "*", "http:", "https:", "git+"))


def test_locked_backend_build_path_requires_hashes_and_no_index():
    text = (ROOT / "backend/Dockerfile").read_text()
    assert "PYTHON_DEPENDENCY_MODE" in text
    assert "--require-hashes" in text
    assert "--no-index" in text
    assert "ARG PYTHON_BASE_IMAGE=" in text


def test_locked_frontend_build_path_is_npm_ci_offline():
    text = (ROOT / "frontend/Dockerfile").read_text()
    assert "NPM_DEPENDENCY_MODE" in text
    assert "npm ci --offline" in text
    assert "ARG NODE_BASE_IMAGE=" in text
    assert "ARG NGINX_BASE_IMAGE=" in text


def test_non_strict_preflight_is_conditional_without_fabricated_corporate_locks():
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts/supply_chain_preflight.py"), "--json"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    out = json.loads(p.stdout)
    assert out["production_authorized"] is False
    assert out["status"] in {"CONDITIONAL", "READY"}


def test_strict_preflight_fails_closed_until_approved_artifacts_exist():
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts/supply_chain_preflight.py"), "--strict"],
        cwd=ROOT, text=True, capture_output=True,
    )
    # Source release intentionally does not fabricate corporate registry locks/digests.
    assert p.returncode != 0


def test_reproducible_overlay_forces_locked_dependency_modes():
    text = (ROOT / "docker-compose.reproducible.yml").read_text()
    assert "PYTHON_DEPENDENCY_MODE: locked" in text
    assert "NPM_DEPENDENCY_MODE: locked" in text
    assert "PYTHON_BASE_IMAGE" in text and "NODE_BASE_IMAGE" in text and "NGINX_BASE_IMAGE" in text


def test_strict_backend_uses_offline_os_package_bundle():
    text = (ROOT / "backend/Dockerfile").read_text()
    overlay = (ROOT / "docker-compose.reproducible.yml").read_text()
    assert "OS_DEPENDENCY_MODE" in text
    assert "verify_os_package_bundle.py" in text
    assert "dpkg -i" in text
    assert '--expected-base-image "$PYTHON_BASE_IMAGE"' in text
    assert "OS_DEPENDENCY_MODE: bundle" in overlay
    assert "network: none" in overlay


def test_os_bundle_preparation_requires_immutable_base_image():
    text = (ROOT / "scripts/prepare_os_package_bundle.sh").read_text()
    assert "@sha256:" in text
    assert "OS_PACKAGE_MANIFEST.json" in text
    assert "apt-get install -y --download-only" in text


def test_os_package_bundle_verifier_binds_hashes_and_base_image(tmp_path):
    import hashlib
    bundle = tmp_path / "runtime"
    bundle.mkdir()
    deb = bundle / "libexample_1.0_amd64.deb"
    deb.write_bytes(b"synthetic-test-deb")
    digest = hashlib.sha256(deb.read_bytes()).hexdigest()
    manifest = {
        "schema": "mgc.os-package-bundle.v1",
        "release": "6.3.24",
        "base_image": "registry.example/python@sha256:" + "a" * 64,
        "files": [{"name": deb.name, "sha256": digest, "bytes": deb.stat().st_size}],
    }
    (bundle / "OS_PACKAGE_MANIFEST.json").write_text(json.dumps(manifest))
    script = ROOT / "backend/verify_os_package_bundle.py"
    ok = subprocess.run(
        [sys.executable, str(script), str(bundle), "--expected-base-image", manifest["base_image"]],
        text=True, capture_output=True,
    )
    assert ok.returncode == 0
    bad = subprocess.run(
        [sys.executable, str(script), str(bundle), "--expected-base-image", "registry.example/python@sha256:" + "b" * 64],
        text=True, capture_output=True,
    )
    assert bad.returncode != 0


def test_strict_compose_disables_network_and_requires_os_bundle():
    text = (ROOT / "docker-compose.reproducible.yml").read_text()
    assert "network: none" in text
    assert "OS_DEPENDENCY_MODE: bundle" in text


def test_os_bundle_verifier_requires_offline_install_receipt_when_requested(tmp_path):
    import hashlib
    bundle = tmp_path / "runtime"
    bundle.mkdir()
    deb = bundle / "libexample_1.0_amd64.deb"
    deb.write_bytes(b"synthetic-test-deb")
    digest = hashlib.sha256(deb.read_bytes()).hexdigest()
    base = "registry.example/python@sha256:" + "c" * 64
    manifest = {
        "schema": "mgc.os-package-bundle.v1",
        "release": "6.3.24",
        "base_image": base,
        "files": [{"name": deb.name, "sha256": digest, "bytes": deb.stat().st_size}],
    }
    manifest_path = bundle / "OS_PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest))
    script = ROOT / "backend/verify_os_package_bundle.py"
    missing = subprocess.run(
        [sys.executable, str(script), str(bundle), "--expected-base-image", base, "--require-install-receipt"],
        text=True, capture_output=True,
    )
    assert missing.returncode != 0
    receipt = {
        "schema": "mgc.os-package-install-receipt.v1",
        "release": "6.3.24",
        "base_image": base,
        "base_image_local_id": "sha256:" + "d" * 64,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "package_count": 1,
        "network_mode": "none",
        "installer": "dpkg -i",
        "result": "pass",
    }
    (bundle / "OS_PACKAGE_INSTALL_RECEIPT.json").write_text(json.dumps(receipt))
    ok = subprocess.run(
        [sys.executable, str(script), str(bundle), "--expected-base-image", base, "--require-install-receipt"],
        text=True, capture_output=True,
    )
    assert ok.returncode == 0
    receipt["manifest_sha256"] = "0" * 64
    (bundle / "OS_PACKAGE_INSTALL_RECEIPT.json").write_text(json.dumps(receipt))
    stale = subprocess.run(
        [sys.executable, str(script), str(bundle), "--expected-base-image", base, "--require-install-receipt"],
        text=True, capture_output=True,
    )
    assert stale.returncode != 0


def test_os_bundle_preparation_proves_offline_install_before_acceptance():
    prepare = (ROOT / "scripts/prepare_os_package_bundle.sh").read_text()
    verify = (ROOT / "scripts/verify_os_package_install.sh").read_text()
    assert "verify_os_package_install.sh" in prepare
    assert "--network none" in verify
    assert "OS_PACKAGE_INSTALL_RECEIPT.json" in verify
    assert "dpkg --audit" in verify
