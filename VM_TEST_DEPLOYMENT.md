# MGC Languages — test VM deployment (CPU-only / no server-side AI/TTS)

This profile is intended for a temporary internal VM before the dedicated GPU workstation/server is available.

## Recommended VM

- 4 vCPU if both MGC services share one VM
- 8 GB RAM if both services share one VM
- 30–40 GB free disk
- Docker Engine/Desktop with Docker Compose v2
- no GPU required

MGC Languages uses port **8080** by default. Okno v Kitai uses port 3000, so both can run on the same VM without a port conflict.

## What stays enabled

- Chinese + English learning content
- 20 Automotive Arcade games
- XP, tests and course progression
- Factory Journey, decision chains and Shift Simulation
- PostgreSQL persistence
- manager/team analytics and leaderboards
- local test authentication

## What is disabled for the temporary VM

`TTS_ENABLED=false` disables the server-side pronunciation engine and its disk cache to reduce CPU/RAM load. Browser speech synthesis may still be available on client devices. No GPU is required.

## Linux VM

```bash
chmod +x scripts/start-vm.sh
./scripts/start-vm.sh
```

The launcher creates `.env.vm` on first start, generates PostgreSQL/admin/metrics secrets, validates Compose, builds the app, starts PostgreSQL + app + Nginx and waits for readiness.

## Windows VM

Double-click:

```text
START_VM.bat
```

or run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-vm.ps1
```

## URLs

- local: `http://127.0.0.1:8080`
- LAN: `http://<VM-IP>:8080`

The VM/network firewall must allow TCP 8080 from the required corporate subnet if users connect from other PCs.

## Admin password

The generated admin password is stored only in `.env.vm` on the VM. Do not commit `.env.vm` to Git.

## Stop

```bash
docker compose --env-file .env.vm -f docker-compose.lan.yml -f docker-compose.vm.yml down
```

PostgreSQL data stays in the named Docker volume `lan_pgdata`.

## Later AI/GPU migration

Keep this VM profile as a lightweight fallback. The future GPU/AI integration can be added to the normal pilot deployment without changing the frozen core learning/game contracts.
