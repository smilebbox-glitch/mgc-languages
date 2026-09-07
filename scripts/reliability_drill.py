from __future__ import annotations
import argparse, json, urllib.error, urllib.request

def fetch(base, path):
    try:
        with urllib.request.urlopen(base.rstrip('/')+path,timeout=8) as r:
            body=r.read(); return r.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body=exc.read()
        try: data=json.loads(body)
        except Exception: data={'raw':body.decode('utf-8','replace')[:300]}
        return exc.code,data

p=argparse.ArgumentParser(description='Safe MGC Languages pilot reliability observation drill')
p.add_argument('--base-url',default='http://localhost:8080')
p.add_argument('--expect',choices=['ready','db-down'],default='ready')
a=p.parse_args()
live_s,live=fetch(a.base_url,'/health/live'); ready_s,ready=fetch(a.base_url,'/health/ready')
assert live_s==200,(live_s,live)
if a.expect=='ready':
    assert ready_s==200 and ready.get('status')=='ready',(ready_s,ready)
    print('PASS: live=200, ready=200')
else:
    assert ready_s==503 and ready.get('status')=='not_ready',(ready_s,ready)
    assert ready.get('checks',{}).get('database')=='failed',(ready_s,ready)
    print('PASS: DB-down graceful degradation: live=200, ready=503, instance should be removed from traffic')
