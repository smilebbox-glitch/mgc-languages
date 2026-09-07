import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { DatabaseSync } from "node:sqlite";

const source = process.env.PILOT_DB_PATH?.trim() || "/data/okno.sqlite";
const backupDir = process.env.PILOT_BACKUP_DIR?.trim() || join(dirname(source), "backups");
await mkdir(backupDir, { recursive: true });
const stamp = new Date().toISOString().replace(/[:.]/gu, "-");
const target = join(backupDir, `okno-${stamp}.sqlite`);
const db = new DatabaseSync(source);
try {
  const escaped = target.replaceAll("'", "''");
  db.exec(`PRAGMA busy_timeout=5000; VACUUM INTO '${escaped}';`);
  console.log(JSON.stringify({ event: "sqlite_backup_created", source, target, time: new Date().toISOString() }));
} finally { db.close(); }
