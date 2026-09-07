import type { NewsItem } from "@/lib/data";
import { marketBrands, marketTotals } from "@/lib/market-data";

const number = new Intl.NumberFormat("ru-RU");
const autostat2025 = "https://www.autostat.ru/press-releases/61576/";
const autostat2026 = "https://www.autostat.ru/press-releases/62855/";
const brandRanking2025 =
  "https://xn----7sbbeeptbfadjdvm5ab9bqj.xn--p1ai/2026/01/30/avtomobili-v-rossii-2025-100-brendov/";

function focusBrand(brand: string): NewsItem["brand"] {
  return ["HAVAL", "TANK", "WEY"].includes(brand) ? "GWM" : "Отрасль";
}

function salesSummary(item: (typeof marketBrands)[number]) {
  const current = item.sales2026Ytd === null
    ? "В открытом рейтинге TOP-10 за январь–июль 2026 года отдельное значение не опубликовано."
    : `За январь–июль 2026 года зарегистрировано ${number.format(item.sales2026Ytd)} автомобилей${item.yoy2026 === null ? "" : `, динамика к сопоставимому периоду — ${item.yoy2026 > 0 ? "+" : ""}${item.yoy2026.toLocaleString("ru-RU")}%`}.`;
  return `За полный 2025 год в России зарегистрировано ${number.format(item.sales2025)} новых автомобилей ${item.brand}. ${current} ${item.note}`;
}

export const analysisKnowledge: NewsItem[] = [
  {
    id: "market-total-russia-2025-2026",
    title: "Российский рынок новых легковых автомобилей: итоги 2025 года и семь месяцев 2026 года",
    summary: `В 2025 году рынок составил ${number.format(marketTotals.sales2025)} автомобилей. За январь–июль 2026 года зарегистрировано ${number.format(marketTotals.sales2026Ytd)} машин, что на ${marketTotals.yoy2026.toLocaleString("ru-RU")}% больше сопоставимого периода; доля китайских марок в июле — ${marketTotals.chinaShareJuly2026.toLocaleString("ru-RU")}%.`,
    source: "АВТОСТАТ / ППК",
    sourceType: "media",
    url: autostat2026,
    publishedAt: "2026-09-02T12:00:00+03:00",
    market: "Россия",
    brand: "Отрасль",
  },
  ...marketBrands.map<NewsItem>((item) => ({
    id: `market-brand-${item.brand.toLocaleLowerCase("ru-RU").replace(/[^\p{L}\p{N}]+/gu, "-")}`,
    title: `Продажи ${item.brand} в России: 2025 год и январь–июль 2026 года`,
    summary: salesSummary(item),
    source: item.sales2026Ytd === null ? "Автостат Инфо" : "АВТОСТАТ / ППК",
    sourceType: "media",
    url: item.sales2026Ytd === null ? brandRanking2025 : autostat2026,
    publishedAt: "2026-09-02T12:00:00+03:00",
    market: "Россия",
    brand: focusBrand(item.brand),
  })),
  {
    id: "market-methodology-2025",
    title: "Методика марочного рейтинга российского авторынка за 2025 год",
    summary: "Годовые значения по основным маркам собраны из рейтинга регистраций новых легковых автомобилей. Итог рынка АВТОСТАТ/ППК и марочный рейтинг Автостат Инфо могут немного различаться из-за методики учёта.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: autostat2025,
    publishedAt: "2026-01-13T12:00:00+03:00",
    market: "Россия",
    brand: "Отрасль",
  },
];
