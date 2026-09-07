#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.release_acceptance import baseline_from_acceptance, canonical_payload_bytes, attach_integrity, validate_integrity  # noqa:E402
from app.core.release_provenance import register_signed_artifact, ProvenanceError  # noqa:E402


def verify(payload:bytes, signature:Path, public_key:Path)->bool:
    with tempfile.NamedTemporaryFile(prefix='mgc-acceptance-promote-',delete=False) as fh:
        fh.write(payload); temp=Path(fh.name)
    try:
        p=subprocess.run(['openssl','dgst','-sha256','-verify',str(public_key),'-signature',str(signature),str(temp)],capture_output=True,text=True)
        return p.returncode==0
    finally: temp.unlink(missing_ok=True)

def sign(payload:bytes,key:Path,sig:Path)->None:
    with tempfile.NamedTemporaryFile(prefix='mgc-baseline-sign-',delete=False) as fh:
        fh.write(payload); temp=Path(fh.name)
    try:
        p=subprocess.run(['openssl','dgst','-sha256','-sign',str(key),'-out',str(sig),str(temp)],capture_output=True,text=True)
        if p.returncode: raise RuntimeError((p.stderr or p.stdout or 'openssl sign failed').strip())
    finally: temp.unlink(missing_ok=True)

def main()->int:
    ap=argparse.ArgumentParser(description='Promote a signed technical acceptance into an explicitly human-approved baseline.')
    ap.add_argument('--acceptance',required=True); ap.add_argument('--acceptance-signature',required=True); ap.add_argument('--acceptance-public-key',required=True)
    ap.add_argument('--approval-reference',required=True); ap.add_argument('--confirm',required=True,choices=['APPROVE_BASELINE','BOOTSTRAP_APPROVED_BASELINE'])
    ap.add_argument('--output',required=True); ap.add_argument('--signing-key',required=True); ap.add_argument('--signature-output',default='')
    ap.add_argument('--provenance-registry',default=''); ap.add_argument('--provenance-key-id',default='')
    args=ap.parse_args(); acceptance=json.loads(Path(args.acceptance).read_text(encoding='utf-8'))
    ok,_,_=validate_integrity(acceptance)
    if ok is not True or not verify(canonical_payload_bytes(acceptance),Path(args.acceptance_signature),Path(args.acceptance_public_key)):
        print('ERROR: acceptance digest/signature verification failed',file=sys.stderr); return 2
    acceptance.setdefault('integrity',{})['detached_signature_verified']=True
    bootstrap=args.confirm=='BOOTSTRAP_APPROVED_BASELINE'
    try:
        baseline=baseline_from_acceptance(acceptance=acceptance,approval_reference=args.approval_reference,approved_at=datetime.now(timezone.utc).isoformat(),bootstrap=bootstrap)
    except ValueError as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 2
    out=Path(args.output); sig=Path(args.signature_output) if args.signature_output else out.with_suffix(out.suffix+'.sig')
    sign(canonical_payload_bytes(baseline),Path(args.signing_key),sig)
    baseline=attach_integrity(baseline,detached_signature_verified=False,signature_algorithm='openssl-dgst-sha256')
    baseline['integrity']['detached_signature_path_hint']=sig.name
    out.write_text(json.dumps(baseline,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    provenance_sequence=None
    if args.provenance_registry or args.provenance_key_id:
        if not (args.provenance_registry and args.provenance_key_id):
            print('ERROR: provenance registration requires --provenance-registry and --provenance-key-id',file=sys.stderr); return 2
        try:
            event=register_signed_artifact(Path(args.provenance_registry),kind='baseline',document_path=out,signature_path=sig,key_id=args.provenance_key_id,actor='baseline-promotion')
            provenance_sequence=event.get('sequence')
        except ProvenanceError as exc:
            print(f'ERROR: provenance registration failed: {exc}',file=sys.stderr); return 2
    print(json.dumps({'output':str(out),'signature':str(sig),'release':baseline['release'],'bootstrap':bootstrap,'canonical_sha256':baseline['integrity']['canonical_sha256'],'provenance_sequence':provenance_sequence},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
