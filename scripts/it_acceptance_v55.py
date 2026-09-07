from __future__ import annotations
import argparse, http.cookiejar, json, os, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

parser=argparse.ArgumentParser(description='MGC Languages v5.5 runtime IT acceptance')
parser.add_argument('--report',default='',help='optional Markdown report path')
args=parser.parse_args()

base=os.getenv('MGC_BASE_URL','http://localhost:8080').rstrip('/')
metrics_token=os.getenv('METRICS_TOKEN','').strip()
admin_user=os.getenv('MGC_ADMIN_USERNAME','').strip()
admin_password=os.getenv('MGC_ADMIN_PASSWORD','').strip()
auth_mode=os.getenv('AUTH_MODE','local').strip().lower()
jar=http.cookiejar.CookieJar(); opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
results=[]

def request(path,method='GET',data=None,headers=None):
    raw=None; h={'Accept':'application/json'}
    if headers: h.update(headers)
    if data is not None: raw=json.dumps(data).encode('utf-8'); h['Content-Type']='application/json'
    req=urllib.request.Request(base+path,data=raw,headers=h,method=method)
    try:
        with opener.open(req,timeout=20) as r: return r.status,r.headers,r.read()
    except urllib.error.HTTPError as e:
        return e.code,e.headers,e.read()

def check(name,ok,detail=''):
    results.append((name,'PASS' if ok else 'FAIL',detail))
    if not ok: print('FAIL:',name,detail)
    else: print('PASS:',name,detail)
    return ok

def jget(path,headers=None):
    st,_,body=request(path,headers=headers)
    try: payload=json.loads(body or b'{}')
    except Exception: payload={}
    return st,payload

st,live=jget('/health/live')
check('liveness',st==200 and live.get('version')=='5.7',f"status={st} version={live.get('version')}")
st,ready=jget('/health/ready')
check('readiness',st==200 and ready.get('status')=='ready',f"status={st} recovery={(ready.get('recovery') or {}).get('state')}")
check('schema head',(ready.get('checks') or {}).get('schema_head',{}).get('current')=='a55c0b91d550',str((ready.get('checks') or {}).get('schema_head')))
st,meta=jget('/api/meta')
check('meta/version',st==200 and meta.get('version')=='5.7',f"profile={meta.get('slo_profile')}")
check('no voice recording',meta.get('voice_recording_enabled') is False,'microphone/recording must remain disabled')

if metrics_token:
    st,headers,body=request('/metrics',headers={'Authorization':'Bearer '+metrics_token})
    text=body.decode('utf-8','replace')
    required=['mgc_slo_availability_percent','mgc_slo_error_rate_percent','mgc_slo_p95_ms','mgc_recovery_state','mgc_pilot_alerts_open']
    check('protected metrics',st==200 and all(x in text for x in required),f"status={st}")
else:
    results.append(('protected metrics','SKIP','METRICS_TOKEN not supplied to acceptance process'))
    print('SKIP: protected metrics')

admin_checks=False
if auth_mode=='local' and admin_user and admin_password:
    st,_,body=request('/api/login','POST',{'username':admin_user,'password':admin_password})
    admin_checks=check('admin login',st==200,f"status={st}")
    if admin_checks:
        csrf=next((c.value for c in jar if c.name=='mgc_csrf'),'')
        st,found=jget('/api/chinese/foundations')
        pt=found.get('putonghua') or {}
        check('Chinese information title',st==200 and found.get('title')=='Информация о китайском',str(found.get('title')))
        check('10 major groups',len(pt.get('groups') or [])==10,f"groups={len(pt.get('groups') or [])}")
        comparisons=pt.get('comparison_examples') or []
        check('dialect comparisons',len(comparisons)>=3 and any(x.get('id')=='hello' for x in comparisons),f"examples={len(comparisons)}")
        st,dash=jget('/api/admin/it-dashboard')
        check('IT dashboard',st==200 and all(k in dash for k in ('readiness','recovery','slo','alerts','maintenance')),f"status={st}")
        st,learning=jget('/api/admin/learning-error-telemetry')
        check('learning error telemetry',st==200 and 'weak_topics' in learning and 'note' in learning,f"status={st}")
        st,alerts=jget('/api/admin/alerts')
        check('pilot alerts endpoint',st==200 and 'alerts' in alerts and 'slo' in alerts,f"active={alerts.get('active_count')}")
        st,_,body=request('/api/admin/maintenance/cleanup?dry_run=true','POST',{}, {'X-CSRF-Token':csrf})
        try: cleanup=json.loads(body or b'{}')
        except Exception: cleanup={}
        check('maintenance dry-run',st==200 and cleanup.get('dry_run') is True and 'counts' in cleanup,f"status={st}")
        st,pron=jget('/api/pronunciation/status')
        if st==200 and pron.get('server_available'):
            st,h,wav=request('/api/pronunciation/audio','POST',{'language':'chinese','text':'普通话','rate':0.8},{'X-CSRF-Token':csrf})
            check('Mandarin WAV playback',st==200 and wav[:4]==b'RIFF',f"status={st} bytes={len(wav)}")
        else:
            results.append(('Mandarin WAV playback','SKIP','offline server TTS unavailable; browser fallback must be checked in UI'))
            print('SKIP: Mandarin WAV playback (server TTS unavailable)')
else:
    results.append(('authenticated Admin checks','SKIP','Use local sandbox credentials or complete these checks manually after corporate OIDC login'))
    print('SKIP: authenticated Admin checks')

# Emit formal Markdown report.
if args.report:
    path=Path(args.report)
    path.parent.mkdir(parents=True,exist_ok=True)
    passed=sum(1 for _,s,_ in results if s=='PASS'); failed=sum(1 for _,s,_ in results if s=='FAIL'); skipped=sum(1 for _,s,_ in results if s=='SKIP')
    rows=['# MGC Languages v5.5 — IT Acceptance Report','',f'- Generated: {datetime.now(timezone.utc).isoformat()}',f'- Target: `{base}`',f'- Auth mode: `{auth_mode}`',f'- Result: **{passed} PASS / {failed} FAIL / {skipped} SKIP**','', '| Check | Result | Detail |','|---|---|---|']
    for name,status,detail in results:
        rows.append(f"| {name.replace('|','/')} | **{status}** | {str(detail).replace('|','/')} |")
    rows += ['','## Sign-off boundary','Passing automated checks supports a controlled pilot decision. Corporate OIDC, TLS/secure-cookie configuration, PostgreSQL backup/restore rehearsal, central monitoring and any required security review must still be evidenced on the real IT environment.','']
    path.write_text('\n'.join(rows),encoding='utf-8')
    print('REPORT:',path)

failed=[x for x in results if x[1]=='FAIL']
if failed:
    raise SystemExit(1)
print('PASS: v5.5 runtime IT acceptance')
