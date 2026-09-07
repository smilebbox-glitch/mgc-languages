import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function text(path) { return readFile(new URL(`../${path}`, import.meta.url), "utf8"); }

test("v1.6 operations endpoints and controls are packaged", async () => {
  const pkg = JSON.parse(await text("package.json"));
  assert.equal(pkg.version, "1.6.1-pilot");
  assert.match(await text("app/api/admin/audit/route.ts"), /readAuditTail/u);
  assert.match(await text("app/api/admin/backup/route.ts"), /runtime\.backup\.export/u);
  assert.match(await text("app/api/admin/restore/route.ts"), /runtime\.backup\.restore/u);
  assert.match(await text("lib/request-context.ts"), /x-request-id/u);
  assert.match(await text("lib/rate-limit.ts"), /rate_limit_exceeded/u);
});

test("runtime backup implementation does not reference known secret variables", async () => {
  const backup = await text("lib/backup.ts");
  for (const secret of ["ADMIN_API_TOKEN", "AUTH_PROXY_SECRET", "METRICS_TOKEN", "RAG_API_KEY", "AUDIT_HMAC_KEY"]) {
    assert.equal(backup.includes(secret), false, `${secret} must not be in runtime backup implementation`);
  }
});

test("container remains hardened while /data is the only persistent writable volume", async () => {
  const compose = await text("compose.yaml");
  assert.match(compose, /read_only: true/u);
  assert.match(compose, /cap_drop:\s*\n\s*- ALL/u);
  assert.match(compose, /okno-runtime-data:\/data/u);
  assert.match(compose, /AUDIT_LOG_PATH: \/data\/audit\/audit\.jsonl/u);
});
