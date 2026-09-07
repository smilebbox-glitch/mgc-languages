import { access, readFile } from "node:fs/promises";
const checks=[]; const failures=[];
function check(v,label){const ok=Boolean(v);checks.push({ok,label});if(!ok)failures.push(label);}
async function exists(path){try{await access(path);return true}catch{return false}}
const pkg=JSON.parse(await readFile("package.json","utf8"));
const compose=await readFile("compose.yaml","utf8");
const db=await readFile("lib/pilot-db.ts","utf8");
const cache=await readFile("lib/source-cache.ts","utf8");
const fx=await readFile("app/api/fx/route.ts","utf8");
const news=await readFile("app/api/news/route.ts","utf8");
const internal=await readFile("app/api/internal/refresh/route.ts","utf8");
const content=await readFile("lib/content-store.ts","utf8");
check(pkg.version==="1.6.1-pilot","package version is v1.6.1 pilot");
check(db.includes("DatabaseSync")&&db.includes("journal_mode=WAL")&&db.includes("busy_timeout=5000"),"SQLite WAL persistent store configured");
check(db.includes("source_snapshots")&&db.includes("source_history")&&db.includes("content_items"),"reliability/content tables exist");
check(cache.includes('"fresh" | "stale" | "expired"')&&cache.includes("stale_until"),"fresh/stale/expired cache policy exists");
check(fx.includes("getSourceSnapshot")&&fx.includes("saveSourceSnapshot")&&fx.includes('mode: "stale"'),"FX persistent stale fallback exists");
check(news.includes("getSourceSnapshot")&&news.includes("saveSourceSnapshot"),"news persistent cache exists");
check(internal.includes("isSchedulerRequest")&&internal.includes("applyRetentionPolicies")&&internal.includes("acquireSchedulerLock"),"authenticated locked refresh orchestration exists");
check(await exists("scripts/scheduler-client.mjs"),"scheduler worker script exists");
check(compose.includes("china-auto-radar-scheduler")&&compose.includes("condition: service_healthy"),"separate scheduler service waits for healthy app");
check(compose.includes("PILOT_DB_PATH: /data/okno.sqlite")&&compose.includes("okno-runtime-data:/data"),"SQLite persists in /data volume");
check(await exists("app/api/admin/reliability/route.ts")&&await exists("components/reliability-console.tsx"),"reliability dashboard packaged");
check(await exists("app/api/admin/content/route.ts")&&content.includes("upsertContent")&&content.includes("archiveContent"),"managed content CRUD packaged");
check(await exists("app/api/content/route.ts")&&await exists("components/managed-content-panel.tsx"),"published managed content is exposed to user UI");
for(const item of checks) console.log(`${item.ok?"PASS":"FAIL"}  ${item.label}`);
if(failures.length){console.error(`\n${failures.length} reliability preflight check(s) failed.`);process.exit(1)}
console.log(`\n${checks.length}/${checks.length} reliability preflight checks passed.`);
