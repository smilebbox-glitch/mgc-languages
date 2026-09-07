from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILES = [ROOT/'backend/Dockerfile', ROOT/'frontend/Dockerfile', ROOT/'ops/gateway/Dockerfile', ROOT/'ops/mock-integrations/Dockerfile', ROOT/'ops/webhook-gateway/Dockerfile', ROOT/'ops/enterprise-edge/Dockerfile']
errors=[]
checks=[]
for path in DOCKERFILES:
    text=path.read_text(encoding='utf-8')
    name=str(path.relative_to(ROOT))
    final_stage=text.split('\nFROM ')[-1]
    def check(ok, code, msg):
        checks.append((name,code,ok,msg))
        if not ok: errors.append(f'{name}: {code}: {msg}')
    check(not re.search(r'^\s*ADD\s', text, re.M|re.I), 'CIS-DI-0009', 'use COPY, not ADD')
    check('sudo' not in text.lower(), 'DKL-DI-0001', 'do not use sudo')
    check(not re.search(r'^FROM\s+\S+:latest(?:\s|$)', text, re.M|re.I), 'DKL-DI-0006', 'do not use latest base tag')
    check(bool(re.search(r'^USER\s+(?!root\b)\S+', final_stage, re.M|re.I)), 'CIS-DI-0001', 'final image must run as non-root')
    check('HEALTHCHECK' in final_stage, 'CIS-DI-0006', 'final image should define HEALTHCHECK')
    check(not re.search(r'^ENV\s+.*(?:PASSWORD|SECRET|TOKEN|PRIVATE_KEY)\s*=\s*\S+', text, re.M|re.I), 'CIS-DI-0010', 'no embedded secrets in ENV')
    # apt update must be in the same logical RUN instruction as install and cache cleanup.
    logical = text.replace('\\\n', ' ')
    for block in re.findall(r'^RUN\s+(.+)$', logical, re.I | re.M):
        if 'apt-get update' in block:
            check('apt-get install' in block and 'rm -rf /var/lib/apt/lists' in block, 'CIS-DI-0007/DKL-DI-0005', 'combine apt update/install and clear lists')
print('Docker/Dockle static preflight')
for name,code,ok,msg in checks:
    print(f"{'PASS' if ok else 'FAIL':4} {code:24} {name} — {msg}")
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: {len(checks)} checks, 0 failures')
