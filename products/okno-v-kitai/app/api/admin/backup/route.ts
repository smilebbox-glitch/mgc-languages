import { writeAudit } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { createRuntimeBackup } from "@/lib/backup";
import { logSecurityEvent } from "@/lib/logger";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, contextHeaders } from "@/lib/request-context";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "admin", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-backup", limit: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30), windowMs: 300_000, actor: auth.principal.subject });
  if (!limit.allowed) return new Response(JSON.stringify({ error: "Слишком много запросов." }), { status: 429, headers: contextHeaders(context, { "content-type": "application/json", ...rateLimitHeaders(limit) }) });
  const backup = await createRuntimeBackup(auth.principal.subject);
  await writeAudit({
    requestId: context.requestId,
    actor: auth.principal.subject,
    action: "runtime.backup.export",
    target: "runtime-config",
    outcome: "success",
    clientIp: context.clientIp,
    details: { backupSchema: backup.schema },
  });
  logSecurityEvent("runtime_backup_exported", { outcome: "success", requestId: context.requestId, actor: auth.principal.subject });
  const stamp = new Date().toISOString().replace(/[:.]/gu, "-");
  return new Response(`${JSON.stringify(backup, null, 2)}\n`, {
    headers: contextHeaders(context, {
      "content-type": "application/json; charset=utf-8",
      "content-disposition": `attachment; filename="okno-runtime-backup-${stamp}.json"`,
      "cache-control": "no-store",
      ...rateLimitHeaders(limit),
    }),
  });
}
