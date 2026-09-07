#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT/"backend"))
from app.core.runtime_contract import APP_VERSION

def component(name, version, ctype='library', **props):
    return {'type':ctype,'name':name,'version':version,'properties':[{'name':f'mgc:{k}','value':str(v)} for k,v in sorted(props.items())]}

def expanded(path:Path, seen=None):
    seen=set() if seen is None else seen; path=path.resolve()
    if path in seen: return []
    seen.add(path); rows=[]
    for raw in path.read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#'): continue
        if line.startswith('-r ') or line.startswith('--requirement '): rows.extend(expanded(path.parent/line.split(None,1)[1].strip(),seen))
        else: rows.append(line)
    return rows

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output', default=f'security-reports/SBOM_v{APP_VERSION}.cdx.json'); args=ap.parse_args()
    comps=[]; profile_membership={}
    for profile in ('core','ai','advanced'):
        for line in expanded(ROOT/f'backend/requirements-{profile}.txt'):
            m=re.match(r'([A-Za-z0-9_.-]+)(\[[^]]+\])?(.*)',line)
            if not m: continue
            key=m.group(1).lower(); profile_membership.setdefault(key,{'line':line,'profiles':set()})['profiles'].add(profile)
    for key,item in sorted(profile_membership.items()):
        m=re.match(r'([A-Za-z0-9_.-]+)(\[[^]]+\])?(.*)',item['line'])
        comps.append(component(m.group(1),(m.group(3) or 'declared').strip() or 'declared',ecosystem='python',resolution='declared-range',profiles=','.join(sorted(item['profiles']))))
    pkg=json.loads((ROOT/'frontend/package.json').read_text())
    for section in ('dependencies','devDependencies'):
        for name,ver in sorted((pkg.get(section) or {}).items()): comps.append(component(name,str(ver),ecosystem='npm',scope=section,resolution='declared-exact'))
    seen=set()
    for path in list(ROOT.rglob('Dockerfile')):
        for raw in path.read_text(errors='ignore').splitlines():
            if raw.upper().startswith('FROM '):
                image=raw.split()[1]
                if image not in seen:
                    seen.add(image); comps.append(component(image,image.split(':',1)[1] if ':' in image else 'unversioned',ctype='container',source=str(path.relative_to(ROOT))))
    bom={'bomFormat':'CycloneDX','specVersion':'1.5','serialNumber':f'urn:uuid:mgc-v{APP_VERSION}-offline-sbom','version':1,'metadata':{'timestamp':datetime.now(timezone.utc).isoformat(),'component':{'type':'application','name':'MGC Engineering AI Local','version':APP_VERSION},'properties':[{'name':'mgc:generator','value':'offline-declared-component-sbom'},{'name':'mgc:dependency-profiles','value':'core,ai,advanced'},{'name':'mgc:warning','value':'Declared dependency ranges are not a substitute for build-host resolved SBOM/CVE scan.'}]},'components':comps}
    out=ROOT/args.output; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(bom,ensure_ascii=False,indent=2)+'\n')
    try: label=out.relative_to(ROOT)
    except ValueError: label=out
    print(f'SBOM: {len(comps)} components -> {label}')
if __name__=='__main__': main()
