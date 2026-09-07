#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('path',nargs='?',default='supply-chain/BUILD_ATTESTATION.json'); ap.add_argument('--strict',action='store_true'); args=ap.parse_args()
    p=(ROOT/args.path).resolve() if not Path(args.path).is_absolute() else Path(args.path)
    d=json.loads(p.read_text()); errors=[]
    if d.get('schema')!='mgc.build-attestation.v1': errors.append('schema')
    bi=d.get('build_inputs') or {}; bip=ROOT/bi.get('path','')
    if not bip.is_file() or sha(bip)!=bi.get('sha256'): errors.append('build_inputs_hash')
    sb=d.get('sbom') or {}
    if sb.get('present'):
        sp=ROOT/sb.get('path','');
        if not sp.is_file() or sha(sp)!=sb.get('sha256'): errors.append('sbom_hash')
    for item in d.get('dependency_artifacts') or []:
        if not item.get('present'): errors.append('missing:'+item.get('path','?')); continue
        fp=ROOT/item['path']
        if not fp.is_file() or sha(fp)!=item.get('sha256'): errors.append('dep_hash:'+item['path'])
    for key,ref in (d.get('immutable_base_images') or {}).items():
        if not re.fullmatch(r'.+@sha256:[0-9a-f]{64}',ref or ''): errors.append('base_image:'+key)
    for item in d.get('cve_reports') or []:
        rp=Path(item['path']); rp=rp if rp.is_absolute() else ROOT/rp
        if not rp.is_file() or sha(rp)!=item.get('sha256'): errors.append('cve_hash:'+item['path'])
    for ci in d.get('container_inputs') or []:
        if not re.fullmatch(r'.+@sha256:[0-9a-fA-F]{64}',ci.get('ref') or ''): errors.append('container_input:'+ci.get('key','?'))
    for image in d.get('images') or []:
        if not re.fullmatch(r'sha256:[0-9a-f]{64}',image.get('local_image_id') or ''): errors.append('image_id:'+image.get('key','?'))
    if d.get('production_authorized') is not False: errors.append('self_authorization_forbidden')
    if errors:
        print('FAIL build attestation:', ', '.join(errors)); raise SystemExit(2 if args.strict else 1)
    print('PASS build attestation evidence integrity; production_authorized=false')
if __name__=='__main__': main()
