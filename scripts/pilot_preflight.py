from __future__ import annotations
import os, shutil, subprocess, sys

findings=[]
errors=[]
def env(name, default=''): return os.getenv(name, default).strip()
def flag(name, default='false'): return env(name, default).lower() in {'1','true','yes','on'}
def bad_secret(name, minimum=24):
    v=env(name)
    if not v or v.upper().startswith('CHANGE_ME') or len(v)<minimum:
        errors.append(f'{name}: set a non-default secret with at least {minimum} characters')

auth=env('AUTH_MODE','local').lower()
if auth not in {'local','oidc'}: errors.append('AUTH_MODE must be local or oidc')
bad_secret('POSTGRES_PASSWORD',16)
bad_secret('OIDC_STATE_SECRET',32)
if flag('METRICS_ENABLED','true'): bad_secret('METRICS_TOKEN',24)
if env('TRUSTED_HOSTS','') in {'','*'}: errors.append('TRUSTED_HOSTS must be explicit for pilot')
if flag('REGISTRATION_ENABLED','false'): findings.append('Self-registration is enabled; disable it for controlled pilot')
if auth=='local':
    bad_secret('MGC_ADMIN_PASSWORD',16)
    findings.append('AUTH_MODE=local is acceptable for technical sandbox; use OIDC for corporate controlled pilot')
else:
    for name in ('OIDC_DISCOVERY_URL','OIDC_CLIENT_ID','OIDC_CLIENT_SECRET'):
        if not env(name): errors.append(f'{name}: required when AUTH_MODE=oidc')
    if not env('OIDC_DEPARTMENT_CLAIM'):
        findings.append('OIDC_DEPARTMENT_CLAIM is empty; department-scoped Manager RBAC will default users to General')
    if not any(env(x) for x in ('OIDC_ADMIN_GROUP','OIDC_EDITOR_GROUP','OIDC_MANAGER_GROUP')):
        findings.append('No OIDC role groups configured; all SSO users will remain ordinary User unless roles are assigned by Admin')
if not flag('COOKIE_SECURE','false'):
    findings.append('COOKIE_SECURE=false; acceptable only behind trusted TLS-terminating reverse proxy during sandbox')


# Readiness policy alignment: fail early when the deployment profile contradicts its own gates.
if flag('READY_REQUIRE_OIDC','false') and auth != 'oidc':
    errors.append('READY_REQUIRE_OIDC=true but AUTH_MODE is not oidc')
if flag('READY_REQUIRE_REGISTRATION_DISABLED','true') and flag('REGISTRATION_ENABLED','false'):
    errors.append('READY_REQUIRE_REGISTRATION_DISABLED=true but REGISTRATION_ENABLED=true')
if flag('READY_REQUIRE_METRICS_TOKEN','true'):
    if not flag('METRICS_ENABLED','true'):
        errors.append('READY_REQUIRE_METRICS_TOKEN=true but METRICS_ENABLED=false')
    elif not env('METRICS_TOKEN') or env('METRICS_TOKEN').upper().startswith('CHANGE_ME'):
        errors.append('READY_REQUIRE_METRICS_TOKEN=true requires a non-default METRICS_TOKEN')
if flag('READY_REQUIRE_SECURE_COOKIE','false') and not flag('COOKIE_SECURE','false'):
    errors.append('READY_REQUIRE_SECURE_COOKIE=true but COOKIE_SECURE=false')
if flag('READY_REQUIRE_RLS','true') and not flag('RLS_ENABLED','true'):
    errors.append('READY_REQUIRE_RLS=true but RLS_ENABLED=false')
if flag('READY_REQUIRE_TERM_APPROVAL','true') and not flag('TERM_APPROVAL_REQUIRED','true'):
    errors.append('READY_REQUIRE_TERM_APPROVAL=true but TERM_APPROVAL_REQUIRED=false')
if flag('OTEL_ENABLED','false') and not env('OTEL_EXPORTER_OTLP_ENDPOINT'):
    findings.append('OTEL_ENABLED=true without OTEL_EXPORTER_OTLP_ENDPOINT; spans remain local/no-export')
if env('COOKIE_SAMESITE','lax').lower() == 'none' and not flag('COOKIE_SECURE','false'):
    errors.append('COOKIE_SAMESITE=none requires COOKIE_SECURE=true')
if '*' in [x.strip() for x in env('CORS_ORIGINS','').split(',') if x.strip()]:
    errors.append('CORS_ORIGINS must not contain * in pilot')
if flag('READY_REQUIRE_SCHEMA_HEAD','true') and env('EXPECTED_ALEMBIC_HEAD','c57d0a31f570') != 'c57d0a31f570':
    findings.append('EXPECTED_ALEMBIC_HEAD differs from packaged migration head c57d0a31f570; verify intentional override')

if flag('TTS_ENABLED','true'):
    binary = shutil.which('espeak-ng') or shutil.which('espeak')
    if binary:
        findings.append(f'Offline TTS engine detected: {binary}')
        for language, voice_name, sample in (('Chinese', env('TTS_VOICE_CHINESE','zh'), '你好'), ('English', env('TTS_VOICE_ENGLISH','en-us'), 'hello')):
            if voice_name:
                try:
                    probe=subprocess.run([binary,'-v',voice_name,'--stdout'],input=sample.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=False)
                    if probe.returncode or not probe.stdout.startswith(b'RIFF'):
                        errors.append(f'{language} TTS voice {voice_name!r} failed local synthesis probe')
                    else:
                        findings.append(f'{language} TTS voice probe passed: {voice_name}')
                except Exception as exc:
                    errors.append(f'{language} TTS voice probe failed: {exc}')
    else:
        findings.append('Offline TTS binary is not present on this host. Docker image installs espeak-ng; browser SpeechSynthesis remains fallback.')
    # Application defaults (zh / en-us) are valid; explicit env overrides are optional.
    if not env('TTS_VOICE_CHINESE','zh'): errors.append('TTS_VOICE_CHINESE resolved to an empty value')
    if not env('TTS_VOICE_ENGLISH','en-us'): errors.append('TTS_VOICE_ENGLISH resolved to an empty value')
    try:
        max_chars=int(env('TTS_MAX_CHARS','300'))
        if not 20 <= max_chars <= 1000: errors.append('TTS_MAX_CHARS must be between 20 and 1000 for pilot')
    except ValueError:
        errors.append('TTS_MAX_CHARS must be an integer')
else:
    findings.append('TTS_ENABLED=false; pronunciation will rely on browser SpeechSynthesis only')

if flag('TTS_LEGACY_GET_ENABLED','false'):
    errors.append('TTS_LEGACY_GET_ENABLED must be false for pilot privacy')
if env('TTS_CACHE_PERSISTENCE','ephemeral').lower() != 'ephemeral':
    findings.append('TTS_CACHE_PERSISTENCE is not ephemeral; persistent audio cache should receive explicit privacy approval')
for name, low, high, default in (('DB_CONNECT_TIMEOUT_SECONDS',1,30,5),('DB_STATEMENT_TIMEOUT_MS',500,60000,5000),('DB_READY_MAX_LATENCY_MS',50,10000,1500),('AUDIT_RETENTION_DAYS',7,3650,180),('OPERATIONAL_EVENT_RETENTION_DAYS',1,365,30),('NUDGE_RETENTION_DAYS',7,365,60),('MAINTENANCE_INTERVAL_SECONDS',3600,604800,21600),('PILOT_DAILY_XP_CAP',100,100000,2500),('PILOT_DAILY_GAME_START_CAP',10,10000,150),('PILOT_DAILY_TTS_CAP',20,10000,500),('PILOT_DAILY_PRACTICE_CAP',20,10000,300),('PILOT_USAGE_RETENTION_DAYS',14,730,90)):
    try:
        value=int(env(name,str(default)))
        if not low <= value <= high: errors.append(f'{name} must be between {low} and {high}')
    except ValueError:
        errors.append(f'{name} must be an integer')
print('MGC Languages v5.7 pilot preflight')
for x in findings: print('WARN:',x)
for x in errors: print('ERROR:',x)
if errors: sys.exit(2)
print('PASS: configuration passed blocking preflight checks')
