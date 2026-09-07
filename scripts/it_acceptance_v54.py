from __future__ import annotations
import http.cookiejar, json, os, urllib.request

base=os.getenv('MGC_BASE_URL','http://localhost:8080').rstrip('/')
metrics_token=os.getenv('METRICS_TOKEN','').strip()
admin_user=os.getenv('MGC_ADMIN_USERNAME','').strip()
admin_password=os.getenv('MGC_ADMIN_PASSWORD','').strip()
auth_mode=os.getenv('AUTH_MODE','local').strip().lower()

jar=http.cookiejar.CookieJar(); opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def request(path, method='GET', data=None, headers=None):
    raw=None; h={'Accept':'application/json'}
    if headers: h.update(headers)
    if data is not None: raw=json.dumps(data).encode(); h['Content-Type']='application/json'
    req=urllib.request.Request(base+path,data=raw,headers=h,method=method)
    with opener.open(req,timeout=15) as r: return r.status,r.headers,r.read()
def jget(path):
    st,_,body=request(path); assert st==200,(path,st,body[:300]); return json.loads(body)

a=jget('/health/live'); ready=jget('/health/ready'); meta=jget('/api/meta')
assert a.get('version')=='5.4',a
assert ready.get('checks',{}).get('schema_head',{}).get('current')=='f54c0a91b723',ready
assert ready.get('checks',{}).get('database_latency',{}).get('status')=='ok',ready
assert meta.get('reliability_profile')=='pilot-v5.4' and meta.get('voice_recording_enabled') is False,meta

if metrics_token:
    st,_,body=request('/metrics',headers={'Authorization':'Bearer '+metrics_token})
    assert st==200 and b'mgc_operational_events_24h' in body and b'mgc_database_metrics_available' in body

if auth_mode=='local' and admin_user and admin_password:
    st,_,body=request('/api/login','POST',{'username':admin_user,'password':admin_password}); assert st==200,(st,body[:300])
    found=jget('/api/chinese/foundations'); assert found.get('title')=='Информация о китайском',found.get('title')
    assert len(found.get('putonghua',{}).get('groups',[]))==10
    dash=jget('/api/admin/it-dashboard')
    assert 'readiness' in dash and 'events_24h' in dash and 'maintenance' in dash and 'database' in dash,dash
    csrf=next((c.value for c in jar if c.name=='mgc_csrf'),'')
    st,_,body=request('/api/admin/maintenance/cleanup?dry_run=true','POST',{}, {'X-CSRF-Token':csrf})
    assert st==200 and 'counts' in json.loads(body)
    pron=jget('/api/pronunciation/status')
    if pron.get('server_available'):
        st,h,wav=request('/api/pronunciation/audio','POST',{'language':'chinese','text':'普通话','rate':0.8},{'X-CSRF-Token':csrf})
        assert st==200 and wav[:4]==b'RIFF',(st,h,wav[:16])
else:
    print('INFO: authenticated Admin/Chinese checks skipped; execute after OIDC login in corporate pilot.')

print('PASS: v5.4 reliability / Chinese information / IT dashboard acceptance')
