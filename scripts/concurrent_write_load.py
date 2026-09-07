from __future__ import annotations

import argparse, concurrent.futures, json, secrets, time, urllib.error, urllib.request
from pathlib import Path


def call(method, url, token, csrf, payload=None, timeout=8.0):
    body=None if payload is None else json.dumps(payload).encode()
    headers={"Cookie":f"mgc_session={token}; mgc_csrf={csrf}","Accept":"application/json"}
    if payload is not None:
        headers.update({"Content-Type":"application/json","X-CSRF-Token":csrf})
    req=urllib.request.Request(url,data=body,headers=headers,method=method)
    started=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=r.read().decode("utf-8",errors="replace")
            return r.status,(json.loads(raw) if raw else {}),(time.perf_counter()-started)*1000
    except urllib.error.HTTPError as e:
        raw=e.read().decode("utf-8",errors="replace")
        try:data=json.loads(raw) if raw else {}
        except Exception:data={"raw":raw}
        return e.code,data,(time.perf_counter()-started)*1000


def profile(base,row,csrf,timeout):
    status,data,_=call("GET",base+"/api/gamification/me",row["session_token"],csrf,timeout=timeout)
    return status,int(data.get("lifetime_xp",-1))


def write_one(base,row,csrf,session_id,timeout):
    return call("POST",base+"/api/practice/result",row["session_token"],csrf,payload={
        "session_id":session_id,"kind":"quiz","language":"chinese","topic":"","score":5,"total":5
    },timeout=timeout)


def main():
    p=argparse.ArgumentParser(description="Concurrent authenticated write-integrity probe")
    p.add_argument("--base-url",default="http://127.0.0.1:8080")
    p.add_argument("--sessions-file",required=True)
    p.add_argument("--users",type=int,default=50)
    p.add_argument("--writes-per-user",type=int,default=5)
    p.add_argument("--timeout",type=float,default=8.0)
    p.add_argument("--report-file")
    a=p.parse_args()
    raw=json.loads(Path(a.sessions_file).read_text(encoding="utf-8"))
    rows=[x for x in raw.get("sessions",[]) if isinstance(x,dict) and x.get("session_token") and x.get("user_id")]
    rows=rows[:max(1,min(200,a.users))]
    if not rows: raise SystemExit("ERROR: no authenticated fixtures")
    writes=max(1,min(20,a.writes_per_user)); base=a.base_url.rstrip("/"); run_id=secrets.token_hex(6)
    csrf={int(r["user_id"]):f"load-csrf-{r['user_id']}-{run_id}" for r in rows}
    baseline={}
    for r in rows:
        uid=int(r["user_id"]); status,xp=profile(base,r,csrf[uid],a.timeout)
        if status!=200 or xp<0: raise SystemExit(f"ERROR: baseline profile failed for user {uid}: {status}")
        baseline[uid]=xp
    ids={int(r["user_id"]):[f"write-{run_id}-{r['user_id']}-{i+1}" for i in range(writes)] for r in rows}
    started=time.perf_counter(); results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(rows)) as ex:
        futures={ex.submit(write_one,base,r,csrf[int(r["user_id"])],sid,a.timeout):(int(r["user_id"]),sid)
                 for r in rows for sid in ids[int(r["user_id"])]}
        for f in concurrent.futures.as_completed(futures):
            uid,sid=futures[f]
            try:status,data,ms=f.result()
            except Exception as e:status,data,ms=0,{"error":f"{type(e).__name__}: {e}"},0.0
            results.append((uid,sid,status,data,ms))
    wall=time.perf_counter()-started
    write_fail=[{"user_id":u,"session_id":s,"status":st,"body":d} for u,s,st,d,_ in results if st!=200 or d.get("duplicate") is True]
    dup_fail=[]
    for r in rows:
        uid=int(r["user_id"]); sid=ids[uid][0]; st,d,_=write_one(base,r,csrf[uid],sid,a.timeout)
        if st!=200 or d.get("duplicate") is not True: dup_fail.append({"user_id":uid,"status":st,"body":d})
    expected=writes*40; isolation=[]
    for r in rows:
        uid=int(r["user_id"]); st,xp=profile(base,r,csrf[uid],a.timeout); delta=xp-baseline[uid] if st==200 else -1
        if st!=200 or delta!=expected: isolation.append({"user_id":uid,"status":st,"delta":delta,"expected":expected})
    lat=[x[4] for x in results if x[4]>0]
    report={"run_id":run_id,"authenticated_users":len(rows),"writes_per_user":writes,"attempted_writes":len(results),
            "successful_unique_writes":len(results)-len(write_fail),"write_failures":write_fail[:10],
            "duplicate_replays_checked":len(rows),"duplicate_failures":dup_fail[:10],"expected_xp_delta_per_user":expected,
            "isolation_failures":isolation[:10],"wall_seconds":round(wall,3),"writes_per_second":round(len(results)/max(wall,.001),2),
            "write_latency_ms":{"mean":round(sum(lat)/len(lat),2) if lat else None,"max":round(max(lat),2) if lat else None}}
    text=json.dumps(report,ensure_ascii=False,indent=2); print(text)
    if a.report_file: Path(a.report_file).write_text(text+"\n",encoding="utf-8")
    if write_fail:return 3
    if dup_fail:return 4
    if isolation:return 5
    print("PASS: concurrent authenticated write integrity preserved across users")
    return 0

if __name__=="__main__": raise SystemExit(main())
