import { auditStatus } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { externalSnapshot } from "@/lib/metrics";
import { outboundPolicy } from "@/lib/outbound";
import { checkRateLimit, rateLimitHeaders, rateLimitPolicy } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { loadRuntimeConfig, runtimeConfigPath } from "@/lib/runtime-config";
import { migrationStatus, pilotDbStatus } from "@/lib/pilot-db";
import { governancePolicy, schedulerLockStatus, sourceSlaStatus } from "@/lib/governance";
import { validatePilotConfiguration } from "@/lib/config-validation";
import { sourceReliabilitySummary } from "@/lib/source-cache";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "viewer", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const runtime = await loadRuntimeConfig();
  return jsonWithContext(
    context,
    {
      service: "okno-v-kitai",
      version: process.env.APP_VERSION || "1.6.1-pilot",
      time: new Date().toISOString(),
      uptimeSeconds: Math.round(process.uptime()),
      requestId: context.requestId,
      principal: auth.principal,
      auth: {
        mode: process.env.AUTH_MODE?.trim() === "proxy" ? "proxy" : "disabled",
        proxySecretConfigured: Boolean(process.env.AUTH_PROXY_SECRET?.trim()),
        adminTokenConfigured: Boolean(process.env.ADMIN_API_TOKEN?.trim()),
      },
      reliability: { database: pilotDbStatus(), schedulerConfigured: Boolean(process.env.SCHEDULER_TOKEN?.trim()), summary: sourceReliabilitySummary(50) },
      integrations: {
        ragConfigured: Boolean(process.env.RAG_API_URL?.trim() && process.env.RAG_MODEL?.trim()),
        runtimeConfigPath: runtimeConfigPath(),
        outbound: outboundPolicy(),
      },
      operations: {
        audit: auditStatus(),
        rateLimit: rateLimitPolicy(),
        backup: { format: "okno-v-kitai-runtime-backup", schema: 2, secretsIncluded: false },
        governance: { policy: governancePolicy(), migrations: migrationStatus(), locks: schedulerLockStatus(), sla: sourceSlaStatus(), validation: validatePilotConfiguration() },
      },
      runtime,
      external: externalSnapshot(),
      process: {
        node: process.version,
        pid: process.pid,
        memory: process.memoryUsage(),
      },
    },
    { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } },
  );
}
