import { access, mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { constants } from "node:fs";
import { auditStatus } from "@/lib/audit";
import { pilotDbStatus } from "@/lib/pilot-db";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { runtimeConfigPath } from "@/lib/runtime-config";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const context = createRequestContext(request);
  let runtimeWritable = false;
  try {
    const directory = dirname(runtimeConfigPath());
    await mkdir(directory, { recursive: true });
    await access(directory, constants.W_OK);
    runtimeWritable = true;
  } catch { runtimeWritable = false; }
  const database = pilotDbStatus();
  const ready = runtimeWritable && database.available && database.migrationsPending === 0;
  return jsonWithContext(context, {
    status: ready ? "ready" : "not-ready",
    checks: { runtimeDataWritable: runtimeWritable, sqliteAvailable: database.available, migrationsCurrent: database.migrationsPending === 0 },
    database: { path: database.path, snapshots: database.snapshots, contentItems: database.contentItems, schemaVersion: database.schemaVersion, schemaLatest: database.schemaLatest, migrationsPending: database.migrationsPending },
    audit: { integrity: auditStatus().integrity },
    time: new Date().toISOString(),
  }, { status: ready ? 200 : 503, headers: { "cache-control": "no-store" } });
}
