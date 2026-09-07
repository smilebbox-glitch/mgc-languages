import { logSecurityEvent } from "@/lib/logger";
import { recordRateLimit } from "@/lib/metrics";
import type { RequestContext } from "@/lib/request-context";

type Bucket = { startedAt: number; count: number };
type Store = Map<string, Bucket>;

const globalRateLimit = globalThis as typeof globalThis & { __oknoRateLimit?: Store };
const store = globalRateLimit.__oknoRateLimit ?? new Map<string, Bucket>();
globalRateLimit.__oknoRateLimit = store;

function clean(now: number, windowMs: number) {
  if (store.size < 5000) return;
  for (const [key, bucket] of store) {
    if (now - bucket.startedAt > windowMs * 2) store.delete(key);
  }
}

export type RateLimitResult = {
  allowed: boolean;
  limit: number;
  remaining: number;
  retryAfterSeconds: number;
};

export function checkRateLimit(args: {
  context: RequestContext;
  scope: string;
  limit: number;
  windowMs?: number;
  actor?: string;
}): RateLimitResult {
  const windowMs = args.windowMs ?? 60_000;
  const now = Date.now();
  const identity = (args.actor || args.context.clientIp || "unknown").slice(0, 180);
  const key = `${args.scope}:${identity}`;
  let bucket = store.get(key);
  if (!bucket || now - bucket.startedAt >= windowMs) {
    bucket = { startedAt: now, count: 0 };
    store.set(key, bucket);
  }
  bucket.count += 1;
  clean(now, windowMs);
  const allowed = bucket.count <= args.limit;
  const remaining = Math.max(0, args.limit - bucket.count);
  const retryAfterSeconds = Math.max(1, Math.ceil((windowMs - (now - bucket.startedAt)) / 1000));
  if (!allowed) {
    recordRateLimit(args.scope);
    logSecurityEvent("rate_limit_exceeded", {
      outcome: "blocked",
      requestId: args.context.requestId,
      actor: identity,
      scope: args.scope,
      path: args.context.path,
      clientIp: args.context.clientIp,
      limit: args.limit,
      windowMs,
    });
  }
  return { allowed, limit: args.limit, remaining, retryAfterSeconds };
}

export function rateLimitHeaders(result: RateLimitResult) {
  return {
    "x-ratelimit-limit": String(result.limit),
    "x-ratelimit-remaining": String(result.remaining),
    ...(result.allowed ? {} : { "retry-after": String(result.retryAfterSeconds) }),
  };
}

export function rateLimitPolicy() {
  return {
    implementation: "in-process-fixed-window",
    note: "Pilot single-instance limiter. Use a shared store/gateway limiter before multi-instance scale-out.",
    defaults: {
      readPerMinute: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120),
      expensivePerMinute: Number(process.env.RATE_LIMIT_EXPENSIVE_PER_MINUTE || 20),
      adminMutationPerFiveMinutes: Number(process.env.RATE_LIMIT_ADMIN_MUTATION_PER_5_MIN || 30),
    },
  };
}
