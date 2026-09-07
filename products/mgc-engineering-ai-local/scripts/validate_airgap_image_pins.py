from __future__ import annotations
import argparse, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=['MGC_API_IMAGE','MGC_FRONTEND_IMAGE','MGC_GATEWAY_IMAGE','MGC_WEBHOOK_IMAGE','POSTGRES_IMAGE','QDRANT_IMAGE','REDIS_IMAGE','NEO4J_IMAGE','MINIO_IMAGE','OAUTH2_PROXY_IMAGE']

def load_env(path: Path) -> dict[str,str]:
    out={}
    if not path.exists(): return out
    for raw in path.read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip().strip('"').strip("'")
    return out

ap=argparse.ArgumentParser(); ap.add_argument('--runtime',choices=['cpu','gpu'],required=True); args=ap.parse_args()
required=BASE+(['LLAMA_CPP_IMAGE'] if args.runtime=='cpu' else ['VLLM_IMAGE'])
values=load_env(ROOT/'.env'); errors=[]
for key in required:
    value=os.getenv(key) or values.get(key,'')
    if not value: errors.append(f'{key}: not configured in environment/.env'); continue
    low=value.lower()
    if ':latest' in low or low.endswith('/latest'): errors.append(f'{key}: floating latest tag is not allowed: {value}')
    if os.getenv('MGC_REQUIRE_REPRODUCIBLE_BUILD','false').lower()=='true' and not __import__('re').search(r'@sha256:[0-9a-fA-F]{64}$', value): errors.append(f'{key}: strict reproducible mode requires repo@sha256 digest: {value}')
    if 'replace_with_' in low or 'replace_with_approved' in low: errors.append(f'{key}: replace placeholder with an IT-approved pinned tag/digest: {value}')
print(f'Air-gap image pinning ({args.runtime})')
if errors:
    for e in errors: print('FAIL',e)
    raise SystemExit(1)
for key in required: print('PASS',key,'=',os.getenv(key) or values.get(key,''))
