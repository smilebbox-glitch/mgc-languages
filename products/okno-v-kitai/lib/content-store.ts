import { randomUUID } from "node:crypto";
import { getPilotDb } from "@/lib/pilot-db";

export type ContentStatus = "draft" | "published" | "archived";
export type ContentItem = {
  id: string; section: string; slug: string; title: string; body: string; status: ContentStatus;
  sortOrder: number; metadata: Record<string, unknown>; createdAt: string; updatedAt: string; updatedBy: string;
};

function mapRow(row: Record<string, unknown>): ContentItem {
  let metadata: Record<string, unknown> = {};
  try { metadata = JSON.parse(String(row.metadata_json || "{}")); } catch { metadata = {}; }
  return { id: String(row.id), section: String(row.section), slug: String(row.slug), title: String(row.title), body: String(row.body), status: String(row.status) as ContentStatus, sortOrder: Number(row.sort_order || 100), metadata, createdAt: String(row.created_at), updatedAt: String(row.updated_at), updatedBy: String(row.updated_by) };
}

export function listContent(section?: string, includeUnpublished = false) {
  const db = getPilotDb();
  const rows = section
    ? db.prepare(`SELECT * FROM content_items WHERE section = ? ${includeUnpublished ? "" : "AND status = 'published'"} ORDER BY sort_order, updated_at DESC`).all(section)
    : db.prepare(`SELECT * FROM content_items ${includeUnpublished ? "" : "WHERE status = 'published'"} ORDER BY section, sort_order, updated_at DESC`).all();
  return (rows as Array<Record<string, unknown>>).map(mapRow);
}

export function upsertContent(input: { id?: string; section: string; slug: string; title: string; body: string; status: ContentStatus; sortOrder?: number; metadata?: Record<string, unknown>; actor: string }) {
  const db = getPilotDb();
  const now = new Date().toISOString();
  const id = input.id?.trim() || randomUUID();
  const section = input.section.trim().slice(0, 80);
  const slug = input.slug.trim().toLowerCase().replace(/[^a-z0-9а-яё_-]+/giu, "-").replace(/^-+|-+$/gu, "").slice(0, 100);
  const title = input.title.trim().slice(0, 240);
  const body = input.body.trim().slice(0, 12000);
  if (!section || !slug || !title || !body) throw new Error("section, slug, title и body обязательны.");
  if (!["draft", "published", "archived"].includes(input.status)) throw new Error("Некорректный status.");
  const existing = db.prepare("SELECT created_at FROM content_items WHERE id = ?").get(id) as { created_at?: string } | undefined;
  db.prepare(`INSERT INTO content_items (id, section, slug, title, body, status, sort_order, metadata_json, created_at, updated_at, updated_by)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET section=excluded.section, slug=excluded.slug, title=excluded.title, body=excluded.body,
      status=excluded.status, sort_order=excluded.sort_order, metadata_json=excluded.metadata_json, updated_at=excluded.updated_at, updated_by=excluded.updated_by`)
    .run(id, section, slug, title, body, input.status, Number.isFinite(input.sortOrder) ? Math.round(input.sortOrder!) : 100, JSON.stringify(input.metadata || {}), existing?.created_at || now, now, input.actor.slice(0,160));
  const row = db.prepare("SELECT * FROM content_items WHERE id = ?").get(id) as Record<string, unknown>;
  return mapRow(row);
}

export function archiveContent(id: string, actor: string) {
  const db = getPilotDb();
  const now = new Date().toISOString();
  const result = db.prepare("UPDATE content_items SET status='archived', updated_at=?, updated_by=? WHERE id=?").run(now, actor.slice(0,160), id);
  return Number(result.changes || 0) > 0;
}

export function contentCounts() {
  const db = getPilotDb();
  const rows = db.prepare("SELECT status, COUNT(*) AS count FROM content_items GROUP BY status").all() as Array<Record<string, unknown>>;
  return Object.fromEntries(rows.map((row) => [String(row.status), Number(row.count || 0)]));
}

export const contentBundleFormat = "okno-v-kitai-managed-content" as const;
export type ContentBundle = {
  format: typeof contentBundleFormat;
  schema: 1;
  createdAt: string;
  createdBy: string;
  appVersion: string;
  items: Array<Omit<ContentItem, "createdAt" | "updatedAt" | "updatedBy"> & { metadata: Record<string, unknown> }>;
};

export function exportContentBundle(actor: string, section?: string): ContentBundle {
  const items = listContent(section, true).map((item) => ({
    id: item.id,
    section: item.section,
    slug: item.slug,
    title: item.title,
    body: item.body,
    status: item.status,
    sortOrder: item.sortOrder,
    metadata: item.metadata,
  }));
  return {
    format: contentBundleFormat,
    schema: 1,
    createdAt: new Date().toISOString(),
    createdBy: actor.slice(0, 160),
    appVersion: process.env.APP_VERSION || "1.6.1-pilot",
    items,
  };
}

export function validateContentBundle(value: unknown): ContentBundle {
  if (!value || typeof value !== "object") throw new Error("Import должен быть JSON-объектом.");
  const raw = value as Partial<ContentBundle>;
  if (raw.format !== contentBundleFormat || raw.schema !== 1 || !Array.isArray(raw.items)) throw new Error("Неподдерживаемый формат managed-content bundle.");
  if (raw.items.length > 1000) throw new Error("Слишком много материалов: максимум 1000 за импорт.");
  const items = raw.items.map((item, index) => {
    if (!item || typeof item !== "object") throw new Error(`Некорректный item #${index + 1}.`);
    const candidate = item as Partial<ContentItem>;
    const status = candidate.status;
    if (status !== "draft" && status !== "published" && status !== "archived") throw new Error(`Некорректный status у item #${index + 1}.`);
    if (typeof candidate.section !== "string" || typeof candidate.slug !== "string" || typeof candidate.title !== "string" || typeof candidate.body !== "string") throw new Error(`У item #${index + 1} отсутствуют обязательные поля.`);
    return {
      id: typeof candidate.id === "string" ? candidate.id.slice(0, 160) : "",
      section: candidate.section,
      slug: candidate.slug,
      title: candidate.title,
      body: candidate.body,
      status,
      sortOrder: Number.isFinite(candidate.sortOrder) ? Number(candidate.sortOrder) : 100,
      metadata: candidate.metadata && typeof candidate.metadata === "object" ? candidate.metadata : {},
    };
  });
  return { format: contentBundleFormat, schema: 1, createdAt: typeof raw.createdAt === "string" ? raw.createdAt : "", createdBy: typeof raw.createdBy === "string" ? raw.createdBy : "unknown", appVersion: typeof raw.appVersion === "string" ? raw.appVersion : "unknown", items };
}

export function importContentBundle(bundle: ContentBundle, actor: string, dryRun = false) {
  const db = getPilotDb();
  let created = 0;
  let updated = 0;
  const normalized = bundle.items.map((item) => {
    const existing = db.prepare("SELECT id FROM content_items WHERE id=? OR slug=? LIMIT 1").get(item.id || "__none__", item.slug) as { id?: string } | undefined;
    if (existing?.id) updated += 1; else created += 1;
    return { ...item, id: existing?.id || item.id || randomUUID() };
  });
  if (dryRun) return { dryRun: true, total: normalized.length, created, updated };
  db.exec("BEGIN IMMEDIATE;");
  try {
    for (const item of normalized) {
      upsertContent({ ...item, actor });
    }
    db.exec("COMMIT;");
  } catch (error) {
    db.exec("ROLLBACK;");
    throw error;
  }
  return { dryRun: false, total: normalized.length, created, updated };
}
