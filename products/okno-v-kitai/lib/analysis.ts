import type { Market, NewsItem } from "@/lib/data";

export type AnalysisFocus = "SHACMAN" | "GWM" | "Все";
export type AnalysisMarket = "Все рынки" | Market;
export type AnalysisPeriod = "90" | "365" | "all";
export type AnalysisMode = "evidence" | "model";

export type AnalysisRequest = {
  focus: AnalysisFocus;
  market: AnalysisMarket;
  period: AnalysisPeriod;
  query: string;
  items: NewsItem[];
};

export type EvidenceItem = NewsItem & {
  citation: number;
  relevance: number;
  matchedTerms: string[];
};

export type AnalysisResult = {
  summary: string;
  signals: Array<{ claim: string; impact: string; citation: number }>;
  risks: string[];
  actions: string[];
  evidence: EvidenceItem[];
  matchedTerms: string[];
  mode: AnalysisMode;
  confidence: {
    level: "Высокая" | "Средняя" | "Ограниченная";
    score: number;
    reason: string;
  };
  coverage: {
    materials: number;
    sources: number;
    focusMaterials: number;
    officialMaterials: number;
  };
};

const stopWords = new Set([
  "какие", "какой", "какая", "которые", "может", "могут", "будет", "будут",
  "нужно", "этого", "этой", "после", "перед", "через", "наших", "компании",
  "россии", "китае", "рынке", "также", "чтобы", "между", "сейчас", "повлиять",
  "происходит", "изменилось", "изменения", "показать", "расскажи", "почему",
]);

const topicGroups = [
  { key: "sales", pattern: /продаж|спрос|рынок|доля|дилер|регистрац|цена|выручк/iu, terms: ["продаж", "спрос", "рынок", "доля", "регистрац", "дилер", "цена", "выручк"] },
  { key: "localization", pattern: /локализ|производ|завод|сборк|мощност|штампов|сварк|окраск/iu, terms: ["локализ", "производ", "завод", "сборк", "мощност", "компонент", "штампов", "сварк", "окраск"] },
  { key: "supply", pattern: /постав|логист|компонент|цепоч|дефицит|закуп|склад/iu, terms: ["постав", "логист", "компонент", "цепоч", "дефицит", "склад", "закуп"] },
  { key: "geopolitics", pattern: /санкц|геополит|экспорт|импорт|тариф|пошлин|огранич|комплаенс|регулир/iu, terms: ["санкц", "экспорт", "импорт", "тариф", "пошлин", "огранич", "комплаенс", "регулир"] },
  { key: "technology", pattern: /технолог|электро|гибрид|батаре|автопилот|двигател|трансмисс|телемат|безопасност/iu, terms: ["технолог", "электро", "гибрид", "батаре", "автопилот", "двигател", "трансмисс", "телемат", "безопасност"] },
  { key: "strategy", pattern: /стратег|риск|решени|инвестиц|партнер|развити|руковод|план/iu, terms: ["стратег", "риск", "план", "инвестиц", "партнер", "развити", "руковод"] },
] as const;

type TopicKey = (typeof topicGroups)[number]["key"];

const brandAliases = [
  { focus: "SHACMAN" as const, pattern: /shacman|shaanxi|шакман|шаанси|陕汽/iu, terms: ["shacman", "shaanxi", "шакман", "шаанси", "陕汽"] },
  { focus: "GWM" as const, pattern: /\bgwm\b|great\s*wall|haval|хавал|хавейл|\btank\b|\bwey\b|poer|пикап|长城|哈弗|坦克|魏牌/iu, terms: ["gwm", "great wall", "haval", "хавал", "хавейл", "tank", "wey", "poer", "пикап", "长城", "哈弗", "坦克", "魏牌"] },
];

function normalize(value: string) {
  return value.toLocaleLowerCase("ru-RU").replaceAll("ё", "е").replace(/\s+/gu, " ").trim();
}

function tokens(value: string) {
  return normalize(value).match(/[\p{L}\p{N}]{3,}/gu)?.filter((term) => !stopWords.has(term)) ?? [];
}

function topicKeys(value: string): TopicKey[] {
  return topicGroups.filter((group) => group.pattern.test(value)).map((group) => group.key);
}

function queryTerms(query: string, focus: AnalysisFocus) {
  const expandedTopics = topicGroups.filter((group) => group.pattern.test(query)).flatMap((group) => group.terms);
  const explicitBrands = brandAliases.filter((group) => group.pattern.test(query)).flatMap((group) => group.terms);
  const selectedBrand = focus === "Все" ? [] : brandAliases.find((group) => group.focus === focus)?.terms ?? [];
  return [...new Set([...tokens(query), ...expandedTopics, ...explicitBrands, ...selectedBrand])].slice(0, 42);
}

function compactSentence(value: string, maxLength = 230) {
  const clean = value.replace(/\s+/gu, " ").trim();
  const first = clean.match(/^[^.!?]+[.!?]?/u)?.[0] ?? clean;
  const withoutDots = first.replace(/(?:…|\.{2,})+$/u, "").trim();
  const shortened = withoutDots.length > maxLength
    ? withoutDots.slice(0, maxLength - 4).replace(/\s+\S*$/u, "").replace(/[,:;—–\s]+$/u, "").trim()
    : withoutDots;
  return /[.!?]$/u.test(shortened) ? shortened : `${shortened}.`;
}

function impactFor(item: NewsItem, queryTopics: TopicKey[]) {
  const topics = topicKeys(`${item.title} ${item.summary}`);
  const primary = topics.find((topic) => queryTopics.includes(topic)) ?? topics[0];
  if (primary === "geopolitics") return "Проверить нормативный источник, экспортные ограничения, таможенные условия и влияние на поставки.";
  if (primary === "localization") return "Оценить влияние на глубину локализации, загрузку мощностей, себестоимость и доступность компонентов.";
  if (primary === "supply") return "Сопоставить сигнал со сроками поставок, запасами и критическими позициями спецификации.";
  if (primary === "sales") return "Сверить показатель с регистрациями, сопоставимым периодом, ценой и дилерскими остатками.";
  if (primary === "technology") return "Проверить влияние на продуктовую дорожную карту, сертификацию и конкурентоспособность.";
  return "Уточнить влияние на продуктовый план, партнёров и российско-китайскую стратегию.";
}

function uniqueNews(items: NewsItem[]) {
  const map = new Map<string, NewsItem>();
  for (const item of items) {
    if (!/^https?:\/\//u.test(item.url)) continue;
    const key = item.id.startsWith("market-") ? item.id : item.url;
    if (!map.has(key)) map.set(key, item);
  }
  return [...map.values()];
}

function titleFingerprint(value: string) {
  return normalize(value).replace(/[^\p{L}\p{N}]+/gu, "").slice(0, 90);
}

function selectDiverse<T extends { item: NewsItem; score: number; matchedTerms: string[] }>(ranked: T[]) {
  const selected: T[] = [];
  const titleKeys = new Set<string>();
  const perSource = new Map<string, number>();
  for (const candidate of ranked) {
    const key = titleFingerprint(candidate.item.title);
    if (titleKeys.has(key)) continue;
    const sourceCount = perSource.get(candidate.item.source) ?? 0;
    if (sourceCount >= 3 && selected.length >= 4) continue;
    selected.push(candidate);
    titleKeys.add(key);
    perSource.set(candidate.item.source, sourceCount + 1);
    if (selected.length === 8) break;
  }
  return selected;
}

function isBroadQuestion(query: string, queryTopics: TopicKey[]) {
  return tokens(query).length <= 2 && queryTopics.length === 0;
}

export function buildAnalysis(request: AnalysisRequest): AnalysisResult {
  const terms = queryTerms(request.query, request.focus);
  const queryTopics = topicKeys(request.query);
  const broadQuestion = isBroadQuestion(request.query, queryTopics);
  const now = Date.now();
  const periodDays = request.period === "all" ? Number.POSITIVE_INFINITY : Number(request.period);
  const corpus = uniqueNews(request.items).filter((item) => {
    const published = new Date(item.publishedAt).getTime();
    const age = Number.isFinite(published) ? Math.max(0, (now - published) / 86_400_000) : Number.POSITIVE_INFINITY;
    return age <= periodDays && (request.focus === "Все" || item.brand === request.focus) && (request.market === "Все рынки" || item.market === request.market);
  });

  const averageLength = corpus.reduce((sum, item) => sum + tokens(`${item.title} ${item.summary}`).length, 0) / Math.max(1, corpus.length);
  const documentFrequency = new Map<string, number>();
  for (const rawTerm of terms) {
    const term = normalize(rawTerm);
    documentFrequency.set(term, corpus.filter((item) => normalize(`${item.title} ${item.summary} ${item.originalTitle ?? ""} ${item.brand}`).includes(term)).length);
  }

  const ranked = corpus.map((item) => {
    const title = normalize(item.title);
    const summary = normalize(item.summary);
    const original = normalize(item.originalTitle ?? "");
    const text = `${title} ${summary} ${original} ${normalize(item.brand)}`;
    const documentTokens = tokens(text);
    const matchedTerms = terms.filter((term) => text.includes(normalize(term)));
    let lexical = 0;
    for (const rawTerm of matchedTerms) {
      const term = normalize(rawTerm);
      const frequency = documentTokens.filter((token) => token.includes(term) || term.includes(token)).length || 1;
      const df = documentFrequency.get(term) ?? 0;
      const idf = Math.log(1 + (corpus.length - df + 0.5) / (df + 0.5));
      const fieldWeight = title.includes(term) ? 2.8 : original.includes(term) ? 1.8 : 1;
      lexical += idf * ((frequency * 2.2) / (frequency + 1.2 * (0.25 + 0.75 * documentTokens.length / Math.max(1, averageLength)))) * fieldWeight;
    }
    const sharedTopics = topicKeys(text).filter((topic) => queryTopics.includes(topic)).length;
    const sourceWeight = item.sourceType === "official" ? 9 : item.sourceType === "media" ? 6 : 3;
    const age = Math.max(0, (now - new Date(item.publishedAt).getTime()) / 86_400_000);
    const freshness = Math.max(0, 9 - age / 35);
    const focusWeight = request.focus !== "Все" && item.brand === request.focus ? 14 : item.brand === "Отрасль" ? 0 : 5;
    const numberIntent = /продаж|рынок|доля|динамик|сколько|2025|2026/iu.test(request.query) && item.id.startsWith("market-") ? 22 : 0;
    return { item, score: lexical * 8 + sharedTopics * 13 + sourceWeight + freshness + focusWeight + numberIntent, matchedTerms, sharedTopics };
  }).filter(({ matchedTerms, sharedTopics }) => broadQuestion || matchedTerms.length > 0 || sharedTopics > 0)
    .sort((left, right) => right.score - left.score || +new Date(right.item.publishedAt) - +new Date(left.item.publishedAt));

  const diverse = selectDiverse(ranked);
  const maxScore = diverse[0]?.score ?? 1;
  const evidence: EvidenceItem[] = diverse.map(({ item, score, matchedTerms }, index) => ({
    ...item,
    citation: index + 1,
    relevance: Math.max(1, Math.min(100, Math.round(score / maxScore * 100))),
    matchedTerms: [...new Set(matchedTerms.map(normalize))].slice(0, 7),
  }));

  const sources = new Set(evidence.map((item) => item.source)).size;
  const focusMaterials = request.focus === "Все" ? evidence.filter((item) => item.brand !== "Отрасль").length : evidence.filter((item) => item.brand === request.focus).length;
  const officialMaterials = evidence.filter((item) => item.sourceType === "official").length;
  const recentMaterials = evidence.filter((item) => now - new Date(item.publishedAt).getTime() <= 120 * 86_400_000).length;
  const confidenceScore = Math.min(100, evidence.length * 7 + sources * 8 + officialMaterials * 5 + recentMaterials * 3);
  const level = confidenceScore >= 75 ? "Высокая" : confidenceScore >= 45 ? "Средняя" : "Ограниченная";
  const signalCandidates = evidence.filter((item, index, list) => list.findIndex((other) => compactSentence(other.summary) === compactSentence(item.summary)) === index).slice(0, 3);
  const signals = signalCandidates.map((item) => ({ claim: compactSentence(item.summary), impact: impactFor(item, queryTopics), citation: item.citation }));
  const supporting = evidence.find((item) => item.citation !== 1 && item.source !== evidence[0]?.source) ?? evidence[1];
  const summary = evidence.length
    ? `Ключевой ответ: ${compactSentence(evidence[0].summary)} [1]${supporting ? ` Связанный подтверждённый сигнал: ${compactSentence(supporting.summary)} [${supporting.citation}]` : ""}`
    : "По выбранному фокусу, рынку и периоду доказательных материалов недостаточно. Уточните компанию или показатель либо расширьте период.";

  const queryText = normalize(request.query);
  const risks = [
    ...(/санкц|экспорт|импорт|геополит|пошлин|тариф|огранич/iu.test(queryText) ? ["Не считать санкционный или экспортный риск подтверждённым без официального нормативного документа."] : []),
    ...(/продаж|рынок|дилер|спрос|доля/iu.test(queryText) ? ["Сравнивать только одинаковые периоды: семь месяцев 2026 года нельзя напрямую сопоставлять с полным 2025 годом."] : []),
    ...(/постав|логист|компонент|локализ|завод/iu.test(queryText) ? ["Заявленная локализация не гарантирует доступность критических компонентов и стабильный срок поставки."] : []),
    ...(sources < 2 && evidence.length ? ["Основной вывод пока опирается на один источник и требует независимого подтверждения."] : []),
    "Дата публикации может отличаться от даты события; перед решением проверьте первоисточник.",
  ].slice(0, 3);
  const actions = [
    evidence[0] ? "Открыть источник [1] и отдельно зафиксировать факт, показатель, период и дату события." : "Расширить период поиска и добавить в вопрос измеримый показатель.",
    ...(/продаж|рынок|дилер|спрос|доля/iu.test(queryText) ? ["Сопоставить сигнал с внутренними продажами, складом, ценами и дилерским покрытием."] : []),
    ...(/постав|логист|компонент|локализ|завод/iu.test(queryText) ? ["Проверить влияние на спецификацию, закупочный план и запас критических компонентов."] : []),
    ...(/стратег|инвестиц|партнер|развити/iu.test(queryText) ? ["Сформировать три сценария — базовый, риск и возможность — с ответственными и контрольной датой."] : []),
    "Повторить проверку после появления новых данных и отметить, какие предположения подтвердились.",
  ].slice(0, 3);

  return {
    summary,
    signals,
    risks,
    actions,
    evidence,
    matchedTerms: terms.slice(0, 14),
    mode: "evidence",
    confidence: {
      level,
      score: confidenceScore,
      reason: evidence.length ? `${evidence.length} релевантных материалов, ${sources} независимых источников, ${recentMaterials} свежих публикаций и ${officialMaterials} официальных материалов.` : "Релевантные публикации в выбранном срезе не найдены.",
    },
    coverage: { materials: evidence.length, sources, focusMaterials, officialMaterials },
  };
}
