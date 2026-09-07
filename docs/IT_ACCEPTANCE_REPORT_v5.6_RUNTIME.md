# MGC Languages v5.6 — IT Acceptance Report

- Generated: 2026-09-07T03:54:05.419530+00:00
- Target: `http://127.0.0.1:8765`
- Auth mode: `local`
- Result: **20 PASS / 0 FAIL / 0 SKIP**

| Check | Result | Detail |
|---|---|---|
| liveness | **PASS** | status=200 version=5.6 |
| readiness | **PASS** | status=200 recovery=healthy |
| schema head | **PASS** | {'status': 'ok', 'current': 'b56f0c21e560', 'expected': 'b56f0c21e560'} |
| meta/version | **PASS** | profile=pilot-operations-v5.5 |
| no voice recording | **PASS** | microphone/recording must remain disabled |
| protected metrics | **PASS** | status=200 |
| admin login | **PASS** | status=200 |
| Chinese information title | **PASS** | Информация о китайском |
| 10 major groups | **PASS** | groups=10 |
| dialect comparisons | **PASS** | examples=3 |
| Putonghua primary scope | **PASS** | Путунхуа (普通话) |
| dialects reference-only | **PASS** | Диалекты и региональные варианты ниже — только справка. Их не нужно учить: они не входят в основной курс, тесты, XP или итоговый экзамен. |
| pilot governance summary | **PASS** | status=200 groups=0 |
| pilot groups endpoint | **PASS** | status=200 groups=0 |
| feature flag catalog | **PASS** | flags=['ai_assistant', 'chinese_reference', 'games', 'learning_nudges', 'server_audio', 'xp_economy'] |
| IT dashboard | **PASS** | status=200 |
| learning error telemetry | **PASS** | status=200 |
| pilot alerts endpoint | **PASS** | active=0 |
| maintenance dry-run | **PASS** | status=200 |
| Mandarin WAV playback | **PASS** | status=200 bytes=71798 |

## Sign-off boundary
Passing automated checks supports a controlled pilot decision. Corporate OIDC, TLS/secure-cookie configuration, PostgreSQL backup/restore rehearsal, central monitoring and any required security review must still be evidenced on the real IT environment.
