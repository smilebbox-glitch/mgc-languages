import assert from "node:assert/strict";
import test from "node:test";
import { DatabaseSync } from "node:sqlite";
import { readFile } from "node:fs/promises";

const text=(p)=>readFile(p,"utf8");

test("SQLite supports the governance locking primitives required by v1.6",()=>{
  const db=new DatabaseSync(":memory:");
  db.exec("CREATE TABLE scheduler_locks(lock_name TEXT PRIMARY KEY, owner TEXT NOT NULL, acquired_at TEXT NOT NULL, expires_at TEXT NOT NULL)");
  const now=new Date().toISOString();
  const future=new Date(Date.now()+60000).toISOString();
  const r=db.prepare("INSERT INTO scheduler_locks VALUES(?,?,?,?)").run("refresh","a",now,future);
  assert.equal(Number(r.changes),1);
  assert.equal(db.prepare("SELECT owner FROM scheduler_locks WHERE lock_name='refresh'").get().owner,"a");
  db.close();
});

test("v1.6 governance controls are packaged",async()=>{
  const pkg=JSON.parse(await text("package.json"));
  assert.equal(pkg.version,"1.6.1-pilot");
  assert.match(await text("lib/pilot-db.ts"),/schema_migrations/u);
  assert.match(await text("lib/governance.ts"),/acquireSchedulerLock/u);
  assert.match(await text("lib/runtime-config.ts"),/maintenance/u);
  assert.match(await text("lib/content-store.ts"),/okno-v-kitai-managed-content/u);
  assert.match(await text("scripts/generate-acceptance-report.mjs"),/IT_ACCEPTANCE_REPORT/u);
});
