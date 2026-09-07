from __future__ import annotations
import argparse, concurrent.futures, http.cookiejar, json, statistics, time, urllib.parse, urllib.request

p=argparse.ArgumentParser(description='Small non-destructive HTTP load smoke for MGC Languages pilot')
p.add_argument('--base-url', default='http://localhost:8080')
p.add_argument('--requests', type=int, default=200)
p.add_argument('--workers', type=int, default=12)
p.add_argument('--include-audio', action='store_true')
p.add_argument('--username', default='')
p.add_argument('--password', default='')
a=p.parse_args()
base=a.base_url.rstrip('/')
paths=['/health/live','/api/meta']
cookie_header=''
csrf_token=''

if a.username and a.password:
    jar=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req=urllib.request.Request(base+'/api/login', data=json.dumps({'username':a.username,'password':a.password}).encode(), headers={'Content-Type':'application/json'}, method='POST')
    with opener.open(req,timeout=10) as r:
        assert r.status==200, r.read()
    cookie_header='; '.join(f'{c.name}={c.value}' for c in jar)
    csrf_token=next((c.value for c in jar if c.name=='mgc_csrf'),'')
    paths += ['/api/chinese/foundations','/api/pronunciation/status','/api/pilot/me']
    if a.include_audio:
        paths.append('POST:/api/pronunciation/audio')
elif a.include_audio:
    print('WARN: --include-audio ignored without --username/--password because pronunciation audio is authenticated')

def once(i):
    path=paths[i%len(paths)]
    t=time.perf_counter()
    try:
        headers={'Cookie':cookie_header} if cookie_header else {}
        is_audio=path == 'POST:/api/pronunciation/audio'
        if is_audio:
            headers.update({'Content-Type':'application/json','X-CSRF-Token':csrf_token})
            data=json.dumps({'language':'chinese','text':'质量','rate':0.85}).encode()
            req=urllib.request.Request(base+'/api/pronunciation/audio',data=data,headers=headers,method='POST')
        else:
            req=urllib.request.Request(base+path,headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            body=r.read(8)
            ok=r.status==200 and (not is_audio or body[:4]==b'RIFF')
            return ok,(time.perf_counter()-t)*1000,r.status,path
    except Exception as exc:
        return False,(time.perf_counter()-t)*1000,str(exc),path

start=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,a.workers)) as ex:
    results=list(ex.map(once, range(max(1,a.requests))))
elapsed=time.perf_counter()-start
ok=[r for r in results if r[0]]; bad=[r for r in results if not r[0]]
lat=sorted(r[1] for r in results)
def pct(q): return lat[min(len(lat)-1, max(0, int(round((len(lat)-1)*q))))]
print(f'requests={len(results)} success={len(ok)} failed={len(bad)} elapsed_s={elapsed:.2f} throughput_rps={len(results)/elapsed:.1f}')
print(f'latency_ms mean={statistics.fmean(lat):.1f} p50={pct(.50):.1f} p95={pct(.95):.1f} p99={pct(.99):.1f} max={max(lat):.1f}')
if bad:
    for r in bad[:10]: print('FAIL',r)
    raise SystemExit(2)
print('PASS: non-destructive pilot load smoke')
