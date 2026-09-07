#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIGEST_RE=re.compile(r'@sha256:[0-9a-fA-F]{64}$')
RANGE_RE=re.compile(r'(^|[^=!<>~])(?:>=|<=|~=|>|<|\^|~|\*)')
IMAGE_KEYS=['PYTHON_BASE_IMAGE','NODE_BASE_IMAGE','NGINX_BASE_IMAGE','POSTGRES_IMAGE','REDIS_IMAGE','QDRANT_IMAGE','NEO4J_IMAGE','MINIO_IMAGE','VLLM_IMAGE','LLAMA_CPP_IMAGE','OAUTH2_PROXY_IMAGE','PROMETHEUS_IMAGE','GRAFANA_IMAGE','JAEGER_IMAGE']

def load_env(path:Path)->dict[str,str]:
    out={}
    if not path.exists(): return out
    for raw in path.read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip().strip('"').strip("'")
    return out

def exact_frontend_deps()->tuple[bool,list[str]]:
    p=ROOT/'frontend/package.json'; data=json.loads(p.read_text())
    bad=[]
    for section in ('dependencies','devDependencies'):
        for name,spec in (data.get(section) or {}).items():
            if RANGE_RE.search(str(spec)) or str(spec).startswith(('git+','http:','https:','file:')):
                bad.append(f'{section}:{name}={spec}')
    return not bad,bad

def lock_is_hashed(path:Path)->tuple[bool,str]:
    if not path.exists() or path.stat().st_size==0: return False,'missing'
    text=path.read_text(encoding='utf-8')
    rows=[]; buf=''
    for raw in text.splitlines():
        line=raw.strip()
        if not line or line.startswith('#'): continue
        buf += (' '+line if buf else line)
        if line.endswith('\\'):
            buf=buf[:-1].rstrip(); continue
        rows.append(buf); buf=''
    if buf: rows.append(buf)
    if not rows: return False,'empty'
    for row in rows:
        if '==' not in row or '--hash=sha256:' not in row:
            return False,f'unhashed/non-exact row: {row[:120]}'
    return True,f'{len(rows)} exact hashed requirements'

def wheelhouse_ok(profile:str)->tuple[bool,str]:
    d=ROOT/f'backend/wheelhouse/{profile}'; m=d/'WHEELHOUSE_MANIFEST.json'
    if not m.exists(): return False,'manifest missing'
    try: data=json.loads(m.read_text())
    except Exception as e: return False,f'invalid manifest: {e}'
    files=data.get('files') or []
    if not files: return False,'no wheels in manifest'
    for item in files:
        f=d/item['name']
        if not f.is_file(): return False,f'missing wheel {f.name}'
        h=hashlib.sha256(f.read_bytes()).hexdigest()
        if h!=item.get('sha256'): return False,f'hash mismatch {f.name}'
    return True,f'{len(files)} wheels verified'

def os_bundle_ok(expected_base:str="")->tuple[bool,str]:
    d=ROOT/'backend/os-packages/runtime'; m=d/'OS_PACKAGE_MANIFEST.json'
    if not m.exists(): return False,'OS package manifest missing'
    try: data=json.loads(m.read_text())
    except Exception as e: return False,f'invalid OS package manifest: {e}'
    if expected_base and data.get('base_image') != expected_base: return False,f'base image mismatch: manifest={data.get("base_image")}'
    files=data.get('files') or []
    if not files: return False,'no OS packages in manifest'
    expected=set()
    for item in files:
        name=item.get('name',''); expected.add(name); f=d/name
        if not name.endswith('.deb') or not f.is_file(): return False,f'missing/invalid OS package {name}'
        if hashlib.sha256(f.read_bytes()).hexdigest()!=item.get('sha256'): return False,f'OS package hash mismatch {name}'
        if item.get('bytes') is not None and f.stat().st_size != int(item['bytes']): return False,f'OS package size mismatch {name}'
    extra={p.name for p in d.glob('*.deb')}-expected
    if extra: return False,'unmanifested OS packages: '+','.join(sorted(extra))
    return True,f'{len(files)} OS packages verified'

def os_install_receipt_ok(expected_base:str="")->tuple[bool,str]:
    d=ROOT/'backend/os-packages/runtime'; m=d/'OS_PACKAGE_MANIFEST.json'; r=d/'OS_PACKAGE_INSTALL_RECEIPT.json'
    if not m.exists(): return False,'OS package manifest missing'
    if not r.exists(): return False,'offline OS install receipt missing'
    try:
        manifest=json.loads(m.read_text()); receipt=json.loads(r.read_text())
    except Exception as e: return False,f'invalid OS install evidence: {e}'
    if receipt.get('schema')!='mgc.os-package-install-receipt.v1': return False,'unsupported install receipt schema'
    if receipt.get('result')!='pass' or receipt.get('network_mode')!='none': return False,'offline install receipt is not PASS/network=none'
    if receipt.get('base_image')!=manifest.get('base_image'): return False,'install receipt base image mismatch'
    if expected_base and receipt.get('base_image')!=expected_base: return False,'install receipt does not match PYTHON_BASE_IMAGE'
    if receipt.get('manifest_sha256')!=hashlib.sha256(m.read_bytes()).hexdigest(): return False,'install receipt manifest hash mismatch'
    if int(receipt.get('package_count',-1))!=len(manifest.get('files') or []): return False,'install receipt package count mismatch'
    return True,'offline dpkg install verified with network disabled'

def package_lock_ok()->tuple[bool,str]:
    p=ROOT/'frontend/package-lock.json'
    if not p.exists(): return False,'package-lock.json missing'
    try: d=json.loads(p.read_text())
    except Exception as e: return False,f'invalid package-lock.json: {e}'
    if int(d.get('lockfileVersion',0)) < 3: return False,'lockfileVersion < 3'
    packages=d.get('packages') or {}
    missing=[]
    for key,val in packages.items():
        if key=='': continue
        if not val.get('version'): missing.append(key+':version')
        # Registry packages need integrity. Links/local packages may legitimately differ.
        if not val.get('link') and not val.get('integrity'): missing.append(key+':integrity')
    if missing: return False,'missing fields: '+', '.join(missing[:5])
    return True,f'lockfileVersion={d.get("lockfileVersion")}, packages={len(packages)}'

def npm_cache_ok()->tuple[bool,str]:
    d=ROOT/'frontend/npm-cache/_cacache'
    return (d.is_dir(), 'offline cache present' if d.is_dir() else 'offline npm cache missing')

def image_env_ok(path:Path)->tuple[bool,str]:
    env=load_env(path); bad=[]
    for k in IMAGE_KEYS:
        v=os.getenv(k) or env.get(k,'')
        if not v or 'REPLACE_' in v or not DIGEST_RE.search(v): bad.append(k)
    return not bad, ('all required images use immutable digests' if not bad else 'unresolved/not-digest: '+','.join(bad))

def build_inputs_ok()->tuple[bool,str]:
    p=ROOT/'supply-chain/BUILD_INPUTS.json'; side=ROOT/'supply-chain/BUILD_INPUTS.sha256'
    if not p.exists() or not side.exists(): return False,'BUILD_INPUTS manifest/sidecar missing'
    try: data=json.loads(p.read_text())
    except Exception as e: return False,f'invalid BUILD_INPUTS: {e}'
    expected=side.read_text().split()[0].strip(); actual=hashlib.sha256(p.read_bytes()).hexdigest()
    if actual!=expected: return False,'BUILD_INPUTS sidecar hash mismatch'
    for item in data.get('files') or []:
        fp=ROOT/item['path']; present=fp.exists()
        if present != bool(item.get('present')): return False,f'presence drift: {item["path"]}'
        if present and hashlib.sha256(fp.read_bytes()).hexdigest()!=item.get('sha256'): return False,f'hash drift: {item["path"]}'
    return True,f'{len(data.get("files") or [])} build inputs verified'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--strict',action='store_true'); ap.add_argument('--json',action='store_true'); ap.add_argument('--env',default='.env.reproducible'); args=ap.parse_args()
    strict=args.strict or os.getenv('MGC_REQUIRE_REPRODUCIBLE_BUILD','false').lower()=='true'
    checks=[]
    def add(name,ok,detail,required=True): checks.append({'name':name,'ok':bool(ok),'detail':detail,'required':required})
    ok,bad=exact_frontend_deps(); add('frontend direct dependency specs exact',ok, 'exact pins' if ok else '; '.join(bad))
    ok,detail=package_lock_ok(); add('frontend package-lock',ok,detail)
    ok,detail=npm_cache_ok(); add('frontend offline npm cache',ok,detail)
    for profile in ('core','ai','advanced'):
        ok,detail=lock_is_hashed(ROOT/f'backend/locks/requirements-{profile}.lock.txt'); add(f'python {profile} hashed lock',ok,detail)
        ok,detail=wheelhouse_ok(profile); add(f'python {profile} wheelhouse',ok,detail)
    env_values=load_env(ROOT/args.env)
    ok,detail=image_env_ok(ROOT/args.env); add('immutable container/base image digests',ok,detail)
    expected_python_base=os.getenv('PYTHON_BASE_IMAGE') or env_values.get('PYTHON_BASE_IMAGE','')
    ok,detail=os_bundle_ok(expected_python_base); add('offline OS package bundle',ok,detail)
    ok,detail=os_install_receipt_ok(expected_python_base); add('offline OS package install receipt',ok,detail)
    ok,detail=build_inputs_ok(); add('build input provenance manifest',ok,detail)
    # Structural safeguards are always expected in source.
    b=(ROOT/'backend/Dockerfile').read_text(); f=(ROOT/'frontend/Dockerfile').read_text()
    add('backend locked/offline install path', '--require-hashes' in b and 'PYTHON_DEPENDENCY_MODE' in b and '--no-index' in b and 'OS_DEPENDENCY_MODE' in b and 'verify_os_package_bundle.py' in b, 'locked mode uses hashed wheels + verified offline OS bundle')
    add('frontend locked/offline install path', 'npm ci --offline' in f and 'NPM_DEPENDENCY_MODE' in f, 'locked mode uses npm ci --offline')
    overlay=(ROOT/'docker-compose.reproducible.yml').read_text() if (ROOT/'docker-compose.reproducible.yml').exists() else ''
    add('reproducible compose overlay', bool(overlay) and 'network: none' in overlay and 'OS_DEPENDENCY_MODE: bundle' in overlay, 'offline build network disabled + OS bundle enforced')
    required_fail=[c for c in checks if c['required'] and not c['ok']]
    status='READY' if not required_fail else 'CONDITIONAL'
    result={'release':'6.3.34','strict':strict,'status':status,'production_authorized':False,'checks':checks}
    if args.json: print(json.dumps(result,indent=2))
    else:
        print(f'Supply-chain reproducibility: {status}')
        for c in checks: print(('PASS' if c['ok'] else ('FAIL' if strict else 'WARN')), c['name'], '-', c['detail'])
        print('production_authorized=false (corporate build approval remains external)')
    if strict and required_fail: raise SystemExit(2)
if __name__=='__main__': main()
