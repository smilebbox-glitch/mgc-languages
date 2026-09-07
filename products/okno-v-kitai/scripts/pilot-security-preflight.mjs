import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";

const failures = [];
const checks = [];
function check(condition, label) {
  checks.push({ label, ok: Boolean(condition) });
  if (!condition) failures.push(label);
}

const compose = await readFile("compose.yaml", "utf8");
check(compose.includes("read_only: true"), "compose read-only root filesystem");
check(compose.includes("no-new-privileges:true"), "compose no-new-privileges");
check(compose.includes("cap_drop:\n      - ALL"), "compose drops all capabilities");
check(compose.includes("127.0.0.1"), "compose localhost bind default");
check(compose.includes("okno-runtime-data:/data"), "runtime config has dedicated volume");
check(compose.includes("/api/ready"), "healthcheck uses readiness endpoint");

const env = await readFile(".env.example", "utf8");
check(env.includes("AUTH_MODE=disabled"), "auth mode is explicit");
check(env.includes("AUTH_PROXY_SECRET="), "trusted proxy secret configurable");
check(env.includes("METRICS_TOKEN="), "metrics protection configurable");
check(env.includes("OUTBOUND_ALLOWLIST="), "outbound allow-list configurable");

async function collect(dir) {
  const result = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) result.push(...await collect(path));
    else if (/\.(ts|tsx)$/u.test(entry.name)) result.push(path);
  }
  return result;
}
const sourceFiles = [...await collect("app"), ...await collect("lib")];
const directFetch = [];
for (const file of sourceFiles) {
  const text = await readFile(file, "utf8");
  const internalLoopbackException = file === "app/api/internal/refresh/route.ts";
  if (file !== "lib/outbound.ts" && !internalLoopbackException && /\bfetch\s*\(/u.test(text)) directFetch.push(file);
}
check(directFetch.length === 0, `all external server fetch calls centralized; only internal refresh loopback is excepted${directFetch.length ? `: ${directFetch.join(", ")}` : ""}`);

for (const item of checks) console.log(`${item.ok ? "PASS" : "FAIL"}  ${item.label}`);
if (failures.length) {
  console.error(`\n${failures.length} security preflight check(s) failed.`);
  process.exit(1);
}
console.log(`\n${checks.length}/${checks.length} security preflight checks passed.`);
