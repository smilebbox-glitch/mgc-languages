import { listContent } from "@/lib/content-store";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const limit = checkRateLimit({ context, scope: "content-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120) });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const section = new URL(request.url).searchParams.get("section")?.trim().slice(0, 80) || undefined;
  return jsonWithContext(context, { items: listContent(section, false), updatedAt: new Date().toISOString() }, { headers: { "cache-control": "private, max-age=60", ...rateLimitHeaders(limit) } });
}
