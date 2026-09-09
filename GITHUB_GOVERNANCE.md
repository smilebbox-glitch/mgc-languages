# GitHub governance target

This file records the repository-administration settings required before confidential corporate use. These controls are enforced by GitHub repository settings, not by application code.

## Visibility

Target: **Private**.

Do not place real secrets in Git even after the repository becomes private.

## `main` ruleset / branch protection

Target branch: `main`.

Required controls:

- Require a pull request before merging.
- Require branches to be up to date before merging / strict required status checks.
- Require conversation resolution before merging.
- Block force pushes.
- Block branch deletion.
- Do not allow required checks to be bypassed for routine changes.

### Review count

While `@smilebbox-glitch` is the only maintainer/reviewer, use **0 required approvals** so the repository does not deadlock: GitHub does not count an author's self-approval.

As soon as a second trusted IT maintainer is added, change this to:

- 1 required approval;
- dismiss stale approvals when new commits are pushed;
- require review from Code Owners.

## Required status checks

Require these always-on checks for `main`:

- `repository-policy`
- `quality`
- `lan-compose-smoke`
- `security-contracts`
- `phone HTTPS -> gateway -> app -> PostgreSQL`
- `Analyze Python`

The frozen-pilot and deployment-specific workflows should still be run where applicable, but do not make path- or scenario-specific checks globally required unless they are guaranteed to start for every pull request.

## Workflow privilege policy

- `pull_request_target` is prohibited unless a separately reviewed security design explicitly requires it.
- `permissions: write-all` is prohibited.
- Workflows should default to `contents: read`; add only the narrow write permission needed by a specific job.
- Secrets must never be exposed to untrusted pull-request code.

## PR-only operating baseline

The repository-integrity alarm is already active. From this governance baseline onward, routine code, deployment and governance changes must be prepared on a branch and merged through a pull request, even before the GitHub admin ruleset is enabled. A direct `main` commit should be treated as a control failure, not as a normal deployment method.

This detection layer does not replace the ruleset: until GitHub branch protection is activated by a repository administrator, a direct push is still technically possible and will be detected only after it occurs.

## Expected operating model after enforcement

1. Create a branch.
2. Open a pull request to `main`.
3. Wait for required checks.
4. Resolve review/security findings.
5. Merge only when GitHub reports the ruleset satisfied.

Direct writes to `main` should be treated as a governance incident after the ruleset is enabled.
