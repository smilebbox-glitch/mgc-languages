export type BrandOrigin = "Россия" | "Китай" | "Беларусь" | "Другие";

export type MarketBrand = {
  brand: string;
  origin: BrandOrigin;
  sales2025: number;
  sales2026Ytd: number | null;
  yoy2026: number | null;
  note: string;
  focus?: "GWM";
};

export const marketBrands: MarketBrand[] = [
  { brand: "LADA", origin: "Россия", sales2025: 330357, sales2026Ytd: 181357, yoy2026: -1.3, note: "Лидер рынка; российское производство." },
  { brand: "HAVAL", origin: "Китай", sales2025: 173434, sales2026Ytd: 99719, yoy2026: 29.5, note: "Лидер среди иностранных марок; локализация GWM в Тульской области.", focus: "GWM" },
  { brand: "TENET", origin: "Россия", sales2025: 33488, sales2026Ytd: 76546, yoy2026: null, note: "Новый локальный бренд на технологиях Chery; сопоставимой базы 2025 года нет." },
  { brand: "GEELY", origin: "Китай", sales2025: 93988, sales2026Ytd: 45250, yoy2026: 2.9, note: "В 2026 году вернулся к умеренному росту." },
  { brand: "BELGEE", origin: "Беларусь", sales2025: 68091, sales2026Ytd: 33702, yoy2026: 38.4, note: "Белорусская сборка моделей на платформе Geely." },
  { brand: "CHANGAN", origin: "Китай", sales2025: 64032, sales2026Ytd: 28637, yoy2026: -24.2, note: "Падение к январю–июлю 2025 года." },
  { brand: "TOYOTA", origin: "Другие", sales2025: 28761, sales2026Ytd: 20356, yoy2026: 86.4, note: "Продажи поддерживает параллельный импорт." },
  { brand: "JETOUR", origin: "Китай", sales2025: 36511, sales2026Ytd: 20320, yoy2026: 1.0, note: "Стабильный объём и расширение модельной линейки." },
  { brand: "MAZDA", origin: "Другие", sales2025: 6902, sales2026Ytd: 14821, yoy2026: 669.9, note: "Рост с низкой базы за счёт альтернативных каналов поставки." },
  { brand: "GAC", origin: "Китай", sales2025: 18202, sales2026Ytd: 11323, yoy2026: 11.1, note: "Рост быстрее рынка в открытом рейтинге." },
  { brand: "CHERY", origin: "Китай", sales2025: 99936, sales2026Ytd: null, yoy2026: null, note: "В 2026 году часть объёма перешла к локальному бренду TENET." },
  { brand: "SOLARIS", origin: "Россия", sales2025: 34526, sales2026Ytd: null, yoy2026: null, note: "Российская сборка моделей на бывшей корейской производственной базе." },
  { brand: "OMODA", origin: "Китай", sales2025: 28779, sales2026Ytd: null, yoy2026: null, note: "Суббренд Chery; в открытый TOP-10 января–июля 2026 не вошёл." },
  { brand: "EXEED", origin: "Китай", sales2025: 21704, sales2026Ytd: null, yoy2026: null, note: "Премиальный суббренд Chery." },
  { brand: "JAECOO", origin: "Китай", sales2025: 18742, sales2026Ytd: null, yoy2026: null, note: "Суббренд Chery; отслеживается отдельно от OMODA." },
  { brand: "TANK", origin: "Китай", sales2025: 18602, sales2026Ytd: null, yoy2026: null, note: "Премиальные внедорожники группы GWM.", focus: "GWM" },
  { brand: "МОСКВИЧ", origin: "Россия", sales2025: 15637, sales2026Ytd: null, yoy2026: null, note: "Российский бренд и локальная сборка." },
  { brand: "LI AUTO", origin: "Китай", sales2025: 13088, sales2026Ytd: null, yoy2026: null, note: "Последовательные гибриды; часть продаж шла через альтернативный импорт." },
  { brand: "HONGQI", origin: "Китай", sales2025: 10002, sales2026Ytd: null, yoy2026: null, note: "Премиальный бренд FAW." },
  { brand: "VOYAH", origin: "Китай", sales2025: 9459, sales2026Ytd: null, yoy2026: null, note: "Электромобили и гибриды Dongfeng." },
  { brand: "WEY", origin: "Китай", sales2025: 2191, sales2026Ytd: null, yoy2026: null, note: "Премиальные гибриды группы GWM.", focus: "GWM" },
];

export const marketTotals = {
  sales2025: 1326016,
  sales2026Ytd: 730714,
  yoy2026: 12.2,
  chinaShareJuly2026: 40.0,
  period2026: "январь–июль 2026",
  updatedAt: "2 сентября 2026",
};

export const marketSources = [
  {
    label: "АВТОСТАТ / ППК — январь–июль 2026",
    url: "https://www.autostat.ru/press-releases/62855/",
  },
  {
    label: "АВТОСТАТ — итоги 2025 года",
    url: "https://www.autostat.ru/press-releases/61576/",
  },
  {
    label: "Автостат Инфо — 100 марок за 2025 год",
    url: "https://xn----7sbbeeptbfadjdvm5ab9bqj.xn--p1ai/2026/01/30/avtomobili-v-rossii-2025-100-brendov/",
  },
  {
    label: "Автостат Инфо — структура рынка июля 2026",
    url: "https://avtostat-info.ru/",
  },
];
