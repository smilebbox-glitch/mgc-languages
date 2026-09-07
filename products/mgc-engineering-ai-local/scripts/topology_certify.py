#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PROFILES = {
    "15": {"min_domains": 2, "min_api_domains": 2, "min_worker_domains": 2, "roles": {"interactive", "cpu", "io"}},
    "30": {"min_domains": 2, "min_api_domains": 2, "min_worker_domains": 2, "roles": {"interactive", "cpu", "io"}},
    "100": {"min_domains": 3, "min_api_domains": 3, "min_worker_domains": 2, "roles": {"interactive", "cpu", "io"}},
}

def main() -> int:
    ap=argparse.ArgumentParser(description="Validate MGC multi-host placement policy. This is not a load/performance certification.")
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--profile", choices=sorted(PROFILES), required=True)
    ap.add_argument("--json", action="store_true")
    args=ap.parse_args()
    data=json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    policy=PROFILES[args.profile]
    checks=[]
    def ck(name, ok, detail=None): checks.append({"name":name,"ok":bool(ok),"detail":detail})
    ck("schema", data.get("schema")=="mgc-multihost-topology-v1")
    ck("profile_matches", str(data.get("profile"))==args.profile)
    nodes=data.get("nodes") or []
    ids=[str(n.get("node_id") or "") for n in nodes]
    ck("unique_nonempty_node_ids", all(ids) and all(ids) and len(ids)==len(set(ids)) and all(ids))
    domains={str(n.get("failure_domain") or "") for n in nodes if str(n.get("failure_domain") or "")}
    ck("failure_domain_count", len(domains)>=policy["min_domains"], {"observed":len(domains),"required":policy["min_domains"]})
    api_domains={str(n.get("failure_domain")) for n in nodes if "api" in set(n.get("roles") or [])}
    ck("api_anti_affinity", len(api_domains)>=policy["min_api_domains"], {"observed":len(api_domains),"required":policy["min_api_domains"]})
    for role in sorted(policy["roles"]):
        rd={str(n.get("failure_domain")) for n in nodes if role in set(n.get("roles") or [])}
        ck(f"worker_{role}_anti_affinity", len(rd)>=policy["min_worker_domains"], {"observed":len(rd),"required":policy["min_worker_domains"]})
    lb=data.get("external_load_balancer") or {}
    ck("external_lb_configured", lb.get("configured") is True)
    ck("external_lb_health_contract", lb.get("health_path")=="/api/v1/health/lb")
    ck("external_lb_non_idempotent_retry_disabled", lb.get("non_idempotent_retry_enabled") is False)
    auth=data.get("authoritative_data") or {}
    ck("database_ha_fencing", auth.get("database_ha_fencing") is True)
    ck("evidence_ha_fencing", auth.get("evidence_ha_fencing") is True)
    ok=all(c["ok"] for c in checks)
    out={"schema":"mgc-topology-certification-result-v1","profile":args.profile,"status":"PASS" if ok else "FAIL","production_authorized":False,"performance_certified":False,"checks":checks}
    if args.json: print(json.dumps(out,indent=2,sort_keys=True))
    else:
        for c in checks: print(("PASS" if c["ok"] else "FAIL")+": "+c["name"])
        print(f"{out['status']}: topology profile {args.profile}; placement policy only, not performance certification")
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
