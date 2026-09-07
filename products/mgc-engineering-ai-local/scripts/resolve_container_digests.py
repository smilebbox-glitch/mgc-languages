#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULTS={
'PYTHON_BASE_IMAGE':'python:3.12-slim-bookworm','NODE_BASE_IMAGE':'node:22-alpine','NGINX_BASE_IMAGE':'nginx:1.27-alpine',
'POSTGRES_IMAGE':'postgres:16','REDIS_IMAGE':'redis:7-alpine','QDRANT_IMAGE':'qdrant/qdrant:latest','NEO4J_IMAGE':'neo4j:5-community','MINIO_IMAGE':'minio/minio:latest',
'VLLM_IMAGE':'vllm/vllm-openai:latest','LLAMA_CPP_IMAGE':'ghcr.io/ggerganov/llama.cpp:server','OAUTH2_PROXY_IMAGE':'quay.io/oauth2-proxy/oauth2-proxy:latest',
'PROMETHEUS_IMAGE':'prom/prometheus:latest','GRAFANA_IMAGE':'grafana/grafana:latest','JAEGER_IMAGE':'jaegertracing/all-in-one:latest'}

def inspect(ref:str)->str:
    subprocess.run(['docker','pull',ref],check=True)
    out=subprocess.check_output(['docker','image','inspect','--format','{{json .RepoDigests}}',ref],text=True).strip()
    import json
    vals=json.loads(out)
    if not vals: raise RuntimeError(f'No RepoDigest for {ref}')
    # Prefer digest for the same repository name when possible.
    repo=ref.split('@')[0].rsplit(':',1)[0] if '/' in ref or ':' in ref else ref
    return next((x for x in vals if x.split('@')[0]==repo),vals[0])

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default='.env.reproducible'); ap.add_argument('--no-pull',action='store_true'); args=ap.parse_args()
    lines=['MGC_REQUIRE_REPRODUCIBLE_BUILD=true','MGC_REQUIRE_CVE_SCANNER=true']
    for key,ref in DEFAULTS.items():
        if args.no_pull:
            import json
            vals=json.loads(subprocess.check_output(['docker','image','inspect','--format','{{json .RepoDigests}}',ref],text=True)); resolved=vals[0]
        else: resolved=inspect(ref)
        if not re.search(r'@sha256:[0-9a-f]{64}$',resolved): raise RuntimeError(f'Non-immutable result for {key}: {resolved}')
        lines.append(f'{key}={resolved}')
    path=ROOT/args.output; path.write_text('\n'.join(lines)+'\n'); print('WROTE',path)
if __name__=='__main__': main()
