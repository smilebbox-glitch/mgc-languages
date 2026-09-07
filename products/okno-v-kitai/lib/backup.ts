import { loadRuntimeConfig, saveMaintenanceConfig, saveRuntimeConfig, sourceKeys, type SourceKey } from "@/lib/runtime-config";

export const backupFormat = "okno-v-kitai-runtime-backup" as const;

export type RuntimeBackup = {
  format: typeof backupFormat;
  schema: 2;
  createdAt: string;
  createdBy: string;
  appVersion: string;
  runtime: {
    sources: Record<SourceKey, boolean>;
    maintenance: { enabled: boolean; message: string };
  };
};

export async function createRuntimeBackup(createdBy: string): Promise<RuntimeBackup> {
  const current = await loadRuntimeConfig();
  return {
    format: backupFormat,
    schema: 2,
    createdAt: new Date().toISOString(),
    createdBy: createdBy.slice(0, 160),
    appVersion: process.env.APP_VERSION || "1.6.1-pilot",
    runtime: { sources: { ...current.sources }, maintenance: { ...current.maintenance } },
  };
}

export function validateRuntimeBackup(value: unknown): RuntimeBackup {
  if (!value || typeof value !== "object") throw new Error("Backup должен быть JSON-объектом.");
  const raw = value as { format?: unknown; schema?: unknown; createdAt?: unknown; createdBy?: unknown; appVersion?: unknown; runtime?: { sources?: unknown; maintenance?: unknown } };
  if (raw.format !== backupFormat || (raw.schema !== 1 && raw.schema !== 2)) throw new Error("Неподдерживаемый формат backup.");
  if (!raw.runtime?.sources || typeof raw.runtime.sources !== "object") throw new Error("Backup не содержит runtime.sources.");
  const sources = {} as Record<SourceKey, boolean>;
  for (const key of sourceKeys) {
    const item = (raw.runtime.sources as Partial<Record<SourceKey, unknown>>)[key];
    if (typeof item !== "boolean") throw new Error(`В backup отсутствует boolean ${key}.`);
    sources[key] = item;
  }
  let maintenance = { enabled: false, message: "Выполняются технические работы. Попробуйте позже." };
  if (raw.schema === 2 && raw.runtime.maintenance && typeof raw.runtime.maintenance === "object") {
    const item = raw.runtime.maintenance as { enabled?: unknown; message?: unknown };
    maintenance = {
      enabled: typeof item.enabled === "boolean" ? item.enabled : false,
      message: typeof item.message === "string" && item.message.trim() ? item.message.trim().slice(0, 500) : maintenance.message,
    };
  }
  return {
    format: backupFormat,
    schema: 2,
    createdAt: typeof raw.createdAt === "string" ? raw.createdAt : "",
    createdBy: typeof raw.createdBy === "string" ? raw.createdBy.slice(0, 160) : "unknown",
    appVersion: typeof raw.appVersion === "string" ? raw.appVersion.slice(0, 80) : "unknown",
    runtime: { sources, maintenance },
  };
}

export async function restoreRuntimeBackup(backup: RuntimeBackup, actor: string) {
  await saveRuntimeConfig(backup.runtime.sources, actor);
  return saveMaintenanceConfig(backup.runtime.maintenance, actor);
}
