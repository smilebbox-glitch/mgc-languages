import { access, readFile } from "node:fs/promises";
const checks=[];const failures=[];function check(v,label){const ok=Boolean(v);checks.push({ok,label});if(!ok)failures.push(label)}async function exists(path){try{await access(path);return true}catch{return false}}
const pkg=JSON.parse(await readFile("package.json","utf8"));const db=await readFile("lib/pilot-db.ts","utf8");const userStore=await readFile("lib/user-store.ts","utf8");const context=await readFile("lib/user-context.ts","utf8");const refresh=await readFile("app/api/internal/refresh/route.ts","utf8");const shell=await readFile("components/site-shell.tsx","utf8");const env=await readFile(".env.example","utf8");
check(pkg.version==="1.6.1-pilot","package version is v1.6.1 pilot");
check(db.includes("user_preferences")&&db.includes("user_favorites")&&db.includes("user_trips")&&db.includes("user_notifications")&&db.includes("usage_events"),"user business-operation tables exist");
check(context.includes("createHmac")&&context.includes("USER_DATA_HMAC_KEY")&&context.includes("okno_device_id"),"pseudonymous user identity layer packaged");
check(userStore.includes("generateUserNotifications")&&userStore.includes("eventLeadDays"),"subscription notification generator packaged");
check(userStore.includes("listFavorites")&&userStore.includes("saveTrip")&&userStore.includes("usageSummary"),"favorites, trip and aggregate usage store packaged");
check(await exists("app/api/user/offline-pack/route.ts")&&await exists("app/my/page.tsx"),"offline travel pack and personal workspace packaged");
check(await exists("components/favorite-button.tsx")&&await exists("components/user-hub.tsx"),"favorite and personal UX components packaged");
check(await exists("app/api/admin/usage/route.ts")&&await exists("components/usage-analytics.tsx"),"admin aggregate usage analytics packaged");
check(refresh.includes("generateUserNotifications")&&refresh.includes("applyUserRetention"),"scheduler generates notifications and applies user retention");
check(shell.includes('href: "/my"'),"personal workspace is in main navigation");
check(env.includes("USER_DATA_HMAC_KEY=")&&env.includes("USAGE_RETENTION_DAYS="),"privacy and usage-retention controls documented in env");
check(pkg.scripts?.["pilot:preflight"]?.includes("pilot:business"),"single pilot preflight includes business operations gate");
for(const item of checks)console.log(`${item.ok?"PASS":"FAIL"}  ${item.label}`);if(failures.length){console.error(`\n${failures.length} business preflight check(s) failed.`);process.exit(1)}console.log(`\n${checks.length}/${checks.length} business preflight checks passed.`);
