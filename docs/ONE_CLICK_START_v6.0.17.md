# MGC Language Lab — One-click company pilot start

## Windows operator path

After the one-time IT configuration, start the company pilot by double-clicking:

`START_COMPANY_PILOT.bat`

The launcher automatically:

1. checks that Docker Desktop / Docker Engine is running;
2. checks Docker Compose v2;
3. validates `.env.pilot` with the strict corporate GO/NO-GO preflight;
4. builds the pilot containers;
5. starts the PostgreSQL / app / Nginx / backup / maintenance stack;
6. waits for `/health/ready`;
7. performs runtime validation;
8. opens the pilot in the browser.

## First run

A secure company pilot cannot be completely zero-configuration because real SSO client credentials, corporate DNS/host names and secrets must come from IT.

If `.env.pilot` does not exist, the launcher:

- copies `.env.company-pilot.example` to `.env.pilot`;
- opens it in Notepad;
- stops with `NO-GO` instead of launching with placeholder credentials.

IT fills the real values once, saves the file and then runs `START_COMPANY_PILOT.bat` again. Subsequent starts are one double-click.

## Safety

The launcher never uses `docker compose down -v` and therefore does not intentionally delete the PostgreSQL volume. A failed preflight or failed readiness check stops with `NO-GO` and leaves an explicit diagnostic message.

For a real company pilot, do not weaken OIDC, secure-cookie, RLS or content-approval readiness requirements merely to make the launcher pass.
