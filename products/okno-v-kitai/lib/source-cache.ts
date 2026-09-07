import { createHash } from "node:crypto";
import { getPilotDb } from "@/lib/pilot-db";

export type CacheState = "fresh" | "stale" | "expired" | "miss";
export type SourceSnapshot<T> = {
  cacheKey: string;
  sourceKey: string;
  scope: string;
  payload: T;
  fetchedAt: string;
  expiresAt: string;
  staleUntil: string;
  status: string;
  qualityScore: number;
  itemCount: number;
  error: string;
  state: CacheState;
  ageSeconds: number;
};

type SaveSnapshotInput<T> = {
  cacheKey: string;
  sourceKey: string;
  scope?: string;
  payload: T;
  ttlMs: number;
  staleMs: number;
  status: string;
  qualityScore: number;
  itemCount?: number;
  error?: string;
  latencyMs?: number;
};

function nowIso(ms = Date.now()) { return new Date(ms).toISOString(); }
function clampScore(value: number) { return Math.max(0, Math.min(100, Math.round(value))); }

export function getSourceSnapshot<T>(cacheKey: string): SourceSnapshot<T> | null {
  const db = getPilotDb();
  const row = db.prepare("SELECT * FROM source_snapshots WHERE cache_key = ?").get(cacheKey) as Record<string, unknown> | undefined;
  if (!row) return null;
  const now = Date.now();
  const expires = Date.parse(String(row.expires_at));
  const staleUntil = Date.parse(String(row.stale_until));
  const fetched = Date.parse(String(row.fetched_at));
  let state: CacheState = "expired";
  if (Number.isFinite(expires) && now <= expires) state = "fresh";
  else if (Number.isFinite(staleUntil) && now <= staleUntil) state = "stale";
  let payload: T;
  try { payload = JSON.parse(String(row.payload_json)) as T; } catch { return null; }
  return {
    cacheKey: String(row.cache_key), sourceKey: String(row.source_key), scope: String(row.scope || ""), payload,
    fetchedAt: String(row.fetched_at), expiresAt: String(row.expires_at), staleUntil: String(row.stale_until),
    status: String(row.status), qualityScore: Number(row.quality_score || 0), itemCount: Number(row.item_count || 0),
    error: String(row.error || ""), state, ageSeconds: Number.isFinite(fetched) ? Math.max(0, Math.floor((now - fetched) / 1000)) : 0,
  };
}

export function saveSourceSnapshot<T>(input: SaveSnapshotInput<T>) {
  const db = getPilotDb();
  const fetchedMs = Date.now();
  const fetchedAt = nowIso(fetchedMs);
  const expiresAt = nowIso(fetchedMs + input.ttlMs);
  const staleUntil = nowIso(fetchedMs + input.ttlMs + input.staleMs);
  const payloadJson = JSON.stringify(input.payload);
  const score = clampScore(input.qualityScore);
  const error = (input.error || "").slice(0, 1000);
  const scope = input.scope || "";
  db.prepare(`INSERT INTO source_snapshots
      (cache_key, source_key, scope, payload_json, fetched_at, expires_at, stale_until, status, quality_score, item_count, error, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(cache_key) DO UPDATE SET source_key=excluded.source_key, scope=excluded.scope, payload_json=excluded.payload_json,
      fetched_at=excluded.fetched_at, expires_at=excluded.expires_at, stale_until=excluded.stale_until, status=excluded.status,
      quality_score=excluded.quality_score, item_count=excluded.item_count, error=excluded.error, updated_at=excluded.updated_at`)
    .run(input.cacheKey, input.sourceKey, scope, payloadJson, fetchedAt, expiresAt, staleUntil, input.status, score, input.itemCount || 0, error, fetchedAt);
  recordSourceRun({ sourceKey: input.sourceKey, scope, status: input.status, qualityScore: score, itemCount: input.itemCount || 0,
    latencyMs: input.latencyMs || 0, fetchedAt, error, payloadHash: createHash("sha256").update(payloadJson).digest("hex") });
  return { fetchedAt, expiresAt, staleUntil };
}

export function recordSourceRun(input: { sourceKey: string; scope?: string; status: string; qualityScore: number; itemCount?: number; latencyMs?: number; fetchedAt?: string; error?: string; payloadHash?: string }) {
  const db = getPilotDb();
  db.prepare(`INSERT INTO source_history (source_key, scope, status, quality_score, item_count, latency_ms, fetched_at, error, payload_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`)
    .run(input.sourceKey, input.scope || "", input.status, clampScore(input.qualityScore), input.itemCount || 0, input.latencyMs || 0,
      input.fetchedAt || nowIso(), (input.error || "").slice(0, 1000), input.payloadHash || "");
  const maxRows = Math.max(100, Math.min(1_000_000, Number(process.env.SOURCE_HISTORY_MAX_ROWS || 5000)));
  db.prepare(`DELETE FROM source_history WHERE id NOT IN (SELECT id FROM source_history ORDER BY id DESC LIMIT ?)` ).run(maxRows);
}

export function sourceReliabilitySummary(limit = 50) {
  const db = getPilotDb();
  const rows = db.prepare(`SELECT source_key, scope,
      COUNT(*) AS runs,
      ROUND(AVG(quality_score),1) AS avg_quality,
      SUM(CASE WHEN status IN ('success','live','partial') THEN 1 ELSE 0 END) AS successful_runs,
      MAX(fetched_at) AS last_run,
      MAX(CASE WHEN status IN ('success','live','partial') THEN fetched_at ELSE '' END) AS last_success
    FROM (SELECT * FROM source_history ORDER BY id DESC LIMIT ?) GROUP BY source_key, scope ORDER BY source_key, scope`).all(limit) as Array<Record<string, unknown>>;
  const snapshots = db.prepare(`SELECT cache_key, source_key, scope, fetched_at, expires_at, stale_until, status, quality_score, item_count, error FROM source_snapshots ORDER BY source_key, scope`).all() as Array<Record<string, unknown>>;
  return {
    sources: rows.map((row) => ({ sourceKey: String(row.source_key), scope: String(row.scope || ""), runs: Number(row.runs || 0), avgQuality: Number(row.avg_quality || 0), successfulRuns: Number(row.successful_runs || 0), lastRun: String(row.last_run || ""), lastSuccess: String(row.last_success || "") })),
    snapshots: snapshots.map((row) => {
      const fetched = Date.parse(String(row.fetched_at));
      const expires = Date.parse(String(row.expires_at));
      const stale = Date.parse(String(row.stale_until));
      const now = Date.now();
      return { cacheKey: String(row.cache_key), sourceKey: String(row.source_key), scope: String(row.scope || ""), fetchedAt: String(row.fetched_at), expiresAt: String(row.expires_at), staleUntil: String(row.stale_until), status: String(row.status), qualityScore: Number(row.quality_score || 0), itemCount: Number(row.item_count || 0), error: String(row.error || ""), state: now <= expires ? "fresh" : now <= stale ? "stale" : "expired", ageSeconds: Number.isFinite(fetched) ? Math.max(0, Math.floor((now - fetched) / 1000)) : 0 };
    }),
  };
}

export function pruneExpiredSnapshots() {
  const db = getPilotDb();
  const result = db.prepare("DELETE FROM source_snapshots WHERE stale_until < ?").run(nowIso());
  return Number(result.changes || 0);
}
