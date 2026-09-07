#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'backend'))
from app.core.release_acceptance import RELEASE_ACCEPTANCE_SCHEMA,canonical_payload_bytes,validate_integrity  # noqa:E402

def verify(doc:dict,sig:Path,key:Path)->bool:
    with tempfile.NamedTemporaryFile(prefix='mgc-chain-',delete=False) as fh: fh.write(canonical_payload_bytes(doc)); temp=Path(fh.name)
    try:
        p=subprocess.run(['openssl','dgst','-sha256','-verify',str(key),'-signature',str(sig),str(temp)],capture_output=True,text=True); return p.returncode==0
    finally: temp.unlink(missing_ok=True)
def main()->int:
    ap=argparse.ArgumentParser(description='Verify ordered signed MGC release acceptance evidence chain.')
    ap.add_argument('--public-key',required=True); ap.add_argument('acceptance',nargs='+',help='Acceptance JSON files in chain order; each requires sibling .sig')
    args=ap.parse_args(); prev=None; expected_seq=1; rows=[]
    for raw in args.acceptance:
        p=Path(raw); doc=json.loads(p.read_text(encoding='utf-8')); sig=Path(str(p)+'.sig')
        ok,_,actual=validate_integrity(doc); chain=doc.get('chain') or {}; reasons=[]
        if doc.get('schema')!=RELEASE_ACCEPTANCE_SCHEMA: reasons.append('schema')
        if ok is not True: reasons.append('digest')
        if not sig.exists() or not verify(doc,sig,Path(args.public_key)): reasons.append('signature')
        if int(chain.get('sequence') or 0)!=expected_seq: reasons.append('sequence')
        if chain.get('parent_acceptance_sha256')!=prev: reasons.append('parent')
        rows.append({'file':str(p),'release':doc.get('release'),'sequence':chain.get('sequence'),'sha256':actual,'status':'PASS' if not reasons else 'FAIL','reasons':reasons})
        if reasons: print(json.dumps({'status':'FAIL','entries':rows},indent=2)); return 2
        prev=actual; expected_seq+=1
    print(json.dumps({'status':'PASS','entries':rows,'tip_sha256':prev},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
