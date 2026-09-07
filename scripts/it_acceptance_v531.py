from __future__ import annotations
import http.cookiejar, json, os, urllib.parse, urllib.request

base=os.getenv('MGC_BASE_URL','http://localhost:8080').rstrip('/')
metrics_token=os.getenv('METRICS_TOKEN','').strip()
admin_user=os.getenv('MGC_ADMIN_USERNAME','').strip()
admin_password=os.getenv('MGC_ADMIN_PASSWORD','').strip()
auth_mode=os.getenv('AUTH_MODE','local').strip().lower()

jar=http.cookiejar.CookieJar()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def request(path, method='GET', data=None, headers=None):
    raw=None
    h={'Accept':'application/json'}
    if headers: h.update(headers)
    if data is not None:
        raw=json.dumps(data).encode(); h['Content-Type']='application/json'
    req=urllib.request.Request(base+path, data=raw, headers=h, method=method)
    with opener.open(req,timeout=15) as r:
        return r.status,r.headers,r.read()

def jget(path):
    st,_,body=request(path); assert st==200,(path,st,body[:300]); return json.loads(body)

jget('/health/live'); jget('/health/ready'); meta=jget('/api/meta')
assert str(meta.get('version','')).startswith('5.3.1'),meta
assert meta.get('voice_recording_enabled') is False and meta.get('pronunciation_transport') == 'POST', meta

if metrics_token:
    st,_,body=request('/metrics',headers={'Authorization':'Bearer '+metrics_token})
    assert st==200 and b'mgc_http_requests_total' in body

if auth_mode=='local' and admin_user and admin_password:
    st,_,body=request('/api/login','POST',{'username':admin_user,'password':admin_password})
    assert st==200,(st,body[:300])
    me=jget('/api/me'); assert me.get('role')=='admin',me
    found=jget('/api/chinese/foundations')
    assert len(found.get('tones',[]))==5 and found.get('context',{}).get('clues')
    assert len(found.get('putonghua',{}).get('groups',[]))==10 and found.get('putonghua',{}).get('workplace')
    pron=jget('/api/pronunciation/status')
    assert 'language_checks' in pron, pron
    if pron.get('server_available'):
        assert all(pron.get('language_checks',{}).values()), pron
        csrf=next((c.value for c in jar if c.name=='mgc_csrf'),'')
        st,h,wav=request('/api/pronunciation/audio','POST',{'language':'chinese','text':'质量','rate':0.75},{'X-CSRF-Token':csrf})
        assert st==200 and wav[:4]==b'RIFF',(st,h,wav[:16])
    telemetry=jget('/api/admin/pilot-telemetry')
    summary=jget('/api/admin/system/summary')
    assert 'departments' in telemetry and 'tts_engine' in telemetry and 'server_tts_available' in telemetry
    assert 'tts_engine' in summary
else:
    print('INFO: authenticated Chinese/TTS/Admin checks skipped. In OIDC mode execute them after corporate login or use the technical local-auth sandbox for automated acceptance.')

print('PASS: v5.3.1 Putonghua/TTS/privacy/IT acceptance checks')
