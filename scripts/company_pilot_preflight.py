from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_MARKERS = ('CHANGE_ME', 'example', 'changeme', 'replace-me')


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def truthy(value: str | None) -> bool:
    return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def is_placeholder(value: str | None) -> bool:
    text = str(value or '').strip()
    return (not text) or any(marker.lower() in text.lower() for marker in PLACEHOLDER_MARKERS)


def get_http(url: str, path: str) -> tuple[bool, str]:
    target = url.rstrip('/') + path
    request = urllib.request.Request(target, headers={'User-Agent': 'mgc-company-pilot-preflight/6.0.17'})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read(4096).decode('utf-8', errors='replace')
            return 200 <= response.status < 300, f'{response.status} {body[:240]}'
    except urllib.error.HTTPError as exc:
        return False, f'HTTP {exc.code}'
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'


def main() -> int:
    parser = argparse.ArgumentParser(description='MGC Languages v6.0.17 company pilot GO/NO-GO preflight')
    parser.add_argument('--env-file', default='.env.pilot')
    parser.add_argument('--url', default='')
    parser.add_argument('--strict-corporate', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    env_path = (ROOT / args.env_file).resolve() if not Path(args.env_file).is_absolute() else Path(args.env_file)
    env = read_env(env_path)
    merged = dict(os.environ)
    merged.update(env)

    checks: list[dict[str, object]] = []

    def check(name: str, ok: bool, detail: str, severity: str = 'blocker') -> None:
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail, 'severity': severity})

    required_files = [
        'docker-compose.pilot.yml', '.env.company-pilot.example',
        'static/frontend/pilot_home.js', 'static/pilot.css',
        'docs/COMPANY_PILOT_RUNBOOK_v6.0.17.md', 'docs/PILOT_UAT_v6.0.17.md'
    ]
    for rel in required_files:
        check(f'file:{rel}', (ROOT / rel).exists(), 'present' if (ROOT / rel).exists() else 'missing')

    check('env-file', env_path.exists(), str(env_path))
    check('postgres-password', not is_placeholder(merged.get('POSTGRES_PASSWORD')), 'configured' if not is_placeholder(merged.get('POSTGRES_PASSWORD')) else 'missing/placeholder')
    check('oidc-state-secret', not is_placeholder(merged.get('OIDC_STATE_SECRET')), 'configured' if not is_placeholder(merged.get('OIDC_STATE_SECRET')) else 'missing/placeholder')
    check('metrics-token', not is_placeholder(merged.get('METRICS_TOKEN')), 'configured' if not is_placeholder(merged.get('METRICS_TOKEN')) else 'missing/placeholder')
    check('registration-disabled', str(merged.get('REGISTRATION_ENABLED', '')).lower() == 'false', f"REGISTRATION_ENABLED={merged.get('REGISTRATION_ENABLED', '')}")
    check('schema-head-required', truthy(merged.get('READY_REQUIRE_SCHEMA_HEAD')), f"READY_REQUIRE_SCHEMA_HEAD={merged.get('READY_REQUIRE_SCHEMA_HEAD', '')}")
    check('rls-required', truthy(merged.get('READY_REQUIRE_RLS')), f"READY_REQUIRE_RLS={merged.get('READY_REQUIRE_RLS', '')}")
    check('content-approval-required', truthy(merged.get('READY_REQUIRE_TERM_APPROVAL')), f"READY_REQUIRE_TERM_APPROVAL={merged.get('READY_REQUIRE_TERM_APPROVAL', '')}")

    trusted = str(merged.get('TRUSTED_HOSTS', '')).strip()
    lan_ready = bool(trusted) and trusted not in {'localhost', '127.0.0.1', 'localhost,127.0.0.1'}
    check('lan-trusted-host', lan_ready, f'TRUSTED_HOSTS={trusted or "<empty>"}')

    if args.strict_corporate:
        check('auth-mode-oidc', str(merged.get('AUTH_MODE', '')).lower() == 'oidc', f"AUTH_MODE={merged.get('AUTH_MODE', '')}")
        check('secure-cookie', truthy(merged.get('COOKIE_SECURE')), f"COOKIE_SECURE={merged.get('COOKIE_SECURE', '')}")
        check('ready-require-oidc', truthy(merged.get('READY_REQUIRE_OIDC')), f"READY_REQUIRE_OIDC={merged.get('READY_REQUIRE_OIDC', '')}")
        check('ready-require-secure-cookie', truthy(merged.get('READY_REQUIRE_SECURE_COOKIE')), f"READY_REQUIRE_SECURE_COOKIE={merged.get('READY_REQUIRE_SECURE_COOKIE', '')}")
        for key in ('OIDC_DISCOVERY_URL', 'OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET'):
            check(key.lower(), not is_placeholder(merged.get(key)), 'configured' if not is_placeholder(merged.get(key)) else 'missing/placeholder')

    compose = (ROOT / 'docker-compose.pilot.yml').read_text(encoding='utf-8') if (ROOT / 'docker-compose.pilot.yml').exists() else ''
    for token in ('postgres:16.4-alpine', 'nginx:1.27-alpine', 'internal: true', 'read_only: true', 'no-new-privileges:true', '/health/ready'):
        check(f'compose:{token}', token in compose, 'present' if token in compose else 'missing')

    for asset in ('hero-chinese.svg', 'hero-english.svg') + tuple(f'phrase-{i}.svg' for i in range(1, 8)):
        check(f'asset:{asset}', (ROOT / 'static' / 'pilot' / asset).exists(), 'present' if (ROOT / 'static' / 'pilot' / asset).exists() else 'missing')

    if args.url:
        for path in ('/health/live', '/health/ready', '/api/meta'):
            ok, detail = get_http(args.url, path)
            check(f'http:{path}', ok, detail)

    blockers = [item for item in checks if not item['ok'] and item['severity'] == 'blocker']
    result = {'status': 'GO' if not blockers else 'NO-GO', 'checks': checks, 'blockers': len(blockers)}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            prefix = 'PASS' if item['ok'] else 'FAIL'
            print(f"{prefix:4} {item['name']}: {item['detail']}")
        print(f"\n{result['status']}: {len(checks) - len(blockers)}/{len(checks)} checks non-blocking; blockers={len(blockers)}")

    return 0 if not blockers else 2


if __name__ == '__main__':
    raise SystemExit(main())
