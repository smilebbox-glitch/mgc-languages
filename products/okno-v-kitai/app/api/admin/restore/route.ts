import { writeAudit } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { restoreRuntimeBackup, validateRuntimeBackup } from "@/lib/backup";
import { logSecurityEvent } from "@/lib/logger";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "admin", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-restore", limit: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30), windowMs: 300_000, actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  try {
    const contentLength = Number(request.headers.get("content-length") || 0);
    if (contentLength > 262_144) {
      return jsonWithContext(context, { error: "Backup слишком большой." }, { status: 413, headers: rateLimitHeaders(limit) });
    }
    const backup = validateRuntimeBackup(await request.json());
    const runtime = await restoreRuntimeBackup(backup, auth.principal.subject);
    await writeAudit({
      requestId: context.requestId,
      actor: auth.principal.subject,
      action: "runtime.backup.restore",
      target: "runtime-config",
      outcome: "success",
      clientIp: context.clientIp,
      details: { backupCreatedAt: backup.createdAt, backupAppVersion: backup.appVersion },
    });
    logSecurityEvent("runtime_backup_restored", { outcome: "success", requestId: context.requestId, actor: auth.principal.subject });
    return jsonWithContext(context, { runtime }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
  } catch (error) {
    await writeAudit({
      requestId: context.requestId,
      actor: auth.principal.subject,
      action: "runtime.backup.restore",
      target: "runtime-config",
      outcome: "failure",
      clientIp: context.clientIp,
      details: { error: error instanceof Error ? error.message : "unknown" },
    });
    logSecurityEvent("runtime_backup_restore_failed", { outcome: "failure", requestId: context.requestId, actor: auth.principal.subject });
    return jsonWithContext(context, { error: error instanceof Error ? error.message : "Некорректный backup." }, { status: 400, headers: rateLimitHeaders(limit) });
  }
}
