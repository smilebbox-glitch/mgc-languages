import { writeAudit } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { importContentBundle, validateContentBundle } from "@/lib/content-store";
import { logSecurityEvent } from "@/lib/logger";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "editor", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "content-import", limit: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30), windowMs: 300_000, actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много изменений." }, { status: 429, headers: rateLimitHeaders(limit) });
  try {
    const raw = await request.text();
    if (Buffer.byteLength(raw, "utf8") > 1_048_576) throw new Error("Import превышает 1 МБ.");
    const bundle = validateContentBundle(JSON.parse(raw));
    const dryRun = new URL(request.url).searchParams.get("dryRun") === "1";
    const result = importContentBundle(bundle, auth.principal.subject, dryRun);
    if (!dryRun) {
      await writeAudit({ requestId: context.requestId, actor: auth.principal.subject, action: "content.import", target: "managed-content", outcome: "success", clientIp: context.clientIp, details: result });
      logSecurityEvent("managed_content_imported", { requestId: context.requestId, actor: auth.principal.subject, ...result });
    }
    return jsonWithContext(context, result, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
  } catch (error) {
    return jsonWithContext(context, { error: error instanceof Error ? error.message : "Не удалось импортировать контент." }, { status: 400, headers: rateLimitHeaders(limit) });
  }
}
