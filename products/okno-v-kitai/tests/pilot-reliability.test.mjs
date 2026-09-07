import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFile } from "node:fs/promises";
import test from "node:test";
async function text(path){return readFile(new URL(`../${path}`,import.meta.url),"utf8")}
test("Node runtime provides SQLite required by v1.6",()=>{const db=new DatabaseSync(":memory:");db.exec("CREATE TABLE t(v INTEGER); INSERT INTO t VALUES(1)");assert.equal(db.prepare("SELECT v FROM t").get().v,1);db.close();});
test("v1.6 packages persistent cache and scheduler",async()=>{const pkg=JSON.parse(await text("package.json"));assert.equal(pkg.version,"1.6.1-pilot");assert.match(await text("lib/pilot-db.ts"),/source_snapshots/u);assert.match(await text("lib/source-cache.ts"),/stale_until/u);assert.match(await text("compose.yaml"),/china-auto-radar-scheduler/u);assert.match(await text("app/api/internal/refresh/route.ts"),/x-scheduler-token|isSchedulerRequest/u);});
test("managed content is audited and published through a separate public endpoint",async()=>{assert.match(await text("app/api/admin/content/route.ts"),/content\.upsert/u);assert.match(await text("app/api/content/route.ts"),/listContent/u);assert.match(await text("components/managed-content-panel.tsx"),/Корпоративные заметки/u);});
