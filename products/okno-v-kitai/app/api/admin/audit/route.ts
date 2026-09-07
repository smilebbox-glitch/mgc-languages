import { readAuditTail } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "admin", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const url = new URL(request.url);
  const requested = Number(url.searchParams.get("limit") || 50);
  const result = await readAuditTail(Number.isFinite(requested) ? requested : 50);
  return jsonWithContext(context, result, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
}
