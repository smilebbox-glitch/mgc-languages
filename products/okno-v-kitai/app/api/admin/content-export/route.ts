import { writeAudit } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { exportContentBundle } from "@/lib/content-store";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, contextHeaders, jsonWithContext } from "@/lib/request-context";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "editor", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "content-export", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const section = new URL(request.url).searchParams.get("section")?.trim().slice(0, 80) || undefined;
  const bundle = exportContentBundle(auth.principal.subject, section);
  await writeAudit({ requestId: context.requestId, actor: auth.principal.subject, action: "content.export", target: section || "all", outcome: "success", clientIp: context.clientIp, details: { items: bundle.items.length } });
  const stamp = new Date().toISOString().replace(/[:.]/gu, "-");
  return new Response(`${JSON.stringify(bundle, null, 2)}\n`, { headers: contextHeaders(context, { "content-type": "application/json; charset=utf-8", "content-disposition": `attachment; filename="okno-content-${stamp}.json"`, "cache-control": "no-store", ...rateLimitHeaders(limit) }) });
}
