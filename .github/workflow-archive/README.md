# Archived GitHub Actions workflows

These workflow definitions are preserved for release history and troubleshooting, but they are intentionally stored outside `.github/workflows`, so GitHub Actions does not execute them automatically.

Archived after promotion of **MGC Languages Company Pilot v6.0.17** on 2026-09-08.

## Active CI

Only two workflows are active:

- `.github/workflows/ci.yml` — compact current CI: content/contracts, v6.0.16/v6.0.17 regression guards, JavaScript syntax and Docker runtime smoke;
- `.github/workflows/ci-v617-company-pilot.yml` — dedicated Company Pilot gate, including corporate preflight and approved UI checks.

## Archived CI

- `ci-v591.yml` … `ci-v616.yml` — historical release-specific checks;
- `ci-pre-v617-full-regression.yml` — previous broad matrix CI retained for forensic/manual reference;
- `restore-data-final.yml` and `restore-source-data.yml` — one-off recovery/migration workflows, intentionally disarmed.

Archived YAML files are documentation/history only. If one is ever needed again, review it first and deliberately restore a reviewed copy to `.github/workflows`.
