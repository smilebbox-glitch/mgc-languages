#!/usr/bin/env python3
import argparse, hashlib, hmac, time

p=argparse.ArgumentParser(description="Sign an MGC integration webhook payload")
p.add_argument("--secret", required=True)
p.add_argument("--body", default='{"event":"changed"}')
a=p.parse_args()
ts=str(int(time.time()))
sig=hmac.new(a.secret.encode(), ts.encode()+b"."+a.body.encode(), hashlib.sha256).hexdigest()
print(f"X-MGC-Timestamp: {ts}")
print(f"X-MGC-Signature: sha256={sig}")
print(a.body)
