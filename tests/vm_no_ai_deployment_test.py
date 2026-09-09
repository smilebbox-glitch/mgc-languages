from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    env = read(".env.vm.example")
    lan = read("docker-compose.lan.yml")
    override = read("docker-compose.vm.yml")
    linux = read("scripts/start-vm.sh")
    windows = read("scripts/start-vm.ps1")
    bat = read("START_VM.bat")

    assert "MGC_PORT=8080" in env
    assert "TTS_ENABLED=false" in env
    assert "TTS_DISK_CACHE_ENABLED=false" in env
    assert "PILOT_DAILY_TTS_CAP=0" in env
    assert "WEB_CONCURRENCY=1" in env
    assert "MGC_TRUSTED_HOSTS=localhost,127.0.0.1" in env
    assert "MGC_TRUSTED_HOSTS=*" not in env

    assert 'TTS_ENABLED: "false"' in override
    assert 'TTS_DISK_CACHE_ENABLED: "false"' in override
    assert "mem_limit:" in override
    assert "cpus:" in override

    lan_nginx = lan.split("  nginx:", 1)[1]
    nginx = override.split("  nginx:", 1)[1]
    assert "no-new-privileges:true" in lan_nginx
    assert "security_opt:" not in nginx, "VM override must not duplicate the base security_opt list"
    assert "read_only: true" in nginx
    assert "cap_drop:\n      - ALL" in nginx
    for capability in ("CHOWN", "SETGID", "SETUID"):
        assert f"      - {capability}" in nginx
    assert "/var/cache/nginx:rw,noexec,nosuid" in nginx
    assert "/var/run:rw,noexec,nosuid" in nginx
    assert "/tmp:rw,noexec,nosuid" in nginx
    for forbidden in ("SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "DAC_OVERRIDE"):
        assert forbidden not in nginx

    for source in (linux, windows):
        assert ".env.vm" in source
        assert "docker-compose.lan.yml" in source
        assert "docker-compose.vm.yml" in source
        assert "MGC_TRUSTED_HOSTS" in source
        assert "localhost,127.0.0.1" in source

    assert "hostname -I" in linux
    assert "Get-NetIPAddress" in windows
    assert "Get-VmIPv4" in windows
    assert "scripts\\start-vm.ps1" in bat
    print(
        "PASS: VM CPU-only / no-server-AI deployment contract with readiness-safe trusted hosts "
        "and hardened exposed nginx gateway"
    )


if __name__ == "__main__":
    main()
