# Security Policy

MGC Languages is currently a controlled-pilot project.

## Reporting

Do not publish credentials, tokens, production URLs, employee data, or vulnerability details in public issues.
Use the repository owner's private communication channel for security-sensitive findings.

## Secrets

- Never commit `.env` files or runtime credentials.
- Use `.env.example` / `.env.pilot.example` only as templates.
- Pilot and production secrets must be supplied by the target environment or an approved secret manager.

## Supported release

Security fixes are applied to the latest v5.7.x pilot branch unless a separate maintenance policy is established by IT.
