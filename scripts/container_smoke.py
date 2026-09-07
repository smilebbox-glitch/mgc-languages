from __future__ import annotations
import json, os, urllib.request
base=os.getenv('MGC_BASE_URL','http://localhost:8080').rstrip('/')

def get(path, headers=None):
    req=urllib.request.Request(base+path, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as r:
        body=r.read()
        assert r.status==200, (path,r.status,body[:300])
        return r.headers, body

for path in ('/health/live','/health/ready','/api/meta'):
    headers,body=get(path)
    text=body.decode('utf-8')
    print(path, 200, text[:300])
    if path=='/api/meta':
        data=json.loads(text)
        assert str(data.get('version','')).startswith('5.2'), data
        print('pronunciation capability advertised:', data.get('server_tts_available'))
print('PASS: deployed v5.2 public service smoke test')
