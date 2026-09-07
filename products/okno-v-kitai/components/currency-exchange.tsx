"use client";

import { ArrowRightLeft, BadgeRussianRuble, Building2, Calculator, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FxCity, FxSnapshot } from "@/lib/fx";

const formatter = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 });
const rateFormatter = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 4 });

export function CurrencyExchange() {
  const [city, setCity] = useState<FxCity>("kaluga");
  const [data, setData] = useState<FxSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [amount, setAmount] = useState("100");
  const [direction, setDirection] = useState<"cny-rub" | "rub-cny">("cny-rub");

  async function load(selectedCity = city) {
    setLoading(true);
    try {
      const response = await fetch(`/api/fx?city=${selectedCity}`, { cache: "no-store" });
      if (!response.ok) throw new Error("FX request failed");
      setData((await response.json()) as FxSnapshot);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(city);
  }, [city]);

  const result = useMemo(() => {
    const value = Number(amount.replace(",", "."));
    if (!data || !Number.isFinite(value)) return null;
    return direction === "cny-rub" ? value * data.cbr.rubPerCny : value / data.cbr.rubPerCny;
  }, [amount, data, direction]);

  return (
    <section className="mt-8 rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5 sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-cyan-300">
            <BadgeRussianRuble className="size-4" /> Деньги в поездке
          </div>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white sm:text-3xl">Юань ↔ рубль и наличный обмен</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Официальный курс ЦБ — для ориентира и расчётов. Курсы банков показывают, сколько банк покупает и продаёт наличный CNY; перед поездкой в отделение проверьте наличие валюты.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["kaluga", "moskva"] as FxCity[]).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCity(item)}
              className={`rounded-lg border px-3 py-2 text-xs font-semibold ${city === item ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-300" : "border-white/10 text-slate-400"}`}
            >
              {item === "kaluga" ? "Калуга" : "Москва"}
            </button>
          ))}
          <button type="button" onClick={() => void load()} className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-slate-400 hover:text-cyan-300">
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} /> Обновить
          </button>
        </div>
      </div>

      {loading && !data ? (
        <div className="mt-5 rounded-xl border border-white/8 bg-[#071011]/70 p-5 text-sm text-slate-500">Получаем актуальные курсы…</div>
      ) : data ? (
        <>
          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.045] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-cyan-300">Курс ЦБ РФ</p>
              <p className="mt-2 text-3xl font-semibold text-white">1 CNY = {rateFormatter.format(data.cbr.rubPerCny)} ₽</p>
              <p className="mt-2 text-xs text-slate-500">Действует с {data.cbr.effectiveDate}</p>
              <a href={data.cbr.sourceUrl} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-semibold text-cyan-300 hover:text-cyan-200">Банк России ↗</a>
            </div>
            <QuickCard title="100 юаней" value={`${formatter.format(100 * data.cbr.rubPerCny)} ₽`} />
            <QuickCard title="1 рубль" value={`${rateFormatter.format(1 / data.cbr.rubPerCny)} CNY`} />
          </div>

          <div className="mt-4 rounded-xl border border-white/8 bg-[#071011]/70 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-white"><Calculator className="size-4 text-violet-300" /> Конвертер</div>
            <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto_1fr] md:items-end">
              <label className="text-xs font-semibold text-slate-500">
                Сумма
                <input value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" className="mt-2 h-11 w-full rounded-lg border border-white/10 bg-white px-3 text-base text-zinc-900 outline-none focus:border-cyan-400" />
              </label>
              <button type="button" onClick={() => setDirection((value) => value === "cny-rub" ? "rub-cny" : "cny-rub")} className="grid size-11 place-items-center rounded-lg border border-white/10 text-cyan-300" aria-label="Поменять направление">
                <ArrowRightLeft className="size-4" />
              </button>
              <div>
                <p className="text-xs font-semibold text-slate-500">{direction === "cny-rub" ? "CNY → RUB" : "RUB → CNY"}</p>
                <div className="mt-2 flex min-h-11 items-center rounded-lg border border-white/8 bg-white/[0.035] px-3 text-lg font-semibold text-white">
                  {result == null ? "—" : `${formatter.format(result)} ${direction === "cny-rub" ? "₽" : "CNY"}`}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 flex items-center gap-2 text-sm font-semibold text-white"><Building2 className="size-4 text-cyan-300" /> Где купить/продать наличный CNY — {data.cityLabel}</div>
          <div className="mt-3 overflow-x-auto rounded-xl border border-white/8">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-white/[0.035] text-xs uppercase tracking-[0.08em] text-slate-500">
                <tr><th className="px-4 py-3">Банк</th><th className="px-4 py-3">Банк покупает CNY</th><th className="px-4 py-3">Банк продаёт CNY</th><th className="px-4 py-3">Обновлено</th></tr>
              </thead>
              <tbody>
                {data.bankRates.map((rate) => (
                  <tr key={rate.bank} className="border-t border-white/8">
                    <td className="px-4 py-3 font-semibold text-white"><a href={rate.sourceUrl} target="_blank" rel="noopener noreferrer" className="hover:text-cyan-300">{rate.bank}</a></td>
                    <td className="px-4 py-3 text-slate-300">{rateFormatter.format(rate.buy)} ₽</td>
                    <td className="px-4 py-3 font-semibold text-cyan-300">{rateFormatter.format(rate.sell)} ₽</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{rate.updatedAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-col gap-1 text-xs leading-5 text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <span>{data.mode === "live" ? "Онлайн-данные получены успешно." : "Часть данных показана из резервного снимка."}</span>
            <span>Получено сервером: {new Date(data.fetchedAt).toLocaleString("ru-RU")}</span>
          </div>
          {data.warnings.length > 0 && <p className="mt-2 text-xs leading-5 text-amber-200">{data.warnings.join(" ")}</p>}
        </>
      ) : (
        <div className="mt-5 rounded-xl border border-amber-300/18 bg-amber-300/[0.055] p-4 text-sm text-slate-400">Курсы сейчас недоступны. Повторите обновление; остальная часть раздела продолжает работать.</div>
      )}
    </section>
  );
}

function QuickCard({ title, value }: { title: string; value: string }) {
  return <div className="rounded-xl border border-white/8 bg-[#071011]/70 p-4"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{title}</p><p className="mt-2 text-3xl font-semibold text-white">{value}</p><p className="mt-2 text-xs text-slate-500">Расчёт по официальному курсу ЦБ</p></div>;
}
