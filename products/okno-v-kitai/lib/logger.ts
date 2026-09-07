type LogLevel = "info" | "warn" | "error";

function sanitize(value: unknown): unknown {
  if (value instanceof Error) return { name: value.name, message: value.message.slice(0, 500) };
  if (typeof value === "string") return value.slice(0, 2000);
  if (Array.isArray(value)) return value.slice(0, 50).map(sanitize);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => !/(token|secret|password|authorization|api[_-]?key)/iu.test(key))
        .slice(0, 50)
        .map(([key, item]) => [key, sanitize(item)]),
    );
  }
  return value;
}

export function logEvent(level: LogLevel, event: string, fields: Record<string, unknown> = {}) {
  const record = JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    service: "okno-v-kitai",
    version: process.env.APP_VERSION || "1.4.0-pilot",
    event,
    ...(sanitize(fields) as Record<string, unknown>),
  });
  if (level === "error") console.error(record);
  else if (level === "warn") console.warn(record);
  else console.log(record);
}

export function logSecurityEvent(event: string, fields: Record<string, unknown> = {}) {
  const outcome = typeof fields.outcome === "string" ? fields.outcome : "unknown";
  const level: LogLevel = outcome === "failure" || outcome === "blocked" ? "warn" : "info";
  logEvent(level, event, {
    eventCategory: "security",
    eventKind: "event",
    ...fields,
  });
}
