import { randomUUID } from "node:crypto";
import { hostname } from "node:os";
import { getPilotDb } from "@/lib/pilot-db";
import { sourceReliabilitySummary } from "@/lib/source-cache";

function intEnv(name: string, fallback: number, min: number, max: number) {
  const value = Number(process.env[name] || fallback);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(min, Math.min(max, Math.round(value)));
}

export function governancePolicy() {
  return {
    retention: {
      sourceHistoryDays: intEnv("SOURCE_HISTORY_RETENTION_DAYS", 30, 1, 3650),
      sourceHistoryMaxRows: intEnv("SOURCE_HISTORY_MAX_ROWS", 5000, 100, 1_000_000),
      expiredSnapshotDays: intEnv("EXPIRED_SNAPSHOT_RETENTION_DAYS", 7, 0, 3650),
      archivedContentDays: intEnv("ARCHIVED_CONTENT_RETENTION_DAYS", 365, 0, 3650),
    },
    scheduler: {
      lockTtlSeconds: intEnv("SCHEDULER_LOCK_TTL_SECONDS", 120, 30, 3600),
    },
    sla: {
      "fx.aggregate": { maxAgeSeconds: intEnv("SOURCE_SLA_FX_SECONDS", 1800, 60, 604800), minQuality: intEnv("SOURCE_SLA_FX_MIN_QUALITY", 60, 0, 100) },
      "news.aggregate": { maxAgeSeconds: intEnv("SOURCE_SLA_NEWS_SECONDS", 3600, 60, 604800), minQuality: intEnv("SOURCE_SLA_NEWS_MIN_QUALITY", 50, 0, 100) },
    },
  } as const;
}

export function applyRetentionPolicies() {
  const db = getPilotDb();
  const policy = governancePolicy().retention;
  const now = Date.now();
  const historyCutoff = new Date(now - policy.sourceHistoryDays * 86_400_000).toISOString();
  const snapshotCutoff = new Date(now - policy.expiredSnapshotDays * 86_400_000).toISOString();
  const archivedCutoff = new Date(now - policy.archivedContentDays * 86_400_000).toISOString();
  const oldHistory = db.prepare("DELETE FROM source_history WHERE fetched_at < ?").run(historyCutoff);
  const rowCap = db.prepare(`DELETE FROM source_history WHERE id NOT IN (SELECT id FROM source_history ORDER BY id DESC LIMIT ?)`)
    .run(policy.sourceHistoryMaxRows);
  const snapshots = db.prepare("DELETE FROM source_snapshots WHERE stale_until < ?").run(snapshotCutoff);
  const archived = policy.archivedContentDays > 0
    ? db.prepare("DELETE FROM content_items WHERE status='archived' AND updated_at < ?").run(archivedCutoff)
    : { changes: 0 };
  const locks = db.prepare("DELETE FROM scheduler_locks WHERE expires_at < ?").run(new Date().toISOString());
  return {
    sourceHistoryByAge: Number(oldHistory.changes || 0),
    sourceHistoryByRowCap: Number(rowCap.changes || 0),
    expiredSnapshots: Number(snapshots.changes || 0),
    archivedContent: Number(archived.changes || 0),
    expiredLocks: Number(locks.changes || 0),
    policy,
  };
}

export function acquireSchedulerLock(lockName = "source-refresh") {
  const db = getPilotDb();
  const policy = governancePolicy();
  const owner = `${hostname()}:${process.pid}:${randomUUID()}`;
  const now = new Date();
  const acquiredAt = now.toISOString();
  const expiresAt = new Date(now.getTime() + policy.scheduler.lockTtlSeconds * 1000).toISOString();
  const result = db.prepare(`INSERT INTO scheduler_locks(lock_name, owner, acquired_at, expires_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(lock_name) DO UPDATE SET owner=excluded.owner, acquired_at=excluded.acquired_at, expires_at=excluded.expires_at
    WHERE scheduler_locks.expires_at < excluded.acquired_at`).run(lockName, owner, acquiredAt, expiresAt);
  return { acquired: Number(result.changes || 0) > 0, lockName, owner, acquiredAt, expiresAt };
}

export function releaseSchedulerLock(lockName: string, owner: string) {
  const db = getPilotDb();
  const result = db.prepare("DELETE FROM scheduler_locks WHERE lock_name=? AND owner=?").run(lockName, owner);
  return Number(result.changes || 0) > 0;
}

export function schedulerLockStatus() {
  const db = getPilotDb();
  return (db.prepare("SELECT lock_name, owner, acquired_at, expires_at FROM scheduler_locks ORDER BY lock_name").all() as Array<Record<string, unknown>>)
    .map((row) => ({ lockName: String(row.lock_name), owner: String(row.owner), acquiredAt: String(row.acquired_at), expiresAt: String(row.expires_at), active: Date.parse(String(row.expires_at)) > Date.now() }));
}

export function sourceSlaStatus() {
  const policy = governancePolicy();
  const snapshots = sourceReliabilitySummary(200).snapshots;
  return Object.entries(policy.sla).flatMap(([sourceKey, rule]) => {
    const matches = snapshots.filter((item) => item.sourceKey === sourceKey);
    if (!matches.length) return [{ sourceKey, scope: "", status: "NO_DATA", ageSeconds: null, qualityScore: null, ...rule }];
    const latestByScope = new Map<string, (typeof matches)[number]>();
    for (const item of matches) {
      const current = latestByScope.get(item.scope);
      if (!current || Date.parse(item.fetchedAt) > Date.parse(current.fetchedAt)) latestByScope.set(item.scope, item);
    }
    return [...latestByScope.values()].map((item) => {
      const ageOk = item.ageSeconds <= rule.maxAgeSeconds;
      const qualityOk = item.qualityScore >= rule.minQuality;
      return { sourceKey, scope: item.scope, status: ageOk && qualityOk ? "MET" : "BREACHED", ageSeconds: item.ageSeconds, qualityScore: item.qualityScore, ...rule };
    });
  });
}
