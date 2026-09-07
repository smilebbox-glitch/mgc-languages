import { access, readFile } from "node:fs/promises";
const checks=[]; const failures=[];
function check(value,label){const ok=Boolean(value);checks.push({ok,label});if(!ok)failures.push(label)}
async function exists(path){try{await access(path);return true}catch{return false}}
const pkg=JSON.parse(await readFile("package.json","utf8"));
const db=await readFile("lib/pilot-db.ts","utf8");
const governance=await readFile("lib/governance.ts","utf8");
const runtime=await readFile("lib/runtime-config.ts","utf8");
const refresh=await readFile("app/api/internal/refresh/route.ts","utf8");
const content=await readFile("lib/content-store.ts","utf8");
const env=await readFile(".env.example","utf8");
check(pkg.version==="1.6.1-pilot","package version is v1.6.1 pilot");
check(db.includes("schema_migrations")&&db.includes("applyMigrations")&&db.includes("scheduler_locks"),"versioned SQLite migrations packaged");
check(governance.includes("applyRetentionPolicies")&&governance.includes("SOURCE_HISTORY_RETENTION_DAYS")&&governance.includes("ARCHIVED_CONTENT_RETENTION_DAYS"),"retention policy implementation packaged");
check(governance.includes("acquireSchedulerLock")&&governance.includes("releaseSchedulerLock")&&governance.includes("SCHEDULER_LOCK_TTL_SECONDS"),"scheduler locking with TTL packaged");
check(refresh.includes("acquireSchedulerLock")&&refresh.includes("applyRetentionPolicies")&&refresh.includes("finally"),"refresh orchestration uses lock and retention cleanup");
check(runtime.includes("maintenance")&&runtime.includes("saveMaintenanceConfig")&&runtime.includes("version: 2"),"runtime maintenance mode is versioned");
check(await exists("app/api/admin/governance/route.ts")&&await exists("components/governance-console.tsx"),"governance control plane packaged");
check(content.includes("contentBundleFormat")&&content.includes("validateContentBundle")&&content.includes("importContentBundle"),"managed content import/export bundle implemented");
check(await exists("app/api/admin/content-export/route.ts")&&await exists("app/api/admin/content-import/route.ts"),"managed content import/export API packaged");
check(governance.includes("sourceSlaStatus")&&env.includes("SOURCE_SLA_FX_SECONDS")&&env.includes("SOURCE_SLA_NEWS_SECONDS"),"source SLA policy packaged");
check(await exists("lib/config-validation.ts"),"configuration validation packaged");
check(await exists("scripts/generate-acceptance-report.mjs")&&pkg.scripts?.["pilot:acceptance"],"automated IT acceptance report generator packaged");
for(const item of checks) console.log(`${item.ok?"PASS":"FAIL"}  ${item.label}`);
if(failures.length){console.error(`\n${failures.length} governance preflight check(s) failed.`);process.exit(1)}
console.log(`\n${checks.length}/${checks.length} governance preflight checks passed.`);
