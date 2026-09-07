"""Environment-driven configuration for MGC Languages.

Extracted from app.py in v5.7.3 without changing defaults or validation bounds.
"""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"
APP_VERSION = os.getenv("APP_VERSION", "5.7.1").strip() or "5.7.1"
INSTANCE_ID = os.getenv("INSTANCE_ID", os.getenv("HOSTNAME", "local")).strip() or "local"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'mgc.db'}")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
AUTH_MODE = os.getenv("AUTH_MODE", "local").strip().lower()
REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "true").lower() == "true"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").strip().lower() if os.getenv("COOKIE_SAMESITE", "lax").strip().lower() in {"lax", "strict", "none"} else "lax"
SESSION_TTL_HOURS = max(1, min(24 * 30, int(os.getenv("SESSION_TTL_HOURS", "168"))))
MAX_IMPORT_BYTES = max(1024, int(os.getenv("MAX_IMPORT_BYTES", str(5 * 1024 * 1024))))
READY_REQUIRE_POSTGRES = os.getenv("READY_REQUIRE_POSTGRES", "false").lower() == "true"
READY_REQUIRE_SCHEMA_HEAD = os.getenv("READY_REQUIRE_SCHEMA_HEAD", "true" if APP_ENV in {"pilot", "production"} else "false").lower() == "true"
READY_REQUIRE_REGISTRATION_DISABLED = os.getenv("READY_REQUIRE_REGISTRATION_DISABLED", "false").lower() == "true"
READY_REQUIRE_METRICS_TOKEN = os.getenv("READY_REQUIRE_METRICS_TOKEN", "false").lower() == "true"
READY_REQUIRE_OIDC = os.getenv("READY_REQUIRE_OIDC", "false").lower() == "true"
READY_REQUIRE_SECURE_COOKIE = os.getenv("READY_REQUIRE_SECURE_COOKIE", "false").lower() == "true"
READY_REQUIRE_RLS = os.getenv("READY_REQUIRE_RLS", "true" if APP_ENV in {"pilot", "production"} else "false").lower() == "true"
READY_REQUIRE_TERM_APPROVAL = os.getenv("READY_REQUIRE_TERM_APPROVAL", "true" if APP_ENV in {"pilot", "production"} else "false").lower() == "true"
EXPECTED_ALEMBIC_HEAD = os.getenv("EXPECTED_ALEMBIC_HEAD", "c57d0a31f570").strip() or "c57d0a31f570"
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")
MAX_IMPORT_ROWS = max(1, min(20000, int(os.getenv("MAX_IMPORT_ROWS", "5000"))))
MAX_XLSX_UNCOMPRESSED_BYTES = max(MAX_IMPORT_BYTES, int(os.getenv("MAX_XLSX_UNCOMPRESSED_BYTES", str(25 * 1024 * 1024))))
AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true"
TRUSTED_HOSTS = [x.strip() for x in os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if x.strip()]
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL", "").strip()
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "").strip()
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_SCOPE = os.getenv("OIDC_SCOPE", "openid profile email groups").strip()
OIDC_USERNAME_CLAIM = os.getenv("OIDC_USERNAME_CLAIM", "preferred_username").strip()
OIDC_DISPLAY_NAME_CLAIM = os.getenv("OIDC_DISPLAY_NAME_CLAIM", "name").strip()
OIDC_GROUPS_CLAIM = os.getenv("OIDC_GROUPS_CLAIM", "groups").strip()
OIDC_ADMIN_GROUP = os.getenv("OIDC_ADMIN_GROUP", "").strip()
OIDC_EDITOR_GROUP = os.getenv("OIDC_EDITOR_GROUP", "").strip()
OIDC_MANAGER_GROUP = os.getenv("OIDC_MANAGER_GROUP", "").strip()
OIDC_STATE_SECRET = os.getenv("OIDC_STATE_SECRET", "dev-only-change-me")
OIDC_DEPARTMENT_CLAIM = os.getenv("OIDC_DEPARTMENT_CLAIM", "department").strip()
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
TTS_MAX_CHARS = max(40, min(1000, int(os.getenv("TTS_MAX_CHARS", "300"))))
TTS_VOICE_CHINESE = os.getenv("TTS_VOICE_CHINESE", "zh").strip() or "zh"
TTS_VOICE_ENGLISH = os.getenv("TTS_VOICE_ENGLISH", "en-us").strip() or "en-us"
TTS_BINARY = os.getenv("TTS_BINARY", "").strip() or (shutil.which("espeak-ng") or shutil.which("espeak") or "")
TTS_TIMEOUT_SECONDS = max(2, min(30, int(os.getenv("TTS_TIMEOUT_SECONDS", "8"))))
TTS_CONCURRENCY = max(1, min(8, int(os.getenv("TTS_CONCURRENCY", "2"))))
TTS_FAILURE_THRESHOLD = max(1, min(20, int(os.getenv("TTS_FAILURE_THRESHOLD", "3"))))
TTS_CIRCUIT_COOLDOWN_SECONDS = max(5, min(300, int(os.getenv("TTS_CIRCUIT_COOLDOWN_SECONDS", "30"))))
TTS_HEALTH_TTL_SECONDS = max(5, min(300, int(os.getenv("TTS_HEALTH_TTL_SECONDS", "30"))))
TTS_DISK_CACHE_ENABLED = os.getenv("TTS_DISK_CACHE_ENABLED", "true").lower() == "true"
TTS_CACHE_DIR = Path(os.getenv("TTS_CACHE_DIR", "/tmp/mgc-tts-cache"))
TTS_DISK_CACHE_MAX_MB = max(8, min(1024, int(os.getenv("TTS_DISK_CACHE_MAX_MB", "128"))))
TTS_DISK_CACHE_TTL_HOURS = max(1, min(24 * 90, int(os.getenv("TTS_DISK_CACHE_TTL_HOURS", "168"))))
TTS_LEGACY_GET_ENABLED = os.getenv("TTS_LEGACY_GET_ENABLED", "true").lower() == "true"
_tts_cache_persistence_raw = os.getenv("TTS_CACHE_PERSISTENCE", "ephemeral" if APP_ENV in {"pilot", "production"} else "persistent").strip().lower()
TTS_CACHE_PERSISTENCE = _tts_cache_persistence_raw if _tts_cache_persistence_raw in {"ephemeral", "persistent"} else "ephemeral"

# v5.4 pilot reliability / retention controls. Values are deliberately explicit and environment-driven.
DB_CONNECT_TIMEOUT_SECONDS = max(1, min(30, int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5"))))
DB_STATEMENT_TIMEOUT_MS = max(500, min(60000, int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "5000"))))
DB_READY_MAX_LATENCY_MS = max(50, min(10000, int(os.getenv("DB_READY_MAX_LATENCY_MS", "1500"))))
AUDIT_RETENTION_DAYS = max(7, min(3650, int(os.getenv("AUDIT_RETENTION_DAYS", "180"))))
AUDIT_CHAIN_LOCK_ID = int(os.getenv("AUDIT_CHAIN_LOCK_ID", "5757001"))
OPERATIONAL_EVENT_RETENTION_DAYS = max(1, min(365, int(os.getenv("OPERATIONAL_EVENT_RETENTION_DAYS", "30"))))
NUDGE_RETENTION_DAYS = max(7, min(365, int(os.getenv("NUDGE_RETENTION_DAYS", "60"))))
MAINTENANCE_INTERVAL_SECONDS = max(3600, min(7 * 24 * 3600, int(os.getenv("MAINTENANCE_INTERVAL_SECONDS", "21600"))))

# v5.5 Pilot Operations. These are internal SLOs for a controlled pilot, not a contractual external SLA.
PILOT_SERVICE_WINDOW = os.getenv("PILOT_SERVICE_WINDOW", "business-hours").strip() or "business-hours"
PILOT_SLA_MODE = os.getenv("PILOT_SLA_MODE", "internal-non-contractual").strip() or "internal-non-contractual"
SLO_WINDOW_MINUTES = max(5, min(24 * 60, int(os.getenv("SLO_WINDOW_MINUTES", "60"))))
SLO_AVAILABILITY_TARGET_PERCENT = max(90.0, min(100.0, float(os.getenv("SLO_AVAILABILITY_TARGET_PERCENT", "99.0"))))
SLO_ERROR_RATE_TARGET_PERCENT = max(0.01, min(10.0, float(os.getenv("SLO_ERROR_RATE_TARGET_PERCENT", "1.0"))))
SLO_P95_TARGET_MS = max(50, min(60000, int(os.getenv("SLO_P95_TARGET_MS", "2000"))))
ALERT_ERROR_RATE_PERCENT = max(SLO_ERROR_RATE_TARGET_PERCENT, min(50.0, float(os.getenv("ALERT_ERROR_RATE_PERCENT", "2.0"))))
ALERT_P95_MS = max(SLO_P95_TARGET_MS, min(120000, int(os.getenv("ALERT_P95_MS", "3000"))))
ALERT_DB_LATENCY_MS = max(50, min(DB_READY_MAX_LATENCY_MS, int(os.getenv("ALERT_DB_LATENCY_MS", "1000"))))
ALERT_CLEANUP_BACKLOG = max(10, min(1000000, int(os.getenv("ALERT_CLEANUP_BACKLOG", "1000"))))
RECOVERY_STABLE_SECONDS = max(5, min(3600, int(os.getenv("RECOVERY_STABLE_SECONDS", "60"))))
ALERT_RETENTION_DAYS = max(7, min(3650, int(os.getenv("ALERT_RETENTION_DAYS", "90"))))

# v5.6 Pilot Governance & Rollout. Conservative defaults prevent accidental pilot abuse.
PILOT_DAILY_XP_CAP = max(100, min(100000, int(os.getenv("PILOT_DAILY_XP_CAP", "2500"))))
PILOT_DAILY_GAME_START_CAP = max(10, min(10000, int(os.getenv("PILOT_DAILY_GAME_START_CAP", "150"))))
PILOT_DAILY_TTS_CAP = max(20, min(10000, int(os.getenv("PILOT_DAILY_TTS_CAP", "500"))))
PILOT_DAILY_PRACTICE_CAP = max(20, min(10000, int(os.getenv("PILOT_DAILY_PRACTICE_CAP", "300"))))
PILOT_EXPORT_MAX_USERS = max(100, min(50000, int(os.getenv("PILOT_EXPORT_MAX_USERS", "10000"))))
PILOT_USAGE_RETENTION_DAYS = max(14, min(730, int(os.getenv("PILOT_USAGE_RETENTION_DAYS", "90"))))

# v5.7 Security, content integrity, observability and adaptive learning.
RLS_ENABLED = os.getenv("RLS_ENABLED", "true" if APP_ENV in {"pilot", "production"} else "false").lower() == "true"
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "false").lower() == "true"
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "mgc-languages").strip() or "mgc-languages"
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
OTEL_EXPORT_TIMEOUT_SECONDS = max(1, min(30, int(os.getenv("OTEL_EXPORT_TIMEOUT_SECONDS", "5"))))
SRS_DAILY_REVIEW_LIMIT = max(5, min(200, int(os.getenv("SRS_DAILY_REVIEW_LIMIT", "30"))))
QUESTION_QUALITY_MIN_ATTEMPTS = max(5, min(1000, int(os.getenv("QUESTION_QUALITY_MIN_ATTEMPTS", "20"))))
QUESTION_QUALITY_LOW_ACCURACY = max(0.05, min(0.90, float(os.getenv("QUESTION_QUALITY_LOW_ACCURACY", "0.35"))))
QUESTION_QUALITY_HIGH_ACCURACY = max(0.60, min(1.0, float(os.getenv("QUESTION_QUALITY_HIGH_ACCURACY", "0.97"))))
TERM_APPROVAL_REQUIRED = os.getenv("TERM_APPROVAL_REQUIRED", "true" if APP_ENV in {"pilot", "production"} else "false").lower() == "true"

# v5.7.1 Observability & Recovery evidence. These controls are operational and do not replace readiness.
DB_POOL_SIZE = max(1, min(100, int(os.getenv("DB_POOL_SIZE", "5"))))
DB_MAX_OVERFLOW = max(0, min(200, int(os.getenv("DB_MAX_OVERFLOW", "10"))))
DB_POOL_ALERT_PERCENT = max(10.0, min(100.0, float(os.getenv("DB_POOL_ALERT_PERCENT", "80"))))
DB_QUERY_WINDOW_MINUTES = max(1, min(120, int(os.getenv("DB_QUERY_WINDOW_MINUTES", "15"))))
DB_SLOW_QUERY_THRESHOLD_MS = max(25, min(60000, int(os.getenv("DB_SLOW_QUERY_THRESHOLD_MS", "500"))))
DB_SLOW_QUERY_ALERT_COUNT = max(1, min(10000, int(os.getenv("DB_SLOW_QUERY_ALERT_COUNT", "5"))))
BACKUP_EVIDENCE_DIR = Path(os.getenv("BACKUP_EVIDENCE_DIR", "/backups"))
WAL_ARCHIVE_DIR = Path(os.getenv("WAL_ARCHIVE_DIR", "/wal_archive"))
BACKUP_MAX_AGE_MINUTES = max(30, min(60 * 24 * 30, int(os.getenv("BACKUP_MAX_AGE_MINUTES", "1560"))))
RESTORE_EVIDENCE_MAX_AGE_DAYS = max(1, min(365, int(os.getenv("RESTORE_EVIDENCE_MAX_AGE_DAYS", "30"))))
RPO_TARGET_MINUTES = max(1, min(60 * 24 * 30, int(os.getenv("RPO_TARGET_MINUTES", "1440"))))
RTO_TARGET_MINUTES = max(1, min(60 * 24, int(os.getenv("RTO_TARGET_MINUTES", "60"))))
RECOVERY_EVIDENCE_REQUIRED = os.getenv("RECOVERY_EVIDENCE_REQUIRED", "false").lower() == "true"

BUILTIN_FEATURE_FLAGS = {
    "games": {"title":"Мини-игры", "description":"Word Match, Listening, Phrase Builder, Find the Mistake", "default_enabled":True},
    "xp_economy": {"title":"XP и помощь", "description":"Расходуемый XP, подсказки и персональные пакеты", "default_enabled":True},
    "learning_nudges": {"title":"Мягкие напоминания", "description":"Learning Nudge Engine без давления", "default_enabled":True},
    "chinese_reference": {"title":"Информация о китайском", "description":"Pinyin, тоны, Путунхуа и справка о диалектах", "default_enabled":True},
    "server_audio": {"title":"Серверное аудио", "description":"Offline TTS; browser voice остаётся fallback", "default_enabled":True},
    "ai_assistant": {"title":"ИИ-помощник", "description":"Дополнительный AI/RAG учебный помощник", "default_enabled":True},
}
