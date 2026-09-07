import {
  bankSourceUrls,
  cityLabels,
  fallbackFxSnapshot,
  parseBankirosCny,
  parseCbrCnyXml,
  type FxCity,
  type FxSnapshot,
} from "@/lib/fx";
import { isSchedulerRequest } from "@/lib/internal-auth";
import { logEvent } from "@/lib/logger";
import { safeFetch } from "@/lib/outbound";
import { loadRuntimeConfig } from "@/lib/runtime-config";
import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { getSourceSnapshot, recordSourceRun, saveSourceSnapshot } from "@/lib/source-cache";

export const dynamic = "force-dynamic";

const CACHE_MS = Number(process.env.FX_CACHE_TTL_SECONDS || 900) * 1000;
const STALE_MS = Number(process.env.FX_CACHE_STALE_SECONDS || 86400) * 1000;

function isCity(value: string | null): value is FxCity {
  return value === "kaluga" || value === "moskva";
}

async function fetchText(url: string, signal: AbortSignal) {
  const response = await safeFetch(url, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(4500)]),
    headers: {
      accept: "text/html,application/xml,text/xml;q=0.9,*/*;q=0.8",
      "user-agent": "MGC-Okno-v-Kitai/1.6 (corporate pilot; currency reference)",
    },
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.text();
}

export async function GET(request: Request) {
  const context = createRequestContext(request);
  const limit = checkRateLimit({ context, scope: "fx-read", limit: Number(process.env.RATE_LIMIT_READ_PER_MINUTE || 120) });
  if (!limit.allowed) return jsonWithContext(context, { error: "Слишком много запросов." }, { status: 429, headers: rateLimitHeaders(limit) });
  const url = new URL(request.url);
  const requestedCity = url.searchParams.get("city");
  const city: FxCity = isCity(requestedCity) ? requestedCity : "kaluga";
  const forceRefresh = url.searchParams.get("refresh") === "1" && isSchedulerRequest(request);
  const runtime = await loadRuntimeConfig();
  const revision = `${runtime.updatedAt}:${runtime.sources["fx.cbr"]}:${runtime.sources["fx.banks"]}`;
  const cacheKey = `fx:${city}:${revision}`;
  const cached = getSourceSnapshot<FxSnapshot>(cacheKey);

  if (!forceRefresh && cached?.state === "fresh") {
    return jsonWithContext(context, { ...cached.payload, cache: { state: "fresh", ageSeconds: cached.ageSeconds, qualityScore: cached.qualityScore } }, {
      headers: { "cache-control": "private, max-age=60", "x-data-cache": "fresh", ...rateLimitHeaders(limit) },
    });
  }

  const started = Date.now();
  const fallback = fallbackFxSnapshot(city);
  const warnings: string[] = [];
  let cbr = fallback.cbr;
  let bankRates = fallback.bankRates;
  let liveParts = 0;
  let cbrLive = false;
  let banksLive = false;

  const cbrJob = runtime.sources["fx.cbr"]
    ? fetchText("https://www.cbr.ru/scripts/XML_daily.asp", request.signal)
    : Promise.reject(new Error("source disabled"));
  const bankJob = runtime.sources["fx.banks"]
    ? fetchText(bankSourceUrls[city], request.signal)
    : Promise.reject(new Error("source disabled"));

  const [cbrResult, bankResult] = await Promise.allSettled([cbrJob, bankJob]);

  if (!runtime.sources["fx.cbr"]) {
    warnings.push("Источник ЦБ РФ отключён администратором; используется резервное значение.");
    recordSourceRun({ sourceKey: "fx.cbr", scope: city, status: "disabled", qualityScore: 0 });
  } else if (cbrResult.status === "fulfilled") {
    try {
      const parsed = parseCbrCnyXml(cbrResult.value);
      cbr = { ...parsed, sourceUrl: "https://www.cbr.ru/currency_base/daily/" };
      liveParts += 1;
      cbrLive = true;
      recordSourceRun({ sourceKey: "fx.cbr", scope: city, status: "success", qualityScore: 100, itemCount: 1, latencyMs: Date.now() - started });
    } catch (error) {
      logEvent("warn", "fx_cbr_parse_failed", { error });
      warnings.push("Не удалось разобрать ответ Банка России; используется резервное значение курса ЦБ.");
      recordSourceRun({ sourceKey: "fx.cbr", scope: city, status: "failure", qualityScore: 0, error: error instanceof Error ? error.message : "parse failed" });
    }
  } else {
    warnings.push("Банк России временно недоступен; используется резервное значение курса ЦБ.");
    recordSourceRun({ sourceKey: "fx.cbr", scope: city, status: "failure", qualityScore: 0, error: cbrResult.reason instanceof Error ? cbrResult.reason.message : "unavailable" });
  }

  if (!runtime.sources["fx.banks"]) {
    warnings.push("Источник банковских курсов отключён администратором; используется резервный снимок.");
    recordSourceRun({ sourceKey: "fx.banks", scope: city, status: "disabled", qualityScore: 0 });
  } else if (bankResult.status === "fulfilled") {
    const parsed = parseBankirosCny(bankResult.value, bankSourceUrls[city]);
    if (parsed.length) {
      bankRates = parsed;
      liveParts += 1;
      banksLive = true;
      recordSourceRun({ sourceKey: "fx.banks", scope: city, status: "success", qualityScore: 100, itemCount: parsed.length, latencyMs: Date.now() - started });
    } else {
      warnings.push("Не удалось извлечь банковские курсы; используется резервный снимок.");
      recordSourceRun({ sourceKey: "fx.banks", scope: city, status: "failure", qualityScore: 0, error: "no rates parsed" });
    }
  } else {
    warnings.push("Источник банковских курсов временно недоступен; используется резервный снимок.");
    recordSourceRun({ sourceKey: "fx.banks", scope: city, status: "failure", qualityScore: 0, error: bankResult.reason instanceof Error ? bankResult.reason.message : "unavailable" });
  }

  if (cached?.state === "stale") {
    if (!cbrLive) { cbr = cached.payload.cbr; warnings.push("Курс ЦБ взят из последнего сохранённого снимка."); }
    if (!banksLive) { bankRates = cached.payload.bankRates; warnings.push("Банковские курсы взяты из последнего сохранённого снимка."); }
  }

  if (liveParts === 0 && cached?.state === "stale") {
    const value: FxSnapshot = {
      ...cached.payload,
      mode: "stale",
      warnings: [...cached.payload.warnings, "Внешние источники временно недоступны. Показан последний сохранённый снимок."],
      cache: { state: "stale", ageSeconds: cached.ageSeconds, qualityScore: cached.qualityScore },
    };
    return jsonWithContext(context, value, { headers: { "cache-control": "private, max-age=30", "x-data-cache": "stale", ...rateLimitHeaders(limit) } });
  }

  const qualityScore = liveParts === 2 ? 100 : liveParts === 1 ? 65 : 10;
  const value: FxSnapshot = {
    city,
    cityLabel: cityLabels[city],
    cbr,
    bankRates,
    fetchedAt: new Date().toISOString(),
    mode: liveParts === 2 ? "live" : "fallback",
    warnings,
    cache: { state: liveParts ? "live" : "fallback", ageSeconds: 0, qualityScore },
  };
  if (liveParts > 0) {
    saveSourceSnapshot({ cacheKey, sourceKey: "fx.aggregate", scope: city, payload: value, ttlMs: CACHE_MS, staleMs: STALE_MS, status: liveParts === 2 ? "live" : "partial", qualityScore, itemCount: bankRates.length + 1, latencyMs: Date.now() - started, error: warnings.join(" ") });
  } else {
    recordSourceRun({ sourceKey: "fx.aggregate", scope: city, status: "fallback", qualityScore, itemCount: bankRates.length + 1, latencyMs: Date.now() - started, error: warnings.join(" ") });
  }
  return jsonWithContext(context, value, {
    headers: { "cache-control": "private, max-age=60", "x-data-cache": value.cache?.state || "live", "x-content-type-options": "nosniff", ...rateLimitHeaders(limit) },
  });
}
