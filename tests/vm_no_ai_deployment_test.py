from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    env = read(".env.vm.example")
    override = read("docker-compose.vm.yml")
    linux = read("scripts/start-vm.sh")
    windows = read("scripts/start-vm.ps1")
    bat = read("START_VM.bat")

    assert "MGC_PORT=8080" in env
    assert "TTS_ENABLED=false" in env
    assert "TTS_DISK_CACHE_ENABLED=false" in env
    assert "PILOT_DAILY_TTS_CAP=0" in env
    assert "WEB_CONCURRENCY=1" in env

    assert 'TTS_ENABLED: "false"' in override
    assert 'TTS_DISK_CACHE_ENABLED: "false"' in override
    assert "mem_limit:" in override
    assert "cpus:" in override

    for source in (linux, windows):
        assert ".env.vm" in source
        assert "docker-compose.lan.yml" in source
        assert "docker-compose.vm.yml" in source

    assert "scripts\\start-vm.ps1" in bat
    print("PASS: VM CPU-only / no-server-AI deployment contract")


if __name__ == "__main__":
    main()
