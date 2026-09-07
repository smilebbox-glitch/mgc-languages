import { randomUUID } from "node:crypto";

export type RequestContext = {
  requestId: string;
  clientIp: string;
  userAgent: string;
  method: string;
  path: string;
};

const REQUEST_ID_RE = /^[A-Za-z0-9._:-]{8,80}$/u;

function safeHeader(value: string | null, max = 300) {
  return (value ?? "").replace(/[\r\n]/gu, " ").trim().slice(0, max);
}

export function createRequestContext(request: Request): RequestContext {
  const supplied = safeHeader(request.headers.get("x-request-id"), 80);
  const forwarded = safeHeader(request.headers.get("x-forwarded-for"), 200)
    .split(",")[0]
    ?.trim();
  const url = new URL(request.url);
  return {
    requestId: REQUEST_ID_RE.test(supplied) ? supplied : randomUUID(),
    clientIp: forwarded || safeHeader(request.headers.get("x-real-ip"), 80) || "unknown",
    userAgent: safeHeader(request.headers.get("user-agent"), 300),
    method: request.method.toUpperCase(),
    path: url.pathname,
  };
}

export function contextHeaders(context: RequestContext, values: HeadersInit = {}) {
  const headers = new Headers(values);
  headers.set("x-request-id", context.requestId);
  headers.set("x-content-type-options", "nosniff");
  return headers;
}

export function jsonWithContext(
  context: RequestContext,
  body: unknown,
  init: ResponseInit = {},
) {
  return Response.json(body, {
    ...init,
    headers: contextHeaders(context, init.headers),
  });
}
