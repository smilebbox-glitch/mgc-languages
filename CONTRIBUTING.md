# Contributing

## Branches

- `main`: release-ready code only.
- `develop`: integration branch for the next pilot increment.
- `feature/<name>`: isolated changes merged into `develop` by pull request.
- `hotfix/<name>`: urgent fixes branched from `main`.

## Required checks

Before merging into `main`:

1. static/schema checks pass;
2. regression shards pass;
3. no secrets or runtime databases are present;
4. Alembic head is compatible with the release;
5. release notes are updated for user-visible or operational changes.

## Security

Do not commit `.env`, passwords, tokens, private certificates, employee exports, or production backups.
