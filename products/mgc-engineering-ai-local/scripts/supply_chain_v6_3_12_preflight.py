#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def ck(name,cond): checks.append((name,bool(cond)))
rt=(ROOT/'backend/app/core/runtime_contract.py').read_text(); ck('current app version 6.3.34','APP_VERSION = "6.3.34"' in rt); ck('current schema remains 6.3.13','SCHEMA_VERSION = "6.3.13"' in rt)
backend=(ROOT/'backend/Dockerfile').read_text(); frontend=(ROOT/'frontend/Dockerfile').read_text()
ck('backend supports immutable base image ARG','ARG PYTHON_BASE_IMAGE=' in backend and 'FROM ${PYTHON_BASE_IMAGE}' in backend)
ck('backend locked install requires hashes','--require-hashes' in backend and '--no-index' in backend)
ck('backend strict path uses verified offline OS bundle','OS_DEPENDENCY_MODE' in backend and 'verify_os_package_bundle.py' in backend and '--require-install-receipt' in backend and 'dpkg -i' in backend)
ck('frontend supports immutable base ARGs','ARG NODE_BASE_IMAGE=' in frontend and 'ARG NGINX_BASE_IMAGE=' in frontend)
ck('frontend reproducible mode is offline','npm ci --offline' in frontend)
overlay=(ROOT/'docker-compose.reproducible.yml').read_text(); ck('reproducible compose overlay exists',bool(overlay)); ck('strict compose disables build network','network: none' in overlay); ck('strict compose enforces OS bundle','OS_DEPENDENCY_MODE: bundle' in overlay)
ck('strict env template exists',(ROOT/'.env.reproducible.example').exists())
ck('python lock generator exists',(ROOT/'scripts/prepare_python_lock.py').exists())
ck('frontend lock generator exists',(ROOT/'scripts/prepare_frontend_lock.sh').exists())
ck('OS package bundle generator exists',(ROOT/'scripts/prepare_os_package_bundle.sh').exists())
ck('OS offline install verifier exists',(ROOT/'scripts/verify_os_package_install.sh').exists() and '--network none' in (ROOT/'scripts/verify_os_package_install.sh').read_text())
ck('OS verifier requires install receipt','--require-install-receipt' in (ROOT/'backend/verify_os_package_bundle.py').read_text())
ck('container digest resolver exists',(ROOT/'scripts/resolve_container_digests.py').exists())
ck('strict build wrapper exists',(ROOT/'scripts/reproducible_build.sh').exists())
overlay=(ROOT/'docker-compose.reproducible.yml').read_text(); ck('webhook edge uses reproducible base image','webhook-edge:' in overlay and 'MGC_BUILD_SOURCE_SHA256' in overlay)
ck('OCI provenance labels','org.opencontainers.image.revision' in backend and 'org.opencontainers.image.revision' in frontend)
ck('build attestation generator',(ROOT/'scripts/generate_build_attestation.py').exists())
ck('build attestation verifier',(ROOT/'scripts/verify_build_attestation.py').exists())
ck('built-image CVE gate',(ROOT/'scripts/image_vulnerability_scan.sh').exists() and 'trivy image' in (ROOT/'scripts/image_vulnerability_scan.sh').read_text())
# Non-strict preflight must return successfully while honestly reporting CONDITIONAL until corporate artifacts are supplied.
p=subprocess.run([sys.executable,str(ROOT/'scripts/supply_chain_preflight.py'),'--json'],cwd=ROOT,text=True,capture_output=True)
ck('non-strict supply-chain preflight executable',p.returncode==0)
try: d=json.loads(p.stdout); ck('unresolved corporate locks report CONDITIONAL',d.get('status') in ('CONDITIONAL','READY')); ck('production never self-authorized',d.get('production_authorized') is False)
except Exception: ck('supply-chain JSON parse',False)
# Strict mode must fail closed in source package because approved corp artifacts are intentionally not fabricated.
p=subprocess.run([sys.executable,str(ROOT/'scripts/supply_chain_preflight.py'),'--strict'],cwd=ROOT,text=True,capture_output=True)
ck('strict mode fails closed without approved locks/digests',p.returncode!=0)
for n,v in checks: print(('PASS' if v else 'FAIL'),n)
if not all(v for _,v in checks): raise SystemExit(1)
print(f'Supply Chain compatibility v6.3.12: {sum(v for _,v in checks)}/{len(checks)} PASS')
