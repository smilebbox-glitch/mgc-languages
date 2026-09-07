import { createHash, createHmac, randomUUID } from "node:crypto";
import { appendFile, mkdir, readFile, rename, rm, stat } from "node:fs/promises";
import { dirname } from "node:path";
import { logEvent } from "@/lib/logger";
import { recordAuditWrite } from "@/lib/metrics";

export type AuditOutcome = "success" | "failure" | "blocked";
export type AuditRecord = {
  schema: 1;
  timestamp: string;
  eventId: string;
  requestId: string;
  actor: string;
  action: string;
  target: string;
  outcome: AuditOutcome;
  clientIp?: string;
  details?: Record<string, unknown>;
  previousHash: string;
  hashAlgorithm: "HMAC-SHA256" | "SHA256";
  hash: string;
};

const auditPath = process.env.AUDIT_LOG_PATH?.trim() || "/data/audit/audit.jsonl";
const maxBytes = Math.max(1024 * 1024, Number(process.env.AUDIT_MAX_BYTES || 10 * 1024 * 1024));
const globalAudit = globalThis as typeof globalThis & { __oknoAuditQueue?: Promise<void> };

globalAudit.__oknoAuditQueue ??= Promise.resolve();

function clean(value: unknown): unknown {
  if (typeof value === "string") return value.slice(0, 1200);
  if (typeof value === "number" || typeof value === "boolean" || value === null) return value;
  if (Array.isArray(value)) return value.slice(0, 50).map(clean);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([key]) => !/(token|secret|password|authorization|api[_-]?key)/iu.test(key))
        .slice(0, 50)
        .map(([key, item]) => [key, clean(item)]),
    );
  }
  return String(value ?? "").slice(0, 500);
}

function hashPayload(payload: Omit<AuditRecord, "hash">, algorithm?: AuditRecord["hashAlgorithm"]) {
  const serialized = JSON.stringify(payload);
  const selected = algorithm ?? (process.env.AUDIT_HMAC_KEY?.trim() ? "HMAC-SHA256" : "SHA256");
  if (selected === "HMAC-SHA256") {
    const key = process.env.AUDIT_HMAC_KEY?.trim();
    if (!key) return { algorithm: selected, hash: "" };
    return { algorithm: selected, hash: createHmac("sha256", key).update(serialized).digest("hex") };
  }
  return { algorithm: "SHA256" as const, hash: createHash("sha256").update(serialized).digest("hex") };
}

async function lastRecord(path = auditPath): Promise<AuditRecord | null> {
  try {
    const text = await readFile(path, "utf8");
    const lines = text.trim().split("\n").filter(Boolean).reverse();
    for (const line of lines) {
      try { return JSON.parse(line) as AuditRecord; } catch { /* inspect earlier valid record */ }
    }
    return null;
  } catch {
    return null;
  }
}

async function rotateIfNeeded() {
  try {
    const info = await stat(auditPath);
    if (info.size < maxBytes) return;
    const rotated = `${auditPath}.1`;
    await rm(rotated, { force: true });
    await rename(auditPath, rotated);
  } catch {
    // File absent or rotation not required.
  }
}

async function appendAudit(args: {
  requestId: string;
  actor: string;
  action: string;
  target: string;
  outcome: AuditOutcome;
  clientIp?: string;
  details?: Record<string, unknown>;
}) {
  await mkdir(dirname(auditPath), { recursive: true });
  await rotateIfNeeded();
  const previous = await lastRecord() ?? await lastRecord(`${auditPath}.1`);
  const base = {
    schema: 1 as const,
    timestamp: new Date().toISOString(),
    eventId: randomUUID(),
    requestId: args.requestId.slice(0, 80),
    actor: args.actor.slice(0, 180),
    action: args.action.slice(0, 120),
    target: args.target.slice(0, 240),
    outcome: args.outcome,
    ...(args.clientIp ? { clientIp: args.clientIp.slice(0, 100) } : {}),
    ...(args.details ? { details: clean(args.details) as Record<string, unknown> } : {}),
    previousHash: previous?.hash ?? "GENESIS",
    hashAlgorithm: (process.env.AUDIT_HMAC_KEY?.trim() ? "HMAC-SHA256" : "SHA256") as "HMAC-SHA256" | "SHA256",
  };
  const { hash } = hashPayload(base);
  const record: AuditRecord = { ...base, hash };
  await appendFile(auditPath, `${JSON.stringify(record)}\n`, { encoding: "utf8", mode: 0o600 });
  recordAuditWrite();
  return record;
}

export function writeAudit(args: Parameters<typeof appendAudit>[0]) {
  const task = globalAudit.__oknoAuditQueue!.then(() => appendAudit(args).then(() => undefined));
  globalAudit.__oknoAuditQueue = task.catch((error) => {
    logEvent("error", "audit_write_failed", { error, action: args.action, requestId: args.requestId });
  });
  return task;
}

function verifyRecord(record: AuditRecord, expectedPrevious: string) {
  const { hash: _hash, ...base } = record;
  const calculated = hashPayload(base, record.hashAlgorithm).hash;
  return record.previousHash === expectedPrevious && calculated === record.hash;
}

export async function readAuditTail(limit = 50) {
  const bounded = Math.max(1, Math.min(200, limit));
  let records: AuditRecord[] = [];
  let parseErrors = 0;
  for (const path of [`${auditPath}.1`, auditPath]) {
    try {
      const text = await readFile(path, "utf8");
      for (const line of text.split("\n").filter(Boolean)) {
        try { records.push(JSON.parse(line) as AuditRecord); } catch { parseErrors += 1; }
      }
    } catch {
      // Optional files.
    }
  }
  let verified = parseErrors === 0;
  for (let index = 0; index < records.length; index += 1) {
    const expected = index === 0 ? records[index].previousHash : records[index - 1].hash;
    if (!verifyRecord(records[index], expected)) verified = false;
  }
  return { records: records.slice(-bounded), verified, parseErrors, path: auditPath };
}

export function auditStatus() {
  return {
    path: auditPath,
    maxBytes,
    integrity: process.env.AUDIT_HMAC_KEY?.trim() ? "hmac-sha256-chain" : "sha256-chain",
    hmacConfigured: Boolean(process.env.AUDIT_HMAC_KEY?.trim()),
  };
}
