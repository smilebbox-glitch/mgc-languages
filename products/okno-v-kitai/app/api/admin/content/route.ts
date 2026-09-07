import { writeAudit } from "@/lib/audit";
import { authorize } from "@/lib/auth";
import { archiveContent, listContent, upsertContent, type ContentStatus } from "@/lib/content-store";
import { logSecurityEvent } from "@/lib/logger";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "viewer", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-content-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120), actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const section = new URL(request.url).searchParams.get("section")?.trim().slice(0,80) || undefined;
  return jsonWithContext(context, { items: listContent(section, true) }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
}

export async function POST(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "editor", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-content-write", limit: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30), windowMs: 300_000, actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много изменений." }, { status: 429, headers: rateLimitHeaders(limit) });
  try {
    const body = await request.json() as { id?: string; section?: string; slug?: string; title?: string; body?: string; status?: ContentStatus; sortOrder?: number; metadata?: Record<string, unknown> };
    const item = upsertContent({ id: body.id, section: body.section || "travel-guide", slug: body.slug || "", title: body.title || "", body: body.body || "", status: body.status || "draft", sortOrder: body.sortOrder, metadata: body.metadata, actor: auth.principal.subject });
    await writeAudit({ requestId: context.requestId, actor: auth.principal.subject, action: "content.upsert", target: item.slug, outcome: "success", clientIp: context.clientIp, details: { id: item.id, section: item.section, status: item.status } });
    logSecurityEvent("managed_content_updated", { outcome: "success", requestId: context.requestId, actor: auth.principal.subject, contentId: item.id });
    return jsonWithContext(context, { item }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
  } catch (error) {
    return jsonWithContext(context, { error: error instanceof Error ? error.message : "Не удалось сохранить контент." }, { status: 400, headers: rateLimitHeaders(limit) });
  }
}

export async function DELETE(request: Request) {
  const context = createRequestContext(request);
  const auth = authorize(request, "editor", context.requestId);
  if (auth.response) return auth.response;
  const limit = checkRateLimit({ context, scope: "admin-content-write", limit: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30), windowMs: 300_000, actor: auth.principal.subject });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много изменений." }, { status: 429, headers: rateLimitHeaders(limit) });
  const id = new URL(request.url).searchParams.get("id")?.trim() || "";
  if (!id) return jsonWithContext(context, { error: "Нужен id." }, { status: 400, headers: rateLimitHeaders(limit) });
  const archived = archiveContent(id, auth.principal.subject);
  if (!archived) return jsonWithContext(context, { error: "Материал не найден." }, { status: 404, headers: rateLimitHeaders(limit) });
  await writeAudit({ requestId: context.requestId, actor: auth.principal.subject, action: "content.archive", target: id, outcome: "success", clientIp: context.clientIp });
  return jsonWithContext(context, { archived: true }, { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
}
