import { authorize } from "@/lib/auth";
import { contentCounts } from "@/lib/content-store";
import { governancePolicy, schedulerLockStatus, sourceSlaStatus } from "@/lib/governance";
import { migrationStatus } from "@/lib/pilot-db";
import { pilotDbStatus } from "@/lib/pilot-db";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { sourceReliabilitySummary } from "@/lib/source-cache";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "viewer", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-reliability-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const reliability = sourceReliabilitySummary(200);
  const expired = reliability.snapshots.filter((item) => item.state === "expired").length;
  const stale = reliability.snapshots.filter((item) => item.state === "stale").length;
  const serviceLevel = expired ? "DEGRADED" : stale ? "STALE" : reliability.snapshots.length ? "HEALTHY" : "WARMING_UP";
  return jsonWithContext(context, {
    serviceLevel,
    database: pilotDbStatus(),
    scheduler: { configured: Boolean(process.env.SCHEDULER_TOKEN?.trim()), intervalSeconds: Number(process.env.SCHEDULER_INTERVAL_SECONDS || 300), locks: schedulerLockStatus() },
    governance: { policy: governancePolicy(), migrations: migrationStatus(), sla: sourceSlaStatus() },
    content: contentCounts(),
    reliability,
    time: new Date().toISOString(),
  }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
}
