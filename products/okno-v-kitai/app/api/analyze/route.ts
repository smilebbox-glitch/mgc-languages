import { buildAnalysis, type AnalysisFocus, type AnalysisRequest, type AnalysisResult } from "@/lib/analysis";
import { analysisKnowledge } from "@/lib/analysis-knowledge";
import { seedNews, type NewsItem } from "@/lib/data";
import { safeFetch } from "@/lib/outbound";
import { isSourceEnabled, maintenanceState } from "@/lib/runtime-config";
import { logEvent } from "@/lib/logger";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";

export const dynamic = "force-dynamic";

function validNews(value: unknown): value is NewsItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<NewsItem>;
  return typeof item.id === "string" && typeof item.title === "string" && typeof item.summary === "string" && typeof item.url === "string" && /^https?:\/\//u.test(item.url) && typeof item.publishedAt === "string" && typeof item.source === "string";
}

function inferFocus(query: string, selected: AnalysisFocus): AnalysisFocus {
  const hasShacman = /shacman|shaanxi|шакман|шаанси|陕汽/iu.test(query);
  const hasGwm = /\bgwm\b|great\s*wall|haval|хавал|хавейл|\btank\b|\bwey\b|poer|长城|哈弗|坦克|魏牌/iu.test(query);
  if (hasShacman && hasGwm) return "Все";
  if (hasShacman) return "SHACMAN";
  if (hasGwm) return "GWM";
  return selected;
}

function cleanJson(value: string) {
  return value.trim().replace(/^```(?:json)?\s*/iu, "").replace(/\s*```$/u, "");
}

function validStrings(value: unknown, limit: number) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim().length >= 8).slice(0, limit)
    : [];
}

async function enhanceWithModel(base: AnalysisResult, query: string, focus: AnalysisFocus) {
  const endpoint = process.env.RAG_API_URL?.trim();
  const model = process.env.RAG_MODEL?.trim();
  if (!endpoint || !model || base.evidence.length === 0 || !(await isSourceEnabled("rag.model"))) return base;

  const evidence = base.evidence.map((item) => ({
    citation: item.citation,
    date: item.publishedAt.slice(0, 10),
    brand: item.brand,
    market: item.market,
    source: item.source,
    title: item.title,
    fact: item.summary,
  }));
  const system = [
    "Ты аналитик российско-китайского автопрома.",
    "Отвечай только по переданным фактам, не добавляй сведения из памяти.",
    "Каждое фактическое утверждение сопровождай ссылкой вида [1].",
    "Сравнивай только сопоставимые периоды и прямо отмечай нехватку данных.",
    "Пиши на русском, конкретно и без вводных фраз.",
    "Верни только JSON: summary, signals, risks, actions.",
    "signals — до 3 объектов claim, impact, citation; risks и actions — до 3 коротких строк.",
  ].join(" ");
  const user = JSON.stringify({ question: query, focus, evidence });
  const headers: Record<string, string> = { "content-type": "application/json" };
  const key = process.env.RAG_API_KEY?.trim();
  if (key) headers.authorization = `Bearer ${key}`;

  try {
    const response = await safeFetch(endpoint, {
      method: "POST",
      headers,
      signal: AbortSignal.timeout(12_000),
      body: JSON.stringify({
        model,
        temperature: 0.1,
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
      }),
    });
    if (!response.ok) return base;
    const payload = await response.json() as { choices?: Array<{ message?: { content?: string } }> };
    const content = payload.choices?.[0]?.message?.content;
    if (!content) return base;
    const parsed = JSON.parse(cleanJson(content)) as {
      summary?: unknown;
      signals?: unknown;
      risks?: unknown;
      actions?: unknown;
    };
    if (typeof parsed.summary !== "string" || parsed.summary.trim().length < 30 || !/\[\d+\]/u.test(parsed.summary)) return base;
    const signals = Array.isArray(parsed.signals)
      ? parsed.signals.flatMap((item) => {
          if (!item || typeof item !== "object") return [];
          const signal = item as { claim?: unknown; impact?: unknown; citation?: unknown };
          const citation = Number(signal.citation);
          if (typeof signal.claim !== "string" || typeof signal.impact !== "string" || !Number.isInteger(citation) || citation < 1 || citation > base.evidence.length) return [];
          return [{ claim: signal.claim.trim(), impact: signal.impact.trim(), citation }];
        }).slice(0, 3)
      : [];
    return {
      ...base,
      summary: parsed.summary.trim(),
      signals: signals.length ? signals : base.signals,
      risks: validStrings(parsed.risks, 3).length ? validStrings(parsed.risks, 3) : base.risks,
      actions: validStrings(parsed.actions, 3).length ? validStrings(parsed.actions, 3) : base.actions,
      mode: "model" as const,
    };
  } catch (error) {
    logEvent("warn", "rag_enhancement_failed", { error });
    return base;
  }
}

export async function POST(request: Request) {
  const context = createRequestContext(request);
  const maintenance = await maintenanceState();
  if (maintenance.enabled) return jsonWithContext(context, { error: maintenance.message, maintenance: true }, { status: 503, headers: { "retry-after": "300", "cache-control": "no-store" } });
  const limit = checkRateLimit({ context, scope: "analysis-expensive", limit: Number(process.env.RATE_LIMIT_EXPENSIVE_PER_MINUTE || 20) });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов на анализ. Повторите позже." }, { status: 429, headers: rateLimitHeaders(limit) });
  try {
    const body = await request.json() as Partial<AnalysisRequest>;
    const query = typeof body.query === "string" ? body.query.trim().slice(0, 1200) : "";
    if (!query) return jsonWithContext(context, { error: "Нужен вопрос для анализа." }, { status: 400, headers: rateLimitHeaders(limit) });
    const supplied = Array.isArray(body.items) ? body.items.filter(validNews).slice(0, 150) : [];
    const selectedFocus: AnalysisFocus = body.focus === "GWM" || body.focus === "Все" ? body.focus : "SHACMAN";
    const focus = inferFocus(query, selectedFocus);
    const corpus = [...new Map([...supplied, ...seedNews, ...analysisKnowledge].map((item) => [item.id, item])).values()];
    const result = buildAnalysis({
      focus,
      market: body.market === "Россия" || body.market === "Китай" || body.market === "Международный" ? body.market : "Все рынки",
      period: body.period === "90" || body.period === "all" ? body.period : "365",
      query,
      items: corpus,
    });
    return jsonWithContext(context, await enhanceWithModel(result, query, focus), { headers: { "cache-control": "no-store", ...rateLimitHeaders(limit) } });
  } catch {
    return jsonWithContext(context, { error: "Не удалось обработать запрос." }, { status: 400, headers: rateLimitHeaders(limit) });
  }
}
