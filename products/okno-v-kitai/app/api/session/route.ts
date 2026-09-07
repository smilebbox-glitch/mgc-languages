import { resolvePrincipal } from "@/lib/auth";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { maintenanceState } from "@/lib/runtime-config";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const principal = resolvePrincipal(request);
  const maintenance = await maintenanceState();
  const limit = checkRateLimit({ context, scope: "session-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: principal.authenticated ? principal.subject : undefined });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  return jsonWithContext(
    context,
    {
      authenticated: principal.authenticated,
      subject: principal.subject,
      email: principal.email,
      groups: principal.groups,
      role: principal.role,
      mode: principal.mode,
      requestId: context.requestId,
      maintenance,
    },
    { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } },
  );
}
