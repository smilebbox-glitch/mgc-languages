# Archived GitHub Actions workflows

These workflow definitions are preserved for release history and troubleshooting, but they are intentionally stored outside `.github/workflows`, so GitHub Actions does not execute them automatically.

Archived after promotion of **MGC Languages Company Pilot v6.0.17** on 2026-09-08.

Active CI is intentionally limited to:

- `.github/workflows/ci.yml` — current main regression/build CI;
- `.github/workflows/ci-v617-company-pilot.yml` — current Company Pilot gate.

The archived `ci-v591.yml` … `ci-v616.yml` files remain available as historical release-specific checks. The two restore workflows are also archived because they were one-off recovery/migration workflows and should not stay armed in the active Actions directory.

If an archived workflow is ever needed again, review it first and deliberately restore a reviewed copy to `.github/workflows` rather than moving it back automatically.
