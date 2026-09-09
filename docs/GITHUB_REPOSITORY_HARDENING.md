# GitHub repository hardening

This document describes the repository controls for the MGC Languages controlled pilot.

## Current repository-side controls

The repository contains automated controls that do not require GitHub administration access:

- CodeQL analysis;
- dependency audit and secret preflight;
- server/mobile HTTPS security gate;
- v6.0.29 RC1 release freeze guard;
- PWA cache-isolation regression;
- CODEOWNERS ownership for security-critical paths;
- repository-integrity workflow;
- pull-request security checklist.

The repository-integrity workflow raises an alarm when a commit pushed to `main` is not associated with a merged pull request. This is detection, not prevention.

## Required GitHub admin settings for `main`

When repository administration is available, create a branch ruleset for the default branch `main`.

Recommended settings:

1. Require a pull request before merging.
2. Require status checks to pass before merging.
3. Require the branch to be up to date before merging.
4. Block force pushes.
5. Block branch deletion.
6. Require linear history where compatible with the chosen merge method.
7. Restrict bypass permissions to repository administration/emergency use only.
8. Keep required approvals at a level that does not deadlock a single-maintainer pilot. While there is only one maintainer, do not require that maintainer to approve their own PR. Enable independent/code-owner approval when a second authorized reviewer exists.

Recommended required PR status checks include the stable job contexts used by the repository:

- `repository-policy`;
- `quality`;
- `lan-compose-smoke`;
- `v629-release-candidate-gate`;
- `security-contracts`;
- `phone HTTPS -> gateway -> app -> PostgreSQL`;
- `Analyze Python` (CodeQL).

Do not configure `main-pr-association` as a required PR check: it intentionally runs after a push reaches `main` and is an integrity alarm for direct pushes.

## Security-critical paths

Treat changes to these areas as security-sensitive:

- `.github/workflows/` and `.github/CODEOWNERS`;
- authentication, authorization and security modules;
- deployment/gateway/Nginx configuration;
- Docker/Compose production and LAN profiles;
- release manifests and release guards;
- secret scanning/preflight logic;
- PWA service worker and registration code.

## Public-to-private transition

While the repository is public, assume every tracked file is externally readable. Never commit runtime secrets, credentials, employee data, internal production URLs, private certificates or confidential partner documents.

Making the repository private later reduces code exposure but does not replace branch rules, security workflows, secret management, least privilege or review controls. Keep the same controls after the visibility change.

## Visibility-change checklist

After switching the repository to private:

- verify GitHub Actions still run;
- verify CodeQL/security scanning availability for the account/plan;
- verify collaborators and app installations are still appropriate;
- review repository Actions permissions and keep the default token read-only unless a workflow explicitly needs write access;
- enable the `main` ruleset described above;
- re-run the full security and LAN/runtime workflows.
