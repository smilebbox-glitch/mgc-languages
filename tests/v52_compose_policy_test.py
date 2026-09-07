from pathlib import Path

root=Path(__file__).resolve().parents[1]
compose=(root/'docker-compose.pilot.yml').read_text()
dockerfile=(root/'Dockerfile').read_text()
env=(root/'.env.pilot.example').read_text()

def service_block(name: str) -> str:
    marker=f'  {name}:\n'
    start=compose.index(marker)+len(marker)
    tail=compose[start:]
    candidates=[i for token in ('\n  db:\n','\n  app:\n','\n  nginx:\n','\nnetworks:\n') if (i:=tail.find(token)) >= 0]
    end=min(candidates) if candidates else len(tail)
    return tail[:end]

db=service_block('db'); app=service_block('app'); nginx=service_block('nginx')
assert '\n    ports:' not in db, db
assert '\n    ports:' not in app, app
assert '\n    ports:' in nginx, nginx
assert 'internal: true' in compose
assert 'image: mgc-languages:5.7.1-it' in app
assert 'read_only: true' in app
assert 'no-new-privileges:true' in app
assert 'cap_drop:' in app and '- ALL' in app
assert 'TTS_ENABLED:' in app and 'OIDC_DEPARTMENT_CLAIM:' in app
assert 'TTS_CACHE_DIR: /tmp/mgc-tts-cache' in app and 'TTS_CONCURRENCY:' in app and 'TTS_FAILURE_THRESHOLD:' in app
assert 'TTS_LEGACY_GET_ENABLED:' in app and 'TTS_CACHE_PERSISTENCE:' in app
assert 'READY_REQUIRE_SCHEMA_HEAD: "true"' in app and 'EXPECTED_ALEMBIC_HEAD: c57d0a31f570' in app
assert 'READY_REQUIRE_REGISTRATION_DISABLED: "true"' in app and 'READY_REQUIRE_METRICS_TOKEN: "true"' in app
assert 'MIGRATION_LOCK_TIMEOUT_SECONDS:' in app and 'MIGRATION_ADVISORY_LOCK_ID:' in app
assert 'ttscache:' not in compose
assert 'apt-get install -y --no-install-recommends espeak-ng' in dockerfile
assert 'USER mgc' in dockerfile
assert 'OIDC_DEPARTMENT_CLAIM=department' in env
assert 'TTS_ENABLED=true' in env
print('OK: v5.3 pilot Compose policy, bounded TTS and offline cache contract')
