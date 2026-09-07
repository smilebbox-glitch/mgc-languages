import { acquireSchedulerLock, applyRetentionPolicies, releaseSchedulerLock } from "@/lib/governance";
import { logEvent } from "@/lib/logger";
import { isSchedulerRequest } from "@/lib/internal-auth";
import { applyUserRetention, generateUserNotifications } from "@/lib/user-store";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!isSchedulerRequest(request)) return Response.json({ error: "forbidden" }, { status: 403 });
  const lock = acquireSchedulerLock("source-refresh");
  if (!lock.acquired) {
    logEvent("info", "scheduler_refresh_skipped_lock_held", { lockName: lock.lockName });
    return Response.json({ ok: true, skipped: true, reason: "lock-held", time: new Date().toISOString() }, { headers: { "cache-control": "no-store" } });
  }
  const token = process.env.SCHEDULER_TOKEN?.trim() || "";
  const base = process.env.INTERNAL_APP_URL?.trim() || "http://127.0.0.1:3000";
  const targets = ["/api/fx?city=kaluga&refresh=1", "/api/fx?city=moskva&refresh=1", "/api/news?refresh=1"];
  const started = Date.now();
  try {
    const results = await Promise.all(targets.map(async (path) => {
      try {
        const response = await fetch(`${base}${path}`, { headers: { "x-scheduler-token": token }, signal: AbortSignal.timeout(25_000) });
        const body = await response.json().catch(() => ({}));
        return { path, ok: response.ok, status: response.status, cache: body?.cache?.state || body?.mode || "unknown" };
      } catch (error) {
        return { path, ok: false, status: 0, error: error instanceof Error ? error.message : "unknown" };
      }
    }));
    const retention = applyRetentionPolicies();
    const userRetention = applyUserRetention();
    const notifications = generateUserNotifications();
    const ok = results.every((item) => item.ok);
    logEvent(ok ? "info" : "warn", "scheduler_refresh_run", { ok, durationMs: Date.now() - started, results, retention, userRetention, notifications });
    return Response.json({ ok, durationMs: Date.now() - started, retention, userRetention, notifications, results, time: new Date().toISOString() }, { status: ok ? 200 : 207, headers: { "cache-control": "no-store" } });
  } finally {
    releaseSchedulerLock(lock.lockName, lock.owner);
  }
}
