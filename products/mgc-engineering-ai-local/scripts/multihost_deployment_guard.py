#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description='Fail-closed guard before multi-host rollout/cutover.')
    ap.add_argument('--snapshot', required=True, help='JSON from GET /api/v1/operations/multi-host-topology')
    args=ap.parse_args()
    data=json.loads(Path(args.snapshot).read_text(encoding='utf-8'))
    checks={
      'enabled': data.get('enabled') is True,
      'registry_available': data.get('registry_status') == 'available',
      'healthy': data.get('status') == 'HEALTHY',
      'topology_ready': data.get('topology_ready') is True,
      'no_identity_conflicts': not bool(data.get('node_identity_conflicts')),
      'no_worker_domain_gaps': not bool(data.get('worker_failure_domain_gaps')),
      'labels_complete': int(data.get('unlabeled_active_components') or 0) == 0,
    }
    for name,ok in checks.items(): print(('PASS' if ok else 'FAIL')+': '+name)
    if not all(checks.values()): raise SystemExit('Multi-host deployment guard failed closed; do not drain/cut over another host.')
    print('PASS: multi-host deployment guard; topology healthy before deployment change. Production authorization remains external.')
if __name__=='__main__': main()
