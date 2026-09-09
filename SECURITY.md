# Security Policy

MGC Languages is a controlled-pilot project. The current security-maintained pilot baseline is **v6.0.29 RC1** unless IT establishes a newer approved baseline.

## Reporting

Do not publish credentials, tokens, production/internal URLs, employee data, partner-confidential data or vulnerability details in public issues, discussions or pull-request comments.
Use the repository owner's private communication channel for security-sensitive findings.

## Secrets and confidential data

- Never commit `.env` files, runtime credentials, API tokens, private keys or private certificates.
- Use `.env.example` / `.env.pilot.example` only as templates and keep them free of real secrets.
- Pilot and production secrets must be supplied by the target environment or an approved secret manager.
- Do not commit employee records, production exports, internal infrastructure addresses or confidential partner documentation.
- While the repository is public, treat every tracked file and Git history object as externally readable.

## Required security gates

Security-sensitive changes must preserve and pass the applicable repository controls:

- secret preflight and dependency audit;
- CodeQL;
- server/mobile HTTPS security gate;
- v6.0.29 RC1 release freeze guard;
- repository-integrity policy;
- PWA cache-isolation regression when the web/PWA layer changes.

Authentication, authorization, cookies, CORS, HTTPS/gateway, admin/manager access, deployment profiles and workflow-permission changes require explicit security review in the pull request.

## PWA / web security invariant

The service worker must never make authenticated/API/admin/manager/user/metrics/health responses or user-specific HTML available from Cache Storage. Navigation remains network-first/no-store with only a generic non-user-specific offline fallback.

PWA registration requires HTTPS, except for the browser platform's localhost development exception. Do not add an insecure HTTP bypass.

## Main-branch integrity

Changes should reach `main` through pull requests with green required checks. The repository-integrity workflow detects a `main` commit that is not associated with a merged pull request. Actual prevention of direct pushes requires a GitHub branch ruleset/branch protection and must be enabled with repository administration access.

## Repository visibility

Changing the repository from public to private is recommended before confidential company use. Private visibility is not a substitute for branch rules, least privilege, secret management, code review or security scanning; retain those controls after the visibility change.
