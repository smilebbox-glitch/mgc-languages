#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

SCENARIOS = [
    {"code":"RD-CHANGE-IMPACT","role":"rd","domain":"change","required":True,"expected":"impact path + evidence"},
    {"code":"RD-BOM-DIFF","role":"rd","domain":"configuration","required":True,"expected":"deterministic BOM diff"},
    {"code":"MFG-BUILDABILITY","role":"manufacturing","domain":"manufacturing","required":True,"expected":"buildability blockers"},
    {"code":"MFG-CUT-IN","role":"manufacturing","domain":"configuration","required":True,"expected":"cut-in/effectivity trace"},
    {"code":"QUALITY-DEFECT-TRACE","role":"quality","domain":"quality","required":True,"expected":"VIN→part→supplier→defect trace"},
    {"code":"QUALITY-CONTAINMENT","role":"quality","domain":"quality","required":True,"expected":"suspect population + containment"},
]

def dataset():
    parts=[]
    for i in range(1,61):
        parts.append({"part_number":f"P-{i:04d}","revision":"D" if i%7==0 else "C","supplier":f"SUP-{(i%4)+1:02d}","critical":i in {7,14,21,35}})
    bom=[]
    for i in range(2,61):
        bom.append({"parent":"P-0001" if i < 20 else f"P-{((i-2)//10)*10+10:04d}","child":f"P-{i:04d}","qty":2 if i%9==0 else 1})
    vins=[]
    for i in range(1,25):
        vins.append({"vin":f"MGC-PILOT-{i:05d}","variant":"Premium" if i%3==0 else "Comfort","build":"PB-02" if i>12 else "PB-01"})
    defects=[
        {"code":"D-WELD-01","vin":"MGC-PILOT-00003","part":"P-0014","supplier":"SUP-03","severity":"high"},
        {"code":"D-FIT-02","vin":"MGC-PILOT-00009","part":"P-0021","supplier":"SUP-02","severity":"medium"},
        {"code":"D-WELD-01","vin":"MGC-PILOT-00015","part":"P-0014","supplier":"SUP-03","severity":"high"},
    ]
    return {
        "schema":"mgc-golden-automotive-dataset-v1",
        "synthetic_only":True,
        "authorizes_production_go":False,
        "project":{"code":"GOLDEN-X1","name":"Synthetic Automotive UAT Vehicle"},
        "counts":{"parts":len(parts),"bom_edges":len(bom),"vehicles":len(vins),"defects":len(defects)},
        "parts":parts,"bom":bom,"vehicles":vins,"defects":defects,"scenarios":SCENARIOS,
        "expected_assertions":{
            "repeated_defect":{"code":"D-WELD-01","count":2,"part":"P-0014","supplier":"SUP-03"},
            "critical_part":"P-0014",
            "required_roles":["rd","manufacturing","quality"],
        },
        "privacy":{"real_people":False,"real_vins":False,"customer_data":False,"employee_tracking":False},
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default='pilot/golden_dataset_v1.json'); args=ap.parse_args()
    payload=dataset(); raw=(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest()
    print(json.dumps({"output":str(out),"sha256":digest,"counts":payload["counts"],"synthetic_only":True},indent=2))
if __name__=='__main__': main()
