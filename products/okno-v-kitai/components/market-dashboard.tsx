"use client";

import { useMemo, useState } from "react";
import { ArrowDownRight, ArrowUpRight, BarChart3, Building2, ExternalLink, Flame, Gauge, Info } from "lucide-react";
import { marketBrands, marketSources, marketTotals, type BrandOrigin } from "@/lib/market-data";

type OriginFilter = "Все" | BrandOrigin;
type SortKey = "sales2026Ytd" | "sales2025" | "yoy2026";

const number = new Intl.NumberFormat("ru-RU");
const compact = new Intl.NumberFormat("ru-RU", { notation: "compact", maximumFractionDigits: 1 });

export function MarketDashboard() {
  const [origin, setOrigin] = useState<OriginFilter>("Все");
  const [sort, setSort] = useState<SortKey>("sales2026Ytd");

  const rows = useMemo(() => {
    return marketBrands
      .filter((item) => origin === "Все" || item.origin === origin)
      .sort((a, b) => (b[sort] ?? -Infinity) - (a[sort] ?? -Infinity));
  }, [origin, sort]);

  const top2026 = Math.max(...marketBrands.map((item) => item.sales2026Ytd ?? 0));
  const gwm2025 = marketBrands.filter((item) => item.focus === "GWM").reduce((sum, item) => sum + item.sales2025, 0);
  const currentTopFive = marketBrands
    .filter((item) => item.sales2026Ytd !== null)
    .sort((a, b) => (b.sales2026Ytd ?? 0) - (a.sales2026Ytd ?? 0))
    .slice(0, 5)
    .reduce((sum, item) => sum + (item.sales2026Ytd ?? 0), 0);
  const concentration = (currentTopFive / marketTotals.sales2026Ytd) * 100;

  return (
    <main className="mgc-surface min-h-[calc(100vh-4rem)] text-zinc-950">
      <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
        <section className="grid overflow-hidden border border-zinc-300 bg-white lg:grid-cols-[minmax(0,1fr)_390px]">
          <div className="p-6 sm:p-8 lg:p-10">
            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.12em] text-[#285fff]">
              <BarChart3 className="size-5" /> Рынок России
            </div>
            <h1 className="mt-4 max-w-4xl text-3xl font-black tracking-[-0.045em] sm:text-5xl">Продажи и позиции автомобильных марок</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-zinc-600">
              Полный 2025 год, оперативные итоги января–июля 2026 года и динамика к сопоставимому периоду. Отдельный фокус — китайские марки и группа GWM.
            </p>
          </div>
          <div className="border-t border-zinc-300 bg-[#101114] p-6 text-white lg:border-l lg:border-t-0 lg:p-8">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#7d9aff]">Методика</p>
            <p className="mt-4 text-sm leading-6 text-zinc-300">
              2026 — данные АВТОСТАТ/ППК за январь–июль. Значения 2025 ниже первой десятки дополнены рейтингом «Автостат Инфо». Разные методики могут давать небольшое расхождение.
            </p>
            <p className="mt-4 text-xs text-zinc-500">Обновлено {marketTotals.updatedAt}</p>
          </div>
        </section>

        <section className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Kpi label="Рынок 2025" value={compact.format(marketTotals.sales2025)} note="новых легковых" icon={Building2} />
          <Kpi label="2026: 7 месяцев" value={compact.format(marketTotals.sales2026Ytd)} note="+12,2% год к году" icon={Gauge} positive />
          <Kpi label="Лидер иномарок" value="HAVAL" note="99 719 автомобилей" icon={Flame} accent />
          <Kpi label="Доля Китая" value={`${marketTotals.chinaShareJuly2026}%`} note="в июле 2026" icon={BarChart3} />
          <Kpi label="TOP-5" value={`${concentration.toFixed(1)}%`} note="концентрация рынка" icon={Info} />
        </section>

        <section className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
          <div className="border border-zinc-300 bg-white">
            <div className="flex flex-col gap-4 border-b border-zinc-200 p-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#285fff]">Марочный рейтинг</p>
                <h2 className="mt-2 text-2xl font-black tracking-[-0.03em]">Основные марки в России</h2>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <label className="text-xs font-semibold text-zinc-500">Происхождение
                  <select value={origin} onChange={(event) => setOrigin(event.target.value as OriginFilter)} className="mt-1 block h-10 min-w-40 border border-zinc-300 bg-white px-3 text-sm font-semibold text-zinc-900">
                    {(["Все", "Россия", "Китай", "Беларусь", "Другие"] as OriginFilter[]).map((item) => <option key={item}>{item}</option>)}
                  </select>
                </label>
                <label className="text-xs font-semibold text-zinc-500">Сортировка
                  <select value={sort} onChange={(event) => setSort(event.target.value as SortKey)} className="mt-1 block h-10 min-w-44 border border-zinc-300 bg-white px-3 text-sm font-semibold text-zinc-900">
                    <option value="sales2026Ytd">Продажи 2026</option>
                    <option value="sales2025">Продажи 2025</option>
                    <option value="yoy2026">Динамика 2026</option>
                  </select>
                </label>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[780px] border-collapse text-left text-sm">
                <thead className="bg-zinc-100 text-xs font-bold uppercase tracking-[0.08em] text-zinc-500">
                  <tr>
                    <th className="px-5 py-3">Марка</th>
                    <th className="px-4 py-3">2025 год</th>
                    <th className="px-4 py-3">Янв–июль 2026</th>
                    <th className="px-4 py-3">К янв–июлю 2025</th>
                    <th className="px-5 py-3">Сигнал</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((item) => {
                    const width = item.sales2026Ytd ? Math.max(4, (item.sales2026Ytd / top2026) * 100) : 0;
                    return (
                      <tr key={item.brand} className="border-t border-zinc-200 align-top hover:bg-[#285fff]/[0.025]">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-2 font-black">
                            {item.brand}
                            {item.focus === "GWM" && <span title="Группа GWM" className="text-orange-500">🔥</span>}
                          </div>
                          <span className="mt-1 block text-xs text-zinc-500">{item.origin}</span>
                        </td>
                        <td className="px-4 py-4 font-semibold tabular-nums">{number.format(item.sales2025)}</td>
                        <td className="px-4 py-4">
                          {item.sales2026Ytd === null ? (
                            <span className="text-xs text-zinc-400">вне открытого TOP-10</span>
                          ) : (
                            <div className="min-w-44">
                              <span className="font-black tabular-nums">{number.format(item.sales2026Ytd)}</span>
                              <div className="mt-2 h-1.5 bg-zinc-200"><div className="h-full bg-[#285fff]" style={{ width: `${width}%` }} /></div>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-4">
                          {item.yoy2026 === null ? <span className="text-zinc-400">нет базы</span> : <Trend value={item.yoy2026} />}
                        </td>
                        <td className="max-w-xs px-5 py-4 text-xs leading-5 text-zinc-600">{item.note}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="border border-orange-300 bg-orange-50 p-5">
              <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-orange-700"><Flame className="size-4" /> Фокус GWM</p>
              <p className="mt-3 text-3xl font-black tracking-[-0.04em]">{number.format(gwm2025)}</p>
              <p className="mt-1 text-sm text-zinc-600">Haval + TANK + WEY за 2025 год</p>
              <div className="mt-5 border-t border-orange-200 pt-4 text-sm leading-6 text-zinc-700">
                Haval продал 99 719 машин за семь месяцев 2026 года и вырос на 29,5% к сопоставимому периоду.
              </div>
            </div>

            <div className="border border-zinc-300 bg-[#101114] p-5 text-white">
              <p className="text-xs font-black uppercase tracking-[0.14em] text-[#7d9aff]">Как читать данные</p>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-zinc-300">
                <li>• Не сравнивайте семь месяцев 2026 с полным 2025 годом как готовый темп роста.</li>
                <li>• Для динамики используйте отдельную колонку к январю–июлю 2025.</li>
                <li>• SHACMAN относится к грузовому сегменту и не включён в легковой рейтинг.</li>
              </ul>
            </div>

            <div className="border border-zinc-300 bg-white p-5">
              <p className="text-xs font-black uppercase tracking-[0.14em] text-zinc-500">Первоисточники</p>
              <div className="mt-4 space-y-3">
                {marketSources.map((source) => (
                  <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer" className="flex items-start justify-between gap-3 text-sm font-semibold text-[#285fff] hover:underline">
                    {source.label}<ExternalLink className="mt-0.5 size-4 shrink-0" />
                  </a>
                ))}
              </div>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}

function Kpi({ label, value, note, icon: Icon, positive = false, accent = false }: { label: string; value: string; note: string; icon: typeof Gauge; positive?: boolean; accent?: boolean }) {
  return (
    <article className={`border p-5 ${accent ? "border-orange-300 bg-orange-50" : "border-zinc-300 bg-white"}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-black uppercase tracking-[0.1em] text-zinc-500">{label}</p>
        <Icon className={`size-4 ${accent ? "text-orange-500" : "text-[#285fff]"}`} />
      </div>
      <p className="mt-3 text-3xl font-black tracking-[-0.04em]">{value}</p>
      <p className={`mt-1 text-xs ${positive ? "font-bold text-emerald-700" : "text-zinc-500"}`}>{note}</p>
    </article>
  );
}

function Trend({ value }: { value: number }) {
  const positive = value >= 0;
  return <span className={`inline-flex items-center gap-1 font-black tabular-nums ${positive ? "text-emerald-700" : "text-red-600"}`}>{positive ? <ArrowUpRight className="size-4" /> : <ArrowDownRight className="size-4" />}{positive ? "+" : ""}{value.toLocaleString("ru-RU")}%</span>;
}
