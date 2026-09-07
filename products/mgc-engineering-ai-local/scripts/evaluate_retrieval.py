import json
import sys
from pathlib import Path

import httpx

base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
rows = [json.loads(x) for x in (Path(__file__).parents[1] / "evals/golden_questions.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
passed = 0
for row in rows:
    payload = {"query": row["question"], "limit": 10, "part_number": row.get("expected_part"), "revision": row.get("expected_revision")}
    r = httpx.post(base + "/api/v1/search", json=payload, timeout=60)
    r.raise_for_status()
    hits = r.json()
    ok = any(row["expected_source_contains"] in h.get("filename", "") for h in hits)
    passed += int(ok)
    print(("PASS" if ok else "FAIL"), row["question"])
print(f"{passed}/{len(rows)} golden retrieval checks passed")
raise SystemExit(0 if passed == len(rows) else 1)
