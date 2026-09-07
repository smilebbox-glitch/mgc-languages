# IT Acceptance Report — Окно в Китай

- Version: **1.6.1-pilot**
- Mode: **package**
- Status: **CONDITIONAL**
- Generated: 2026-09-06T19:16:11.992Z
- SBOM components: 878

| Gate | Status | Duration |
|---|---|---:|
| Security preflight | PASS | 44 ms |
| Operations preflight | PASS | 32 ms |
| Reliability preflight | PASS | 32 ms |
| Governance preflight | PASS | 32 ms |
| Business operations preflight | PASS | 33 ms |
| One-click deployment preflight | PASS | 29 ms |
| TypeScript syntax | PASS | 762 ms |
| SBOM generation | PASS | 59 ms |
| Targeted pilot tests | PASS | 146 ms |
| Dependency vulnerability audit | PENDING | 6 ms |

## Interpretation

- **ACCEPT**: target runtime + online dependency audit passed.
- **CONDITIONAL**: package gates passed, but target runtime and/or online CVE gate still require execution in corporate infrastructure.
- **FAIL**: at least one required gate failed.

### Dependency vulnerability audit

```text
PENDING: set ONLINE_ACCEPTANCE=YES where registry/advisory network access is available
```
