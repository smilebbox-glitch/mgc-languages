import { mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { DatabaseSync } from "node:sqlite";

let database: DatabaseSync | null = null;
const dbPath = process.env.PILOT_DB_PATH?.trim() || "/data/okno.sqlite";

type Migration = { version: number; name: string; sql: string };

const migrations: Migration[] = [
  {
    version: 1,
    name: "reliability_content_base",
    sql: `
      CREATE TABLE IF NOT EXISTS source_snapshots (
        cache_key TEXT PRIMARY KEY,
        source_key TEXT NOT NULL,
        scope TEXT NOT NULL DEFAULT '',
        payload_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        stale_until TEXT NOT NULL,
        status TEXT NOT NULL,
        quality_score INTEGER NOT NULL,
        item_count INTEGER NOT NULL DEFAULT 0,
        error TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_source_snapshots_source ON source_snapshots(source_key, fetched_at DESC);

      CREATE TABLE IF NOT EXISTS source_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_key TEXT NOT NULL,
        scope TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL,
        quality_score INTEGER NOT NULL,
        item_count INTEGER NOT NULL DEFAULT 0,
        latency_ms INTEGER NOT NULL DEFAULT 0,
        fetched_at TEXT NOT NULL,
        error TEXT NOT NULL DEFAULT '',
        payload_hash TEXT NOT NULL DEFAULT ''
      );
      CREATE INDEX IF NOT EXISTS idx_source_history_source ON source_history(source_key, fetched_at DESC);

      CREATE TABLE IF NOT EXISTS content_items (
        id TEXT PRIMARY KEY,
        section TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('draft','published','archived')),
        sort_order INTEGER NOT NULL DEFAULT 100,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        updated_by TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_content_items_section ON content_items(section, status, sort_order, updated_at DESC);
    `,
  },
  {
    version: 2,
    name: "scheduler_governance",
    sql: `
      CREATE TABLE IF NOT EXISTS scheduler_locks (
        lock_name TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        acquired_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_scheduler_locks_expiry ON scheduler_locks(expires_at);
    `,
  },
  {
    version: 3,
    name: "user_business_operations",
    sql: `
      CREATE TABLE IF NOT EXISTS user_preferences (
        user_key TEXT PRIMARY KEY, subscriptions_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS user_favorites (
        user_key TEXT NOT NULL, item_type TEXT NOT NULL, item_id TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, PRIMARY KEY(user_key,item_type,item_id)
      );
      CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites(user_key,created_at DESC);
      CREATE TABLE IF NOT EXISTS user_trips (
        user_key TEXT PRIMARY KEY, trip_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS user_notifications (
        id TEXT PRIMARY KEY, user_key TEXT NOT NULL, event_key TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
        url TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, read_at TEXT, UNIQUE(user_key,event_key)
      );
      CREATE INDEX IF NOT EXISTS idx_user_notifications_user ON user_notifications(user_key,created_at DESC);
      CREATE TABLE IF NOT EXISTS usage_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_key TEXT NOT NULL, event_name TEXT NOT NULL, path TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_usage_events_time ON usage_events(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_usage_events_name ON usage_events(event_name,created_at DESC);
    `,
  },
];

export function pilotDbPath() {
  return dbPath;
}

function applyMigrations(db: DatabaseSync) {
  db.exec(`CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
  );`);
  const appliedRows = db.prepare("SELECT version FROM schema_migrations ORDER BY version").all() as Array<{ version: number }>;
  const applied = new Set(appliedRows.map((row) => Number(row.version)));
  for (const migration of migrations) {
    if (applied.has(migration.version)) continue;
    db.exec("BEGIN IMMEDIATE;");
    try {
      db.exec(migration.sql);
      db.prepare("INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)")
        .run(migration.version, migration.name, new Date().toISOString());
      db.exec("COMMIT;");
    } catch (error) {
      db.exec("ROLLBACK;");
      throw error;
    }
  }
}

function seedContent(db: DatabaseSync) {
  const now = new Date().toISOString();
  db.prepare(`INSERT OR IGNORE INTO content_items (id, section, slug, title, body, status, sort_order, metadata_json, created_at, updated_at, updated_by)
    VALUES (?, ?, ?, ?, ?, 'published', 50, '{}', ?, ?, 'system-seed')`)
    .run(
      "seed-travel-live-data",
      "travel-guide",
      "aktualnost-dannyh",
      "Проверяйте актуальность перед операцией",
      "Курсы валют, правила въезда, авиаперевозки и доступность сервисов меняются. Используйте дату обновления и источник в карточке, а перед оплатой или вылетом перепроверьте условия у официального поставщика.",
      now,
      now,
    );
}

export function getPilotDb() {
  if (database) return database;
  mkdirSync(dirname(dbPath), { recursive: true });
  const db = new DatabaseSync(dbPath);
  db.exec("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON; PRAGMA synchronous=NORMAL;");
  applyMigrations(db);
  seedContent(db);
  database = db;
  return db;
}

export function migrationStatus() {
  const db = getPilotDb();
  const rows = db.prepare("SELECT version, name, applied_at FROM schema_migrations ORDER BY version").all() as Array<Record<string, unknown>>;
  const current = rows.length ? Math.max(...rows.map((row) => Number(row.version || 0))) : 0;
  return {
    current,
    latest: migrations.at(-1)?.version || 0,
    pending: Math.max(0, (migrations.at(-1)?.version || 0) - current),
    applied: rows.map((row) => ({ version: Number(row.version), name: String(row.name), appliedAt: String(row.applied_at) })),
  };
}

export function pilotDbStatus() {
  try {
    const db = getPilotDb();
    const row = db.prepare("SELECT COUNT(*) AS count FROM source_snapshots").get() as { count?: number } | undefined;
    const content = db.prepare("SELECT COUNT(*) AS count FROM content_items").get() as { count?: number } | undefined;
    const users = db.prepare("SELECT COUNT(*) AS count FROM user_preferences").get() as { count?: number } | undefined;
    const migrationsState = migrationStatus();
    return {
      available: true,
      path: dbPath,
      snapshots: Number(row?.count || 0),
      contentItems: Number(content?.count || 0),
      userProfiles: Number(users?.count || 0),
      schemaVersion: migrationsState.current,
      schemaLatest: migrationsState.latest,
      migrationsPending: migrationsState.pending,
    };
  } catch (error) {
    return {
      available: false,
      path: dbPath,
      snapshots: 0,
      contentItems: 0,
      schemaVersion: 0,
      schemaLatest: migrations.at(-1)?.version || 0,
      migrationsPending: migrations.length,
      error: error instanceof Error ? error.message : "unknown",
    };
  }
}
