export type FxCity = "kaluga" | "moskva";

export type BankCashRate = {
  bank: string;
  buy: number;
  sell: number;
  updatedAt: string;
  sourceUrl: string;
};

export type FxSnapshot = {
  city: FxCity;
  cityLabel: string;
  cbr: {
    rubPerCny: number;
    effectiveDate: string;
    sourceUrl: string;
  };
  bankRates: BankCashRate[];
  fetchedAt: string;
  mode: "live" | "stale" | "fallback";
  cache?: { state: "fresh" | "stale" | "expired" | "miss" | "live" | "fallback"; ageSeconds?: number; qualityScore?: number };
  warnings: string[];
};

export const cityLabels: Record<FxCity, string> = {
  kaluga: "Калуга",
  moskva: "Москва",
};

export const bankSourceUrls: Record<FxCity, string> = {
  kaluga: "https://bankiros.ru/currency/cny/kaluga",
  moskva: "https://bankiros.ru/currency/cny/moskva",
};

export function parseCbrCnyXml(xml: string) {
  const date = xml.match(/<ValCurs[^>]*Date="([^"]+)"/iu)?.[1] ?? "";
  const block = [...xml.matchAll(/<Valute\b[^>]*>([\s\S]*?)<\/Valute>/giu)]
    .map((match) => match[1])
    .find((value) => /<CharCode>\s*CNY\s*<\/CharCode>/iu.test(value));
  if (!block) throw new Error("CNY is absent in CBR response");

  const nominalRaw = block.match(/<Nominal>\s*([^<]+)\s*<\/Nominal>/iu)?.[1];
  const valueRaw = block.match(/<Value>\s*([^<]+)\s*<\/Value>/iu)?.[1];
  const nominal = Number((nominalRaw ?? "1").replace(",", "."));
  const value = Number((valueRaw ?? "").replace(",", "."));
  if (!Number.isFinite(value) || !Number.isFinite(nominal) || nominal <= 0) {
    throw new Error("Invalid CBR CNY value");
  }
  return { rubPerCny: value / nominal, effectiveDate: date };
}

function decodeHtml(value: string) {
  const named: Record<string, string> = {
    amp: "&",
    quot: '"',
    apos: "'",
    nbsp: " ",
    laquo: "«",
    raquo: "»",
    mdash: "—",
    ndash: "–",
  };
  return value
    .replace(/<script\b[\s\S]*?<\/script>/giu, " ")
    .replace(/<style\b[\s\S]*?<\/style>/giu, " ")
    .replace(/<br\s*\/?\s*>/giu, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&#(\d+);/g, (_, code: string) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/giu, (_, code: string) => String.fromCodePoint(parseInt(code, 16)))
    .replace(/&([a-z]+);/giu, (match, name: string) => named[name.toLowerCase()] ?? match)
    .replace(/\s+/g, " ")
    .trim();
}

const knownBanks = [
  "Совкомбанк",
  "Фора-Банк",
  "СберБанк",
  "Банк ПСБ",
  "Россельхозбанк",
  "Банк ВТБ",
  "Кошелев-Банк",
  "Альфа-Банк",
  "Инго Банк",
  "Банк Казани",
  "Норвик Банк (Вятка Банк)",
  "Экспобанк",
  "АО КБ «Юнистрим»",
  "Авангард",
  "СДМ-Банк",
  "Агророс",
  "Банк 131",
  "Банк Уралсиб",
  "Газпромбанк",
  "Цифра банк",
  "Трансстройбанк",
];

export function parseBankirosCny(html: string, sourceUrl: string): BankCashRate[] {
  const text = decodeHtml(html);
  const results: BankCashRate[] = [];
  for (const bank of knownBanks) {
    let offset = 0;
    while (offset < text.length) {
      const index = text.indexOf(bank, offset);
      if (index < 0) break;
      offset = index + bank.length;
      const segment = text.slice(offset, Math.min(text.length, offset + 900));
      const dateMatch = segment.match(/(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})/u);
      if (!dateMatch || dateMatch.index == null) continue;
      const beforeDate = segment.slice(0, dateMatch.index);
      const values = [...beforeDate.matchAll(/(?<!\d)(\d{1,3}(?:[.,]\d{1,4})?)(?!\d)/gu)]
        .map((match) => Number(match[1].replace(",", ".")))
        .filter((value) => Number.isFinite(value) && value >= 5 && value <= 30);
      if (values.length < 2) continue;
      const buy = values.at(-2)!;
      const sell = values.at(-1)!;
      if (buy > 30 || sell > 30) continue;
      results.push({ bank, buy, sell, updatedAt: `${dateMatch[1]} ${dateMatch[2]}`, sourceUrl });
      break;
    }
  }

  return [...new Map(results.map((item) => [item.bank, item])).values()]
    .sort((left, right) => left.sell - right.sell)
    .slice(0, 10);
}

const fallbackByCity: Record<FxCity, BankCashRate[]> = {
  kaluga: [
    { bank: "Банк ПСБ", buy: 12.99, sell: 13.59, updatedAt: "06.09.2026 01:30", sourceUrl: bankSourceUrls.kaluga },
    { bank: "Банк ВТБ", buy: 13.05, sell: 13.85, updatedAt: "06.09.2026 01:30", sourceUrl: bankSourceUrls.kaluga },
    { bank: "Фора-Банк", buy: 13.2, sell: 13.9, updatedAt: "06.09.2026 01:30", sourceUrl: bankSourceUrls.kaluga },
    { bank: "СберБанк", buy: 12.96, sell: 13.92, updatedAt: "06.09.2026 01:31", sourceUrl: bankSourceUrls.kaluga },
    { bank: "Россельхозбанк", buy: 12.47, sell: 14.02, updatedAt: "06.09.2026 00:30", sourceUrl: bankSourceUrls.kaluga },
  ],
  moskva: [
    { bank: "Инго Банк", buy: 12.9, sell: 13.13, updatedAt: "06.09.2026 19:15", sourceUrl: bankSourceUrls.moskva },
    { bank: "Альфа-Банк", buy: 13.0, sell: 13.15, updatedAt: "06.09.2026 18:15", sourceUrl: bankSourceUrls.moskva },
    { bank: "Банк Казани", buy: 13.12, sell: 13.25, updatedAt: "06.09.2026 15:45", sourceUrl: bankSourceUrls.moskva },
    { bank: "Экспобанк", buy: 13.0, sell: 13.5, updatedAt: "06.09.2026 14:15", sourceUrl: bankSourceUrls.moskva },
    { bank: "СберБанк", buy: 12.96, sell: 13.92, updatedAt: "06.09.2026 00:31", sourceUrl: bankSourceUrls.moskva },
  ],
};

export function fallbackFxSnapshot(city: FxCity): FxSnapshot {
  return {
    city,
    cityLabel: cityLabels[city],
    cbr: {
      rubPerCny: 12.8849,
      effectiveDate: "06.09.2026",
      sourceUrl: "https://www.cbr.ru/currency_base/daily/",
    },
    bankRates: fallbackByCity[city],
    fetchedAt: new Date().toISOString(),
    mode: "fallback",
    warnings: ["Показан резервный снимок. Перед обменом уточните курс и наличие CNY в конкретном отделении."],
  };
}
