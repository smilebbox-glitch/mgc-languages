from pathlib import Path
import sys, yaml

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(name, cond):
    checks.append((name,bool(cond)))

required=[
 "docs/CORPORATE_DEPLOYMENT_ARCHITECTURE.md",
 "docs/CORPORATE_PILOT_LAUNCH_RUNBOOK.md",
 "docs/CORPORATE_NETWORK_PORTS.md",
 "docs/CORPORATE_IDENTITY_INTEGRATION_CHECKLIST.md",
 "docs/CORPORATE_SYSTEM_CONNECTIVITY_CHECKLIST.md",
 "docs/CORPORATE_PILOT_ROLLOUT_PLAN.md",
 "deployment/corporate-pilot/deployment-profile.example.yml",
 "deployment/corporate-pilot/launch-checklist.yml",
 "deployment/corporate-pilot/firewall-matrix.csv",
]
for f in required: check(f, (ROOT/f).exists())
profile=yaml.safe_load((ROOT/'deployment/corporate-pilot/deployment-profile.example.yml').read_text())
check('pilot population 15-30', profile.get('pilot',{}).get('users')==30)
check('target benchmark mandatory', profile.get('certification',{}).get('target_host_performance_required') is True)
check('deployment not auto-authorized', profile.get('governance',{}).get('deployment_authorized') is False)
check('only edge inbound rule documented', '443' in (ROOT/'deployment/corporate-pilot/firewall-matrix.csv').read_text() and '9443' in (ROOT/'deployment/corporate-pilot/firewall-matrix.csv').read_text())
failed=[n for n,ok in checks if not ok]
for n,ok in checks: print(('PASS' if ok else 'FAIL'), n)
print(f"Corporate deployment preflight: {len(checks)-len(failed)}/{len(checks)} PASS")
sys.exit(1 if failed else 0)
