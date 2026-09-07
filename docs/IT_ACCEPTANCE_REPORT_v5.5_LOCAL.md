# MGC Languages v5.5 — IT Acceptance Report

- Generated: 2026-09-06T21:30:16.785256+00:00
- Target: `http://127.0.0.1:8875`
- Auth mode: `local`
- Result: **15 PASS / 0 FAIL / 0 SKIP**

| Check | Result | Detail |
|---|---|---|
| liveness | **PASS** | status=200 version=5.5 |
| readiness | **PASS** | status=200 recovery=healthy |
| schema head | **PASS** | {'status': 'ok', 'current': 'a55c0b91d550', 'expected': 'a55c0b91d550'} |
| meta/version | **PASS** | profile=pilot-operations-v5.5 |
| no voice recording | **PASS** | microphone/recording must remain disabled |
| protected metrics | **PASS** | status=200 |
| admin login | **PASS** | status=200 |
| Chinese information title | **PASS** | Информация о китайском |
| 10 major groups | **PASS** | groups=10 |
| dialect comparisons | **PASS** | examples=3 |
| IT dashboard | **PASS** | status=200 |
| learning error telemetry | **PASS** | status=200 |
| pilot alerts endpoint | **PASS** | active=0 |
| maintenance dry-run | **PASS** | status=200 |
| Mandarin WAV playback | **PASS** | status=200 bytes=71798 |

## Sign-off boundary
Passing automated checks supports a controlled pilot decision. Corporate OIDC, TLS/secure-cookie configuration, PostgreSQL backup/restore rehearsal, central monitoring and any required security review must still be evidenced on the real IT environment.
