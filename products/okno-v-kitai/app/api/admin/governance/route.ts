import { writeAudit } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { validatePilotConfiguration } from "@/lib/config-validation";
import { governancePolicy, schedulerLockStatus, sourceSlaStatus } from "@/lib/governance";
import { migrationStatus } from "@/lib/pilot-db";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { loadRuntimeConfig, saveMaintenanceConfig } from "@/lib/runtime-config";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "viewer", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "governance-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const runtime = await loadRuntimeConfig();
  return jsonWithContext(context, { maintenance: runtime.maintenance, policy: governancePolicy(), migrations: migrationStatus(), locks: schedulerLockStatus(), sla: sourceSlaStatus(), validation: validatePilotConfiguration() }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
}

export async function PUT(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "admin", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "governance-write", limit: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30), windowMs: 300_000, actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много изменений." }, { status: 429, headers: rateLimitHeaders(limit) });
  try {
    const body = await request.json() as { maintenance?: { enabled?: boolean; message?: string } };
    if (!body.maintenance || typeof body.maintenance.enabled !== "boolean") throw new Error("Нужен maintenance.enabled boolean.");
    const runtime = await saveMaintenanceConfig({ enabled: body.maintenance.enabled, message: body.maintenance.message }, auth.principal.subject);
    await writeAudit({ requestId: context.requestId, actor: auth.principal.subject, action: "governance.maintenance.update", target: "runtime", outcome: "success", clientIp: context.clientIp, details: runtime.maintenance });
    return jsonWithContext(context, { maintenance: runtime.maintenance }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
  } catch (error) {
    return jsonWithContext(context, { error: error instanceof Error ? error.message : "Не удалось сохранить governance config." }, { status: 400, headers: rateLimitHeaders(limit) });
  }
}
