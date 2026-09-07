import { timingSafeEqual } from "node:crypto";
import { prometheusMetrics } from "@/lib/metrics";
import { createRequestContext, contextHeaders } from "@/lib/request-context";
import { loadRuntimeConfig } from "@/lib/runtime-config";

export const dynamic = "force-dynamic";

function safeEqual(left: string, right: string) {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const expected = process.env.METRICS_TOKEN?.trim();
  if (expected) {
    const supplied = request.headers.get("authorization")?.replace(/^Bearer\s+/iu, "").trim() || "";
    if (!supplied || !safeEqual(supplied, expected)) return new Response("not found\n", { status: 404, headers: contextHeaders(context) });
  }
  const runtime = await loadRuntimeConfig();
  return new Response(prometheusMetrics(runtime.sources), {
    headers: contextHeaders(context, {
      "content-type": "text/plain; version=0.0.4; charset=utf-8",
      "cache-control": "no-store",
    }),
  });
}
