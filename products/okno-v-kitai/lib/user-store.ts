import { randomUUID } from "node:crypto";
import { getPilotDb } from "@/lib/pilot-db";
import { autoEvents, type NewsItem } from "@/lib/data";

export type UserSubscriptions = {
  brands: string[];
  markets: string[];
  topics: string[];
  cities: string[];
  events: string[];
  eventLeadDays: number;
};

export const defaultSubscriptions: UserSubscriptions = {
  brands: [], markets: [], topics: [], cities: [], events: [], eventLeadDays: 30,
};

export type UserFavorite = {
  itemType: "news" | "event" | "link";
  itemId: string;
  title: string;
  url: string;
  metadata: Record<string, unknown>;
  createdAt: string;
};

export type UserTrip = {
  title: string;
  city: string;
  startDate: string;
  endDate: string;
  eventId: string;
  hotel: string;
  flight: string;
  notes: string;
  checklist: string[];
};

const defaultTrip: UserTrip = { title: "", city: "", startDate: "", endDate: "", eventId: "", hotel: "", flight: "", notes: "", checklist: [] };

function parseJson<T>(value: unknown, fallback: T): T {
  try { return JSON.parse(String(value || "")) as T; } catch { return fallback; }
}
function arrayOfStrings(value: unknown, max = 50) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").map((item) => item.trim()).filter(Boolean).slice(0, max) : [];
}
function normalizeSubscriptions(input: Partial<UserSubscriptions>): UserSubscriptions {
  return {
    brands: arrayOfStrings(input.brands, 20), markets: arrayOfStrings(input.markets, 20), topics: arrayOfStrings(input.topics, 20),
    cities: arrayOfStrings(input.cities, 30), events: arrayOfStrings(input.events, 50),
    eventLeadDays: Math.max(1, Math.min(180, Math.round(Number(input.eventLeadDays || 30)))),
  };
}

export function getSubscriptions(userKey: string) {
  const db = getPilotDb();
  const row = db.prepare("SELECT subscriptions_json, created_at, updated_at FROM user_preferences WHERE user_key=?").get(userKey) as Record<string, unknown> | undefined;
  if (!row) return { subscriptions: defaultSubscriptions, createdAt: "", updatedAt: "" };
  return { subscriptions: normalizeSubscriptions(parseJson<Partial<UserSubscriptions>>(row.subscriptions_json, {})), createdAt: String(row.created_at || ""), updatedAt: String(row.updated_at || "") };
}

export function saveSubscriptions(userKey: string, input: Partial<UserSubscriptions>) {
  const db = getPilotDb();
  const now = new Date().toISOString();
  const subscriptions = normalizeSubscriptions(input);
  db.prepare(`INSERT INTO user_preferences(user_key, subscriptions_json, created_at, updated_at) VALUES(?,?,?,?)
    ON CONFLICT(user_key) DO UPDATE SET subscriptions_json=excluded.subscriptions_json, updated_at=excluded.updated_at`)
    .run(userKey, JSON.stringify(subscriptions), now, now);
  return { subscriptions, updatedAt: now };
}

export function listFavorites(userKey: string): UserFavorite[] {
  const db = getPilotDb();
  return (db.prepare("SELECT * FROM user_favorites WHERE user_key=? ORDER BY created_at DESC LIMIT 500").all(userKey) as Array<Record<string, unknown>>).map((row) => ({
    itemType: String(row.item_type) as UserFavorite["itemType"], itemId: String(row.item_id), title: String(row.title), url: String(row.url || ""),
    metadata: parseJson<Record<string, unknown>>(row.metadata_json, {}), createdAt: String(row.created_at),
  }));
}

export function saveFavorite(userKey: string, input: Omit<UserFavorite, "createdAt">) {
  const db = getPilotDb();
  const itemType = ["news","event","link"].includes(input.itemType) ? input.itemType : "link";
  const itemId = input.itemId.trim().slice(0, 240);
  const title = input.title.trim().slice(0, 300);
  const url = input.url.trim().slice(0, 1200);
  if (!itemId || !title) throw new Error("itemId и title обязательны.");
  const now = new Date().toISOString();
  db.prepare(`INSERT INTO user_favorites(user_key,item_type,item_id,title,url,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)
    ON CONFLICT(user_key,item_type,item_id) DO UPDATE SET title=excluded.title,url=excluded.url,metadata_json=excluded.metadata_json`)
    .run(userKey, itemType, itemId, title, url, JSON.stringify(input.metadata || {}), now);
  return { itemType, itemId, title, url, metadata: input.metadata || {}, createdAt: now };
}

export function removeFavorite(userKey: string, itemType: string, itemId: string) {
  const db = getPilotDb();
  const result = db.prepare("DELETE FROM user_favorites WHERE user_key=? AND item_type=? AND item_id=?").run(userKey, itemType, itemId);
  return Number(result.changes || 0) > 0;
}

export function getTrip(userKey: string): UserTrip {
  const db = getPilotDb();
  const row = db.prepare("SELECT trip_json FROM user_trips WHERE user_key=?").get(userKey) as { trip_json?: string } | undefined;
  return row ? { ...defaultTrip, ...parseJson<Partial<UserTrip>>(row.trip_json, {}) } : defaultTrip;
}
export function saveTrip(userKey: string, input: Partial<UserTrip>) {
  const db = getPilotDb();
  const now = new Date().toISOString();
  const trip: UserTrip = {
    title: String(input.title || "").trim().slice(0, 200), city: String(input.city || "").trim().slice(0, 120),
    startDate: /^\d{4}-\d{2}-\d{2}$/u.test(String(input.startDate || "")) ? String(input.startDate) : "",
    endDate: /^\d{4}-\d{2}-\d{2}$/u.test(String(input.endDate || "")) ? String(input.endDate) : "",
    eventId: String(input.eventId || "").trim().slice(0, 160), hotel: String(input.hotel || "").trim().slice(0, 300),
    flight: String(input.flight || "").trim().slice(0, 300), notes: String(input.notes || "").trim().slice(0, 5000), checklist: arrayOfStrings(input.checklist, 100),
  };
  db.prepare(`INSERT INTO user_trips(user_key,trip_json,created_at,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_key) DO UPDATE SET trip_json=excluded.trip_json,updated_at=excluded.updated_at`)
    .run(userKey, JSON.stringify(trip), now, now);
  return trip;
}

function detectTopics(item: NewsItem) {
  const text = `${item.title} ${item.summary}`;
  const matches: string[] = [];
  const patterns: Array<[string, RegExp]> = [
    ["Стратегия", /стратег|инвестиц|партнер|альянс|сделк|развити|strategy|战略|合作/iu],
    ["Геополитика", /санкц|пошлин|тариф|экспортн|огранич|запрет|регулир|комплаенс|关税|制裁|政策/iu],
    ["Локализация", /локализ|производств|завод|сборк|factory|产能|工厂|本地化/iu],
    ["Поставки", /постав|логист|компонент|цепочк|supplier|供应链|零部件|交付/iu],
    ["Продажи", /продаж|рынок|спрос|цена|доля|sales|销量|市场|价格/iu],
    ["Технологии", /технолог|батаре|электро|гибрид|автопилот|technology|电池|智能驾驶|新能源/iu],
  ];
  for (const [topic, pattern] of patterns) if (pattern.test(text)) matches.push(topic);
  return matches;
}

function insertNotification(userKey: string, eventKey: string, kind: string, title: string, body: string, url = "") {
  const db = getPilotDb();
  const result = db.prepare(`INSERT OR IGNORE INTO user_notifications(id,user_key,event_key,kind,title,body,url,created_at,read_at) VALUES(?,?,?,?,?,?,?,?,NULL)`)
    .run(randomUUID(), userKey, eventKey.slice(0,300), kind.slice(0,40), title.slice(0,300), body.slice(0,1000), url.slice(0,1200), new Date().toISOString());
  return Number(result.changes || 0);
}

export function generateUserNotifications() {
  const db = getPilotDb();
  const prefs = db.prepare("SELECT user_key, subscriptions_json, created_at FROM user_preferences").all() as Array<Record<string, unknown>>;
  const newsRow = db.prepare("SELECT payload_json FROM source_snapshots WHERE source_key='news.aggregate' ORDER BY fetched_at DESC LIMIT 1").get() as { payload_json?: string } | undefined;
  const news = parseJson<{news?: NewsItem[]}>(newsRow?.payload_json, {}).news || [];
  let created = 0;
  const now = Date.now();
  for (const row of prefs) {
    const userKey = String(row.user_key);
    const subscriptions = normalizeSubscriptions(parseJson<Partial<UserSubscriptions>>(row.subscriptions_json, {}));
    const createdAt = Date.parse(String(row.created_at || "")) || (now - 7 * 86400000);
    for (const item of news.slice(0, 120)) {
      const published = Date.parse(item.publishedAt);
      if (!Number.isFinite(published) || published < Math.max(createdAt, now - 7 * 86400000)) continue;
      const topics = detectTopics(item);
      const matches = subscriptions.brands.includes(item.brand) || subscriptions.markets.includes(item.market) || topics.some((topic) => subscriptions.topics.includes(topic));
      if (!matches) continue;
      created += insertNotification(userKey, `news:${item.id}`, "news", item.title, `${item.source} · ${item.market}${topics.length ? ` · ${topics.join(", ")}` : ""}`, item.url);
    }
    for (const event of autoEvents) {
      const start = Date.parse(`${event.start}T00:00:00Z`);
      const days = Math.ceil((start - now) / 86400000);
      if (days < 0 || days > subscriptions.eventLeadDays) continue;
      if (!subscriptions.events.includes(event.id) && !subscriptions.cities.includes(event.city)) continue;
      created += insertNotification(userKey, `event:${event.id}:${event.start}`, "event", `${event.shortName}: через ${days} дн.`, `${event.city} · ${event.start} — ${event.end}`, event.url);
    }
  }
  return { users: prefs.length, created };
}

export function listNotifications(userKey: string, limit = 100) {
  const db = getPilotDb();
  return (db.prepare("SELECT id,kind,title,body,url,created_at,read_at FROM user_notifications WHERE user_key=? ORDER BY created_at DESC LIMIT ?").all(userKey, Math.max(1, Math.min(500, limit))) as Array<Record<string, unknown>>).map((row) => ({
    id: String(row.id), kind: String(row.kind), title: String(row.title), body: String(row.body), url: String(row.url || ""), createdAt: String(row.created_at), readAt: row.read_at ? String(row.read_at) : null,
  }));
}
export function markNotificationsRead(userKey: string, ids?: string[]) {
  const db = getPilotDb(); const now = new Date().toISOString();
  if (!ids?.length) return Number(db.prepare("UPDATE user_notifications SET read_at=? WHERE user_key=? AND read_at IS NULL").run(now,userKey).changes || 0);
  let changed = 0; for (const id of ids.slice(0,200)) changed += Number(db.prepare("UPDATE user_notifications SET read_at=? WHERE user_key=? AND id=?").run(now,userKey,id).changes || 0); return changed;
}

export function trackUsage(userKey: string, eventName: string, path: string, metadata: Record<string, unknown> = {}) {
  const db = getPilotDb();
  db.prepare("INSERT INTO usage_events(user_key,event_name,path,metadata_json,created_at) VALUES(?,?,?,?,?)")
    .run(userKey, eventName.trim().slice(0,80), path.trim().slice(0,500), JSON.stringify(metadata).slice(0,4000), new Date().toISOString());
}

export function usageSummary(days = 30) {
  const db = getPilotDb(); const cutoff = new Date(Date.now() - Math.max(1,Math.min(365,days))*86400000).toISOString();
  const totals = db.prepare(`SELECT COUNT(*) AS events, COUNT(DISTINCT user_key) AS users FROM usage_events WHERE created_at>=?`).get(cutoff) as Record<string, unknown>;
  const events = db.prepare(`SELECT event_name,COUNT(*) AS count,COUNT(DISTINCT user_key) AS users FROM usage_events WHERE created_at>=? GROUP BY event_name ORDER BY count DESC LIMIT 30`).all(cutoff) as Array<Record<string, unknown>>;
  const paths = db.prepare(`SELECT path,COUNT(*) AS count,COUNT(DISTINCT user_key) AS users FROM usage_events WHERE created_at>=? AND event_name='page_view' GROUP BY path ORDER BY count DESC LIMIT 30`).all(cutoff) as Array<Record<string, unknown>>;
  return { days, totalEvents:Number(totals.events||0), uniqueUsers:Number(totals.users||0), events:events.map(r=>({event:String(r.event_name),count:Number(r.count||0),users:Number(r.users||0)})), paths:paths.map(r=>({path:String(r.path),count:Number(r.count||0),users:Number(r.users||0)})) };
}

export function applyUserRetention() {
  const db = getPilotDb(); const days = Math.max(1,Math.min(3650,Number(process.env.USAGE_RETENTION_DAYS||90))); const cutoff = new Date(Date.now()-days*86400000).toISOString();
  const usage = db.prepare("DELETE FROM usage_events WHERE created_at<?").run(cutoff);
  const notifications = db.prepare("DELETE FROM user_notifications WHERE created_at<?").run(new Date(Date.now()-180*86400000).toISOString());
  return { usageEvents:Number(usage.changes||0), notifications:Number(notifications.changes||0), usageRetentionDays:days };
}
