import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export const sourceKeys = [
  "fx.cbr",
  "fx.banks",
  "news.telegram",
  "news.autostat",
  "news.chinaPortals",
  "translate.google",
  "rag.model",
] as const;

export type SourceKey = (typeof sourceKeys)[number];

export type RuntimeConfig = {
  version: 2;
  updatedAt: string;
  updatedBy: string;
  sources: Record<SourceKey, boolean>;
  maintenance: {
    enabled: boolean;
    message: string;
  };
};

const configPath = process.env.RUNTIME_CONFIG_PATH?.trim() || "/data/runtime-config.json";

const defaultSources: Record<SourceKey, boolean> = {
  "fx.cbr": true,
  "fx.banks": true,
  "news.telegram": true,
  "news.autostat": true,
  "news.chinaPortals": true,
  "translate.google": true,
  "rag.model": true,
};

function defaultConfig(): RuntimeConfig {
  return {
    version: 2,
    updatedAt: new Date(0).toISOString(),
    updatedBy: "defaults",
    sources: { ...defaultSources },
    maintenance: { enabled: false, message: "Выполняются технические работы. Попробуйте позже." },
  };
}

function normalize(value: unknown): RuntimeConfig {
  const base = defaultConfig();
  if (!value || typeof value !== "object") return base;
  const raw = value as Partial<RuntimeConfig> & { version?: number; maintenance?: unknown };
  const rawSources = raw.sources && typeof raw.sources === "object" ? raw.sources : {};
  for (const key of sourceKeys) {
    const candidate = (rawSources as Partial<Record<SourceKey, unknown>>)[key];
    if (typeof candidate === "boolean") base.sources[key] = candidate;
  }
  if (typeof raw.updatedAt === "string") base.updatedAt = raw.updatedAt;
  if (typeof raw.updatedBy === "string") base.updatedBy = raw.updatedBy.slice(0, 160);
  if (raw.maintenance && typeof raw.maintenance === "object") {
    const maintenance = raw.maintenance as { enabled?: unknown; message?: unknown };
    if (typeof maintenance.enabled === "boolean") base.maintenance.enabled = maintenance.enabled;
    if (typeof maintenance.message === "string" && maintenance.message.trim()) base.maintenance.message = maintenance.message.trim().slice(0, 500);
  }
  return base;
}

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  try {
    return normalize(JSON.parse(await readFile(configPath, "utf8")));
  } catch (error) {
    const code = (error as NodeJS.ErrnoException)?.code;
    if (code !== "ENOENT") console.warn(JSON.stringify({ level: "warn", event: "runtime_config_read_failed", code }));
    return defaultConfig();
  }
}

async function persist(current: RuntimeConfig) {
  await mkdir(dirname(configPath), { recursive: true });
  const temporary = `${configPath}.${process.pid}.tmp`;
  await writeFile(temporary, `${JSON.stringify(current, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  await rename(temporary, configPath);
  return current;
}

export async function saveRuntimeConfig(
  sources: Partial<Record<SourceKey, boolean>>,
  updatedBy: string,
): Promise<RuntimeConfig> {
  const current = await loadRuntimeConfig();
  for (const key of sourceKeys) {
    if (typeof sources[key] === "boolean") current.sources[key] = sources[key]!;
  }
  current.updatedAt = new Date().toISOString();
  current.updatedBy = updatedBy.slice(0, 160) || "unknown";
  return persist(current);
}

export async function saveMaintenanceConfig(input: { enabled: boolean; message?: string }, updatedBy: string): Promise<RuntimeConfig> {
  const current = await loadRuntimeConfig();
  current.maintenance.enabled = Boolean(input.enabled);
  if (typeof input.message === "string" && input.message.trim()) current.maintenance.message = input.message.trim().slice(0, 500);
  current.updatedAt = new Date().toISOString();
  current.updatedBy = updatedBy.slice(0, 160) || "unknown";
  return persist(current);
}

export async function isSourceEnabled(key: SourceKey) {
  return (await loadRuntimeConfig()).sources[key];
}

export async function maintenanceState() {
  return (await loadRuntimeConfig()).maintenance;
}

export function runtimeConfigPath() {
  return configPath;
}
