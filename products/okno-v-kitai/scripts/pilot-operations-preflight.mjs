import { access, readFile } from "node:fs/promises";

const failures = [];
const checks = [];
function check(condition, label) {
  const ok = Boolean(condition);
  checks.push({ label, ok });
  if (!ok) failures.push(label);
}

async function exists(path) {
  try { await access(path); return true; } catch { return false; }
}

const packageJson = JSON.parse(await readFile("package.json", "utf8"));
const compose = await readFile("compose.yaml", "utf8");
const env = await readFile(".env.example", "utf8");
const adminConfig = await readFile("app/api/admin/config/route.ts", "utf8");
const backup = await readFile("app/api/admin/backup/route.ts", "utf8");
const restore = await readFile("app/api/admin/restore/route.ts", "utf8");
const audit = await readFile("lib/audit.ts", "utf8");
const rateLimit = await readFile("lib/rate-limit.ts", "utf8");
const requestContext = await readFile("lib/request-context.ts", "utf8");
const backupLib = await readFile("lib/backup.ts", "utf8");

check(packageJson.version === "1.6.1-pilot", "package version is v1.6.1 pilot");
check(await exists("app/api/admin/audit/route.ts"), "admin audit endpoint exists");
check(await exists("app/api/admin/backup/route.ts"), "admin backup endpoint exists");
check(await exists("app/api/admin/restore/route.ts"), "admin restore endpoint exists");
check(audit.includes("previousHash") && audit.includes("HMAC-SHA256"), "audit trail has hash chaining and optional HMAC");
check(audit.includes("mode: 0o600"), "audit file is created with owner-only mode");
check(backupLib.includes("runtime: { sources") && !backupLib.includes("ADMIN_API_TOKEN") && !backupLib.includes("RAG_API_KEY"), "runtime backup excludes application secrets");
check(backup.includes("runtime.backup.export") && restore.includes("runtime.backup.restore"), "backup/restore operations are audited");
check(adminConfig.includes("runtime.sources.update") && adminConfig.includes("writeAudit"), "runtime source changes are audited");
check(rateLimit.includes("in-process-fixed-window") && rateLimit.includes("rate_limit_exceeded"), "pilot rate limiter and SIEM event exist");
check(requestContext.includes("randomUUID") && requestContext.includes("x-request-id"), "correlation request IDs are implemented");
check(compose.includes("AUDIT_HMAC_KEY") && compose.includes("RATE_LIMIT_EXPENSIVE_PER_MINUTE"), "compose exposes audit and rate-limit controls");
check(env.includes("AUDIT_HMAC_KEY=") && env.includes("RATE_LIMIT_READ_PER_MINUTE="), "environment template documents operations controls");
check(packageJson.scripts?.["pilot:preflight"]?.includes("pilot:sbom"), "single pilot preflight command includes SBOM generation");
check(packageJson.scripts?.["pilot:audit-deps"]?.includes("npm audit"), "online dependency vulnerability gate is defined");

for (const item of checks) console.log(`${item.ok ? "PASS" : "FAIL"}  ${item.label}`);
if (failures.length) {
  console.error(`\n${failures.length} operations preflight check(s) failed.`);
  process.exit(1);
}
console.log(`\n${checks.length}/${checks.length} operations preflight checks passed.`);
