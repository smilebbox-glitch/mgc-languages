import { writeAudit } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { logEvent, logSecurityEvent } from "@/lib/logger";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { loadRuntimeConfig, saveRuntimeConfig, sourceKeys, type SourceKey } from "@/lib/runtime-config";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "viewer", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const runtime = await loadRuntimeConfig();
  return jsonWithContext(context, { runtime, principal: auth.principal }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
}

export async function PUT(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "admin", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-config-write", limit: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30), windowMs: 300_000, actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много изменений конфигурации." }, { status: 429, headers: rateLimitHeaders(limit) });
  try {
    const before = await loadRuntimeConfig();
    const body = await request.json() as { sources?: Partial<Record<SourceKey, unknown>> };
    if (!body.sources || typeof body.sources !== "object") {
      return jsonWithContext(context, { error: "Нужен объект sources." }, { status: 400, headers: rateLimitHeaders(limit) });
    }
    const changes: Partial<Record<SourceKey, boolean>> = {};
    for (const key of sourceKeys) {
      const value = body.sources[key];
      if (typeof value === "boolean" && value !== before.sources[key]) changes[key] = value;
    }
    if (!Object.keys(changes).length) {
      return jsonWithContext(context, { runtime: before, unchanged: true }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
    }
    const runtime = await saveRuntimeConfig(changes, auth.principal.subject);
    await writeAudit({
      requestId: context.requestId,
      actor: auth.principal.subject,
      action: "runtime.sources.update",
      target: "runtime-config",
      outcome: "success",
      clientIp: context.clientIp,
      details: { changes },
    });
    logSecurityEvent("runtime_config_updated", { outcome: "success", requestId: context.requestId, actor: auth.principal.subject, changes });
    return jsonWithContext(context, { runtime }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
  } catch (error) {
    logEvent("error", "runtime_config_update_failed", { requestId: context.requestId, error });
    await writeAudit({
      requestId: context.requestId,
      actor: auth.principal.subject,
      action: "runtime.sources.update",
      target: "runtime-config",
      outcome: "failure",
      clientIp: context.clientIp,
      details: { error: error instanceof Error ? error.message : "unknown" },
    });
    return jsonWithContext(context, { error: "Не удалось сохранить настройки." }, { status: 500, headers: rateLimitHeaders(limit) });
  }
}
