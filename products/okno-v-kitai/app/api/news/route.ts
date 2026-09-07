import type { Brand, NewsItem } from "@/lib/data";
import { sourceChannels, sourceWebsites } from "@/lib/data";
import { safeFetch } from "@/lib/outbound";
import { loadRuntimeConfig } from "@/lib/runtime-config";
import { logEvent } from "@/lib/logger";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { isSchedulerRequest } from "@/lib/internal-auth";
import { getSourceSnapshot, recordSourceRun, saveSourceSnapshot } from "@/lib/source-cache";

export const dynamic = "force-dynamic";

const sourceNames = new Map(
  sourceChannels.map((source) => [source.handle, source.name])
);

const brandPatterns: Array<[Brand, RegExp]> = [
  ["SHACMAN", /\bshacman\b|\bshaanxi\b|шакман|шаанси|陕汽/iu],
  [
    "GWM",
    /\bgwm\b|great\s*wall|г(р|рэ)ейт\s*волл|\bhaval\b|\btank\b|\bwey\b|\bora\b|хавейл|хавал|танк|长城|哈弗|坦克|魏牌|欧拉/iu,
  ],
];

function decodeHtml(value: string) {
  const entities: Record<string, string> = {
    amp: "&",
    quot: '"',
    apos: "'",
    lt: "<",
    gt: ">",
    nbsp: " ",
    laquo: "«",
    raquo: "»",
    mdash: "—",
    ndash: "–",
  };

  return value
    .replace(/<br\s*\/?\s*>/giu, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&#(\d+);/g, (_, code: string) =>
      String.fromCodePoint(Number(code))
    )
    .replace(/&#x([0-9a-f]+);/giu, (_, code: string) =>
      String.fromCodePoint(parseInt(code, 16))
    )
    .replace(/&([a-z]+);/giu, (match, name: string) =>
      entities[name.toLowerCase()] ?? match
    )
    .replace(/\s+/g, " ")
    .trim();
}

function detectBrand(text: string): Brand {
  for (const [brand, pattern] of brandPatterns) {
    if (pattern.test(text)) return brand;
  }
  return "Отрасль";
}

function shorten(value: string, length: number) {
  if (value.length <= length) return value;
  const shortened = value.slice(0, length - 1).replace(/\s+\S*$/, "");
  return `${shortened}…`;
}

function compactSummary(value: string, title = "", length = 260) {
  let cleaned = decodeHtml(value)
    .replace(/https?:\/\/\S+/giu, "")
    .replace(title, "")
    .replace(/^[\s—–:;,.]+/u, "")
    .trim();
  if (!cleaned) cleaned = decodeHtml(value).trim();
  const sentences = cleaned.match(/[^.!?。！？]+[.!?。！？]+/gu) ?? [];
  const complete = sentences.find((sentence) => sentence.trim().length >= 24)?.trim();
  let result = complete || cleaned;
  if (result.length > length) {
    result = result.slice(0, length).replace(/\s+\S*$/u, "").replace(/[,:;—–\s]+$/u, "");
  }
  result = result.replace(/[…\s]+$/u, "");
  if (result && !/[.!?。！？]$/u.test(result)) result += ".";
  return result;
}

function makeTitle(text: string) {
  const firstSentence = text.match(/^.{20,180}?[.!?](?:\s|$)/u)?.[0] ?? text;
  return shorten(firstSentence.trim(), 150);
}

async function fetchText(url: string, requestSignal?: AbortSignal) {
  const response = await safeFetch(url, {
    headers: {
      "user-agent":
        "Mozilla/5.0 (compatible; ChinaAutoRadar/1.0; +https://chatgpt.com)",
      accept: "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    signal: requestSignal
      ? AbortSignal.any([requestSignal, AbortSignal.timeout(4200)])
      : AbortSignal.timeout(4200),
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.text();
}

async function fetchTelegramChannel(handle: string, requestSignal?: AbortSignal): Promise<NewsItem[]> {
  const html = await fetchText(`https://t.me/s/${handle}`, requestSignal);
  const chunks = html.split("tgme_widget_message_wrap").slice(1);
  const items: NewsItem[] = [];

  for (const chunk of chunks) {
    const post = chunk.match(/data-post="([^"]+)"/u)?.[1];
    const datetime = chunk.match(/<time[^>]+datetime="([^"]+)"/u)?.[1];
    const body = chunk.match(
      /tgme_widget_message_text[^>]*>([\s\S]*?)<\/div>/u
    )?.[1];

    if (!post || !datetime || !body) continue;
    const text = decodeHtml(body);
    if (text.length < 28) continue;

    const brand = detectBrand(text);
    const postId = post.split("/").at(-1) ?? post;

    items.push({
      id: `telegram-${handle}-${postId}`,
      title: makeTitle(text),
      summary: compactSummary(text, makeTitle(text)),
      source: sourceNames.get(handle) ?? `@${handle}`,
      sourceType: "telegram",
      url: `https://t.me/${post}`,
      publishedAt: datetime,
      market: "Россия",
      brand,
      live: true,
    });
  }

  return items.slice(-24);
}

function unwrapXml(value: string) {
  return decodeHtml(value.replace(/^<!\[CDATA\[/u, "").replace(/\]\]>$/u, ""));
}

async function fetchAutostatRss(requestSignal?: AbortSignal): Promise<NewsItem[]> {
  const xml = await fetchText("https://www.autostat.ru/news/rss/3/", requestSignal);
  const items: NewsItem[] = [];

  for (const match of xml.matchAll(/<item>([\s\S]*?)<\/item>/giu)) {
    const item = match[1];
    const titleRaw = item.match(/<title>([\s\S]*?)<\/title>/iu)?.[1];
    const linkRaw = item.match(/<link>([\s\S]*?)<\/link>/iu)?.[1];
    const dateRaw = item.match(/<pubDate>([\s\S]*?)<\/pubDate>/iu)?.[1];
    const descriptionRaw = item.match(
      /<description>([\s\S]*?)<\/description>/iu
    )?.[1];

    if (!titleRaw || !linkRaw || !dateRaw) continue;
    const title = unwrapXml(titleRaw);
    const link = unwrapXml(linkRaw);
    const description = descriptionRaw ? unwrapXml(descriptionRaw) : title;

    items.push({
      id: `autostat-${link.match(/\/(\d+)\/?$/u)?.[1] ?? encodeURIComponent(link)}`,
      title: shorten(title, 160),
      summary: compactSummary(description, title),
      source: "АВТОСТАТ",
      sourceType: "media",
      url: link,
      publishedAt: new Date(dateRaw).toISOString(),
      market: "Россия",
      brand: detectBrand(`${title} ${description}`),
      live: true,
    });
  }

  return items.slice(0, 50);
}

const autoIndustryPattern =
  /汽车|车企|整车|新能源车|商用车|重卡|卡车|零部件|供应链|销量|产量|出口|工厂|自动驾驶|电池|充电|SHACMAN|Shaanxi|陕汽|Great\s*Wall|GWM|长城汽车|哈弗|坦克|魏牌|欧拉|炮/iu;

function absoluteUrl(href: string, base: string) {
  try {
    const url = new URL(decodeHtml(href), base);
    if (!/^https?:$/u.test(url.protocol)) return null;
    url.hash = "";
    for (const key of [...url.searchParams.keys()]) {
      if (/^(utm_|spm|from|source|ref)/iu.test(key)) url.searchParams.delete(key);
    }
    return url.toString();
  } catch {
    return null;
  }
}

async function translateChinese(value: string, requestSignal?: AbortSignal) {
  if (!/[\u3400-\u9fff]/u.test(value)) return value;
  try {
    const endpoint = new URL("https://translate.googleapis.com/translate_a/single");
    endpoint.search = new URLSearchParams({
      client: "gtx",
      sl: "zh-CN",
      tl: "ru",
      dt: "t",
      q: value,
    }).toString();
    const signal = requestSignal
      ? AbortSignal.any([requestSignal, AbortSignal.timeout(3000)])
      : AbortSignal.timeout(3000);
    const response = await safeFetch(endpoint, { signal });
    if (!response.ok) return value;
    const payload = (await response.json()) as Array<Array<Array<string>>>;
    return payload[0]?.map((part) => part[0]).join("") || value;
  } catch {
    return value;
  }
}

function metaValue(html: string, names: string[]) {
  for (const tag of html.matchAll(/<meta\b[^>]*>/giu)) {
    const value = tag[0];
    const key = value.match(/(?:name|property)=["']([^"']+)["']/iu)?.[1]?.toLowerCase();
    if (!key || !names.includes(key)) continue;
    const content = value.match(/content=["']([^"']+)["']/iu)?.[1];
    if (content) return decodeHtml(content);
  }
  return "";
}

function articleDate(html: string) {
  const raw =
    metaValue(html, ["article:published_time", "pubdate", "publishdate", "date"]) ||
    html.match(/["']datePublished["']\s*:\s*["']([^"']+)["']/iu)?.[1] ||
    html.match(/(20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2})/u)?.[1];
  if (!raw) return new Date().toISOString();
  const normalized = raw.replace("年", "-").replace("月", "-").replace("日", "").replaceAll("/", "-");
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
}

async function fetchChineseArticle(candidate: { title: string; url: string }, requestSignal?: AbortSignal) {
  try {
    const html = await fetchText(candidate.url, requestSignal);
    const description = metaValue(html, ["description", "og:description", "twitter:description"]);
    if (description.length < 24 || !/[\u3400-\u9fff]/u.test(description)) return null;
    const [translatedTitle, translatedDescription] = await Promise.all([
      translateChinese(candidate.title, requestSignal),
      translateChinese(description, requestSignal),
    ]);
    if (
      translatedTitle === candidate.title ||
      /[\u3400-\u9fff]/u.test(translatedTitle) ||
      /[\u3400-\u9fff]/u.test(translatedDescription)
    ) {
      return null;
    }
    return {
      title: translatedTitle,
      summary: compactSummary(translatedDescription, translatedTitle),
      publishedAt: articleDate(html),
    };
  } catch {
    return null;
  }
}

async function fetchChinesePortal(source: (typeof sourceWebsites)[number], requestSignal?: AbortSignal): Promise<NewsItem[]> {
  const html = await fetchText(source.url, requestSignal);
  const candidates = new Map<string, { title: string; url: string }>();

  for (const match of html.matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/giu)) {
    const originalTitle = decodeHtml(match[2]);
    if (originalTitle.length < 8 || originalTitle.length > 140) continue;
    if (!autoIndustryPattern.test(originalTitle)) continue;
    const url = absoluteUrl(match[1], source.url);
    if (!url || candidates.has(url)) continue;
    candidates.set(url, { title: originalTitle, url });
  }

  const ranked = [...candidates.values()]
    .sort((left, right) => {
      const leftFocus = detectBrand(left.title) === "Отрасль" ? 0 : 1;
      const rightFocus = detectBrand(right.title) === "Отрасль" ? 0 : 1;
      return rightFocus - leftFocus;
    })
    .slice(0, 4);

  const translated = await Promise.all(
    ranked.map(async (candidate, index) => {
      const article = await fetchChineseArticle(candidate, requestSignal);
      if (!article) return null;
      return {
        id: `portal-${source.name}-${index}-${encodeURIComponent(candidate.url)}`,
        title: shorten(article.title, 160),
        originalTitle: candidate.title,
        summary: article.summary,
        source: source.name,
        sourceType: "media" as const,
        url: candidate.url,
        publishedAt: article.publishedAt,
        market: "Китай" as const,
        brand: detectBrand(candidate.title),
        translated: true,
        live: true,
      };
    })
  );
  return translated.filter((item): item is NonNullable<typeof item> => item !== null);
}

function canonicalUrl(value: string) {
  return absoluteUrl(value, value) ?? value;
}

function titleFingerprint(value: string) {
  return value.toLocaleLowerCase("ru-RU").replace(/[^\p{L}\p{N}]+/gu, "").slice(0, 80);
}

function withDeadline<T>(promise: Promise<T>, timeoutMs = 8500): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("source deadline exceeded")), timeoutMs);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      }
    );
  });
}

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const limit = checkRateLimit({ context, scope: "news-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120) });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const runtime = await loadRuntimeConfig();
  const url = new URL(request.url);
  const forceRefresh = url.searchParams.get("refresh") === "1" && isSchedulerRequest(request);
  const revision = `${runtime.updatedAt}:${runtime.sources["news.telegram"]}:${runtime.sources["news.autostat"]}:${runtime.sources["news.chinaPortals"]}:${runtime.sources["translate.google"]}`;
  const cacheKey = `news:aggregate:${revision}`;
  type NewsPayload = { news: NewsItem[]; updatedAt: string; sourceCount: number; totalSources: number; disabledSources: string[]; errors: string[]; cache?: { state: string; ageSeconds?: number; qualityScore?: number } };
  const cached = getSourceSnapshot<NewsPayload>(cacheKey);
  if (!forceRefresh && cached?.state === "fresh") {
    return jsonWithContext(context, { ...cached.payload, cache: { state: "fresh", ageSeconds: cached.ageSeconds, qualityScore: cached.qualityScore } }, {
      headers: { "cache-control": "public, max-age=120, s-maxage=300", "x-data-cache": "fresh", ...rateLimitHeaders(limit) },
    });
  }

  const started = Date.now();
  const requestController = new AbortController();
  const requestDeadline = setTimeout(() => requestController.abort(), 6500);
  const jobs = [
    ...(runtime.sources["news.telegram"] ? sourceChannels.map((source) => ({
      name: `news.telegram:${source.handle}`,
      promise: withDeadline(fetchTelegramChannel(source.handle, requestController.signal)),
    })) : []),
    ...(runtime.sources["news.autostat"]
      ? [{ name: "news.autostat:rss", promise: withDeadline(fetchAutostatRss(requestController.signal)) }]
      : []),
    ...(runtime.sources["news.chinaPortals"] && runtime.sources["translate.google"]
      ? sourceWebsites
          .filter((source) => source.language === "zh")
          .map((source) => ({
            name: `news.chinaPortal:${source.name}`,
            promise: withDeadline(fetchChinesePortal(source, requestController.signal)),
          }))
      : []),
  ];

  const disabledSources = [
    ...(!runtime.sources["news.telegram"] ? ["news.telegram"] : []),
    ...(!runtime.sources["news.autostat"] ? ["news.autostat"] : []),
    ...(!runtime.sources["news.chinaPortals"] ? ["news.chinaPortals"] : []),
    ...(!runtime.sources["translate.google"] ? ["translate.google"] : []),
  ];

  const results = await Promise.allSettled(jobs.map((job) => job.promise));
  clearTimeout(requestDeadline);
  const errors: string[] = [];
  const news = results.flatMap((result, index) => {
    const job = jobs[index];
    if (result.status === "fulfilled") {
      recordSourceRun({ sourceKey: job.name, status: "success", qualityScore: result.value.length ? 100 : 70, itemCount: result.value.length, latencyMs: Date.now() - started });
      return result.value;
    }
    errors.push(job.name);
    recordSourceRun({ sourceKey: job.name, status: "failure", qualityScore: 0, latencyMs: Date.now() - started, error: result.reason instanceof Error ? result.reason.message : "source failed" });
    return [];
  });

  if (errors.length) logEvent("warn", "news_sources_failed", { errors });

  const combinedNews = cached?.state === "stale" && errors.length
    ? [...news, ...cached.payload.news.map((item) => ({ ...item, live: false }))]
    : news;
  const uniqueMap = new Map<string, NewsItem>();
  const seenTitles = new Set<string>();
  for (const item of combinedNews) {
    const day = item.publishedAt.slice(0, 10);
    const titleKey = `${day}:${titleFingerprint(item.originalTitle ?? item.title)}`;
    if (seenTitles.has(titleKey)) continue;
    seenTitles.add(titleKey);
    uniqueMap.set(canonicalUrl(item.url), item);
  }

  const unique = Array.from(uniqueMap.values())
    .sort((left, right) => new Date(right.publishedAt).getTime() - new Date(left.publishedAt).getTime())
    .slice(0, 120);

  if (!unique.length && cached?.state === "stale") {
    return jsonWithContext(context, {
      ...cached.payload,
      errors: [...cached.payload.errors, ...errors],
      cache: { state: "stale", ageSeconds: cached.ageSeconds, qualityScore: cached.qualityScore },
    }, { headers: { "cache-control": "public, max-age=60", "x-data-cache": "stale", ...rateLimitHeaders(limit) } });
  }

  const sourceCount = jobs.length - errors.length;
  const qualityScore = jobs.length ? Math.round((sourceCount / jobs.length) * 100) : 0;
  const payload: NewsPayload = {
    news: unique,
    updatedAt: new Date().toISOString(),
    sourceCount,
    totalSources: jobs.length,
    disabledSources,
    errors,
    cache: { state: unique.length ? "live" : "miss", ageSeconds: 0, qualityScore },
  };
  if (unique.length) {
    saveSourceSnapshot({ cacheKey, sourceKey: "news.aggregate", payload, ttlMs: Number(process.env.NEWS_CACHE_TTL_SECONDS || 900) * 1000, staleMs: Number(process.env.NEWS_CACHE_STALE_SECONDS || 21600) * 1000, status: errors.length ? "partial" : "live", qualityScore, itemCount: unique.length, latencyMs: Date.now() - started, error: errors.join(", ") });
  } else {
    recordSourceRun({ sourceKey: "news.aggregate", status: jobs.length ? "failure" : "disabled", qualityScore, itemCount: 0, latencyMs: Date.now() - started, error: errors.join(", ") });
  }

  return jsonWithContext(context, payload, {
    headers: {
      "cache-control": "public, max-age=120, s-maxage=300, stale-while-revalidate=3600",
      "x-data-cache": payload.cache?.state || "live",
      ...rateLimitHeaders(limit),
    },
  });
}
