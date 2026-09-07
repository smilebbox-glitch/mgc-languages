#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, platform, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path:Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def docker_id(ref:str):
    try:
        out=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',ref],text=True).strip()
        return out if out.startswith('sha256:') else None
    except Exception: return None

def load_env(path:Path)->dict[str,str]:
    out={}
    if not path.exists(): return out
    for raw in path.read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip().strip('"').strip("'")
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',default='supply-chain/BUILD_ATTESTATION.json')
    ap.add_argument('--cve-report',action='append',default=[])
    ap.add_argument('--builder-id',default=os.getenv('CI_RUNNER_ID') or os.getenv('HOSTNAME') or 'unknown')
    ap.add_argument('--strict',action='store_true')
    args=ap.parse_args()
    bi=ROOT/'supply-chain/BUILD_INPUTS.json'; bs=ROOT/'supply-chain/BUILD_INPUTS.sha256'
    sbom=ROOT/'security-reports/SBOM_v6.3.34.cdx.json'
    if not bi.exists() or not bs.exists(): raise SystemExit('Generate BUILD_INPUTS first')
    artifacts=[]
    for rel in ['frontend/package-lock.json','backend/locks/requirements-core.lock.txt','backend/locks/requirements-ai.lock.txt','backend/locks/requirements-advanced.lock.txt',
                'backend/wheelhouse/core/WHEELHOUSE_MANIFEST.json','backend/wheelhouse/ai/WHEELHOUSE_MANIFEST.json','backend/wheelhouse/advanced/WHEELHOUSE_MANIFEST.json',
                'backend/os-packages/runtime/OS_PACKAGE_MANIFEST.json','backend/os-packages/runtime/OS_PACKAGE_INSTALL_RECEIPT.json']:
        p=ROOT/rel; artifacts.append({'path':rel,'present':p.exists(),'sha256':sha(p) if p.exists() else None})
    reports=[]
    for raw in args.cve_report:
        p=Path(raw).resolve(); reports.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
    build_inputs=json.loads(bi.read_text())
    base_images=build_inputs.get('immutable_images') or {}
    image_refs={k:os.getenv(k,'') for k in ['MGC_API_IMAGE','MGC_FRONTEND_IMAGE','MGC_GATEWAY_IMAGE','MGC_WEBHOOK_IMAGE']}
    env_path=ROOT/os.getenv('MGC_REPRODUCIBLE_ENV_FILE','.env.reproducible')
    env_values=load_env(env_path)
    immutable_keys=['PYTHON_BASE_IMAGE','NODE_BASE_IMAGE','NGINX_BASE_IMAGE','POSTGRES_IMAGE','REDIS_IMAGE','QDRANT_IMAGE','NEO4J_IMAGE','MINIO_IMAGE','VLLM_IMAGE','LLAMA_CPP_IMAGE','OAUTH2_PROXY_IMAGE','PROMETHEUS_IMAGE','GRAFANA_IMAGE','JAEGER_IMAGE']
    container_inputs=[{'key':k,'ref':os.getenv(k) or env_values.get(k,'')} for k in immutable_keys]
    images=[{'key':k,'ref':v,'local_image_id':docker_id(v) if v else None} for k,v in image_refs.items()]
    out={
      'schema':'mgc.build-attestation.v1','release':'6.3.34','created_at':datetime.now(timezone.utc).isoformat(),
      'builder':{'id':args.builder_id,'python':sys.version.split()[0],'platform':platform.platform()},
      'build_inputs':{'path':'supply-chain/BUILD_INPUTS.json','sha256':sha(bi)},
      'sbom':{'path':'security-reports/SBOM_v6.3.34.cdx.json','present':sbom.exists(),'sha256':sha(sbom) if sbom.exists() else None},
      'dependency_artifacts':artifacts,'immutable_base_images':base_images,'container_inputs':container_inputs,'cve_reports':reports,'images':images,
      'production_authorized':False,
      'note':'Evidence record only. Corporate change approval and target-host acceptance remain external.'
    }
    missing=[x['path'] for x in artifacts if not x['present']]
    import re
    bad_inputs=[x['key'] for x in container_inputs if not re.fullmatch(r'.+@sha256:[0-9a-fA-F]{64}',x['ref'] or '')]
    if args.strict and (missing or len(reports)<2 or not sbom.exists() or any(not x['local_image_id'] for x in images) or bad_inputs):
        raise SystemExit('Strict attestation incomplete: missing locks/wheelhouse, CVE report, SBOM, or built image IDs')
    path=ROOT/args.output; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(out,indent=2)+'\n'); print('WROTE',path)
if __name__=='__main__': main()
