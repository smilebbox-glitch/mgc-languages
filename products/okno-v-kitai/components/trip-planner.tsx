"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  BedDouble,
  Calculator,
  CalendarDays,
  Check,
  CheckCircle2,
  Clock3,
  Download,
  FileText,
  Hotel,
  Plane,
  Save,
  ShieldAlert,
  Ticket,
  TrainFront,
  Users,
  WalletCards,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TripWorkspaceNav } from "@/components/trip-workspace-nav";
import { autoEvents, eventGuidance } from "@/lib/data";
import { eventTravelPlans } from "@/lib/travel";
import { tripBudgetDefaults, tripBudgetNotice } from "@/lib/trip-planning";

type BudgetState = {
  eventId: string;
  travelers: number;
  rooms: number;
  nights: number;
  allowanceDays: number;
  flight: number;
  hotel: number;
  ticket: number;
  transport: number;
  allowance: number;
  documents: number;
};

const storageKey = "okno-v-kitay-trip-budget-v1";
const defaultEventId = "bauma-china-2026";
const rubles = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });

function makeDefault(eventId: string, travelers = 1): BudgetState {
  const plan = eventTravelPlans[eventId];
  const defaults = tripBudgetDefaults[eventId];
  return {
    eventId,
    travelers,
    rooms: travelers,
    nights: plan?.nights ?? 5,
    allowanceDays: (plan?.nights ?? 5) + 2,
    flight: defaults?.flightPerPerson ?? 65000,
    hotel: defaults?.hotelPerRoomNight ?? 10000,
    ticket: defaults?.ticketPerPerson ?? 0,
    transport: defaults?.localTransportPerPerson ?? 9000,
    allowance: defaults?.dailyAllowancePerPerson ?? 6000,
    documents: defaults?.documentsPerPerson ?? 18000,
  };
}

function safeNumber(value: string, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : fallback;
}

function downloadText(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function TripPlanner() {
  const [budget, setBudget] = useState<BudgetState>(() => makeDefault(defaultEventId));
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const load = window.setTimeout(() => {
      try {
        const stored = window.localStorage.getItem(storageKey);
        if (stored) setBudget(JSON.parse(stored) as BudgetState);
      } catch {
        // Локальное сохранение необязательно для расчёта.
      }
    }, 0);
    return () => window.clearTimeout(load);
  }, []);

  const event = autoEvents.find((item) => item.id === budget.eventId) ?? autoEvents[0];
  const plan = eventTravelPlans[budget.eventId];
  const guidance = eventGuidance[budget.eventId];
  const afterConfirmedVisaFreePeriod = event.start > "2026-09-14";
  const availableEvents = autoEvents.filter((item) => eventTravelPlans[item.id]);

  const rows = useMemo(() => [
    { key: "flight", label: "Перелёт", icon: Plane, value: budget.flight * budget.travelers },
    { key: "hotel", label: "Отель", icon: Hotel, value: budget.hotel * budget.rooms * budget.nights },
    { key: "ticket", label: "Билеты на выставку", icon: Ticket, value: budget.ticket * budget.travelers },
    { key: "transport", label: "Транспорт в городе", icon: TrainFront, value: budget.transport * budget.travelers },
    { key: "allowance", label: "Суточные", icon: WalletCards, value: budget.allowance * budget.allowanceDays * budget.travelers },
    { key: "documents", label: "Документы и страховка", icon: FileText, value: budget.documents * budget.travelers },
  ], [budget]);
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  const perPerson = total / Math.max(1, budget.travelers);

  function changeEvent(eventId: string) {
    setBudget(makeDefault(eventId, budget.travelers));
    setSaved(false);
  }

  function update<K extends keyof BudgetState>(key: K, value: BudgetState[K]) {
    setBudget((current) => ({ ...current, [key]: value }));
    setSaved(false);
  }

  function saveDraft() {
    window.localStorage.setItem(storageKey, JSON.stringify(budget));
    setSaved(true);
  }

  function exportCsv() {
    const lines = [
      ["Командировка", event.name],
      ["Город", event.city],
      ["Даты", plan?.travelWindow ?? `${event.start} — ${event.end}`],
      ["Участников", budget.travelers],
      ["Статья", "Сумма, ₽"],
      ...rows.map((row) => [row.label, row.value]),
      ["ИТОГО", total],
      ["На 1 человека", Math.round(perPerson)],
    ];
    const csv = `\uFEFF${lines.map((line) => line.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(";")).join("\r\n")}`;
    downloadText(`budget-${event.id}.csv`, csv, "text/csv;charset=utf-8");
  }

  return (
    <main className="radar-grid min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-[1480px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-cyan-300"><Calculator className="size-5" /> Рабочая поездка</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">Собрать командировку</h1>
          </div>
          <TripWorkspaceNav active="budget" />
        </div>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_430px]">
          <div className="space-y-5">
            <div className="rounded-2xl border border-white/8 bg-[#0a1516]/92 p-5 sm:p-6">
              <label htmlFor="trip-event" className="text-sm font-semibold text-slate-200">Выставка</label>
              <Select value={budget.eventId} onValueChange={changeEvent}>
                <SelectTrigger id="trip-event" className="mt-2 min-h-12 w-full border-white/10 bg-[#071011] text-left text-slate-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-zinc-300 bg-white text-zinc-900">
                  {availableEvents.map((item) => <SelectItem key={item.id} value={item.id}>{item.shortName} · {item.city}</SelectItem>)}
                </SelectContent>
              </Select>

              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <SummaryFact icon={CalendarDays} label="Даты" value={plan?.travelWindow ?? `${event.start} — ${event.end}`} />
                <SummaryFact icon={BedDouble} label="Площадка" value={event.venue} />
                <SummaryFact icon={Users} label="Формат" value={event.category} />
                {plan && <SummaryFact icon={Clock3} label="От SVO до площадки" value={plan.journeyFromSvo} />}
              </div>
            </div>

            <div className="rounded-2xl border border-white/8 bg-[#0a1516]/92 p-5 sm:p-6">
              <h2 className="text-lg font-semibold text-white">Параметры поездки</h2>
              <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <NumberField label="Участников" value={budget.travelers} min={1} max={20} onChange={(value) => update("travelers", value)} />
                <NumberField label="Номеров" value={budget.rooms} min={1} max={20} onChange={(value) => update("rooms", value)} />
                <NumberField label="Ночей" value={budget.nights} min={1} max={30} onChange={(value) => update("nights", value)} />
                <NumberField label="Дней с суточными" value={budget.allowanceDays} min={1} max={32} onChange={(value) => update("allowanceDays", value)} />
              </div>
            </div>

            <div className="rounded-2xl border border-white/8 bg-[#0a1516]/92 p-5 sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-white">Стоимость</h2>
                <span className="text-xs text-slate-500">Все суммы в российских рублях</span>
              </div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <MoneyField label="Перелёт / человек" value={budget.flight} onChange={(value) => update("flight", value)} />
                <MoneyField label="Отель / номер / ночь" value={budget.hotel} onChange={(value) => update("hotel", value)} />
                <MoneyField label="Выставка / человек" value={budget.ticket} onChange={(value) => update("ticket", value)} />
                <MoneyField label="Транспорт / человек" value={budget.transport} onChange={(value) => update("transport", value)} />
                <MoneyField label="Суточные / день" value={budget.allowance} onChange={(value) => update("allowance", value)} />
                <MoneyField label="Документы и страховка" value={budget.documents} onChange={(value) => update("documents", value)} />
              </div>
            </div>

            {afterConfirmedVisaFreePeriod ? (
              <div className="rounded-2xl border border-amber-300/18 bg-amber-300/[0.055] p-5">
                <div className="flex gap-3"><ShieldAlert className="mt-0.5 size-5 shrink-0 text-amber-300" /><div><p className="font-semibold text-amber-100">Поездка после 14 сентября 2026 года</p><p className="mt-1 text-sm leading-6 text-slate-400">В расчёт включён редактируемый резерв на документы и страховку. До оплаты проверьте продление безвизового режима или требования к визе.</p></div></div>
              </div>
            ) : (
              <div className="rounded-2xl border border-emerald-300/18 bg-emerald-300/[0.05] p-5">
                <div className="flex gap-3"><CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-300" /><div><p className="font-semibold text-emerald-100">Даты входят в подтверждённый безвизовый период</p><p className="mt-1 text-sm leading-6 text-slate-400">Для граждан РФ с обычным загранпаспортом разрешено пребывание до 30 дней. Повторно проверьте правило непосредственно перед вылетом.</p></div></div>
              </div>
            )}
          </div>

          <aside data-print-sheet className="h-fit rounded-2xl border border-cyan-300/18 bg-[#0a1516]/96 p-5 shadow-[0_24px_80px_rgba(0,0,0,.22)] sm:p-6 xl:sticky xl:top-24">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.15em] text-cyan-300">Предварительный бюджет</p>
                <h2 className="mt-2 text-xl font-semibold text-white">{event.shortName}</h2>
                <p className="mt-1 text-sm text-slate-500">{event.city} · {budget.travelers} чел.</p>
              </div>
              <span className="grid size-10 place-items-center rounded-xl bg-cyan-300/10 text-cyan-300"><Calculator className="size-5" /></span>
            </div>

            <div className="mt-6 space-y-3">
              {rows.map(({ key, label, value, icon: Icon }) => (
                <div key={key} className="flex items-center justify-between gap-3 border-b border-white/7 pb-3 text-sm">
                  <span className="inline-flex items-center gap-2 text-slate-400"><Icon className="size-4 text-slate-600" /> {label}</span>
                  <span className="font-medium text-slate-200">{rubles.format(value)}</span>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-xl bg-cyan-300 p-5 text-[#071011]">
              <p className="text-xs font-bold uppercase tracking-[0.12em] opacity-70">Итого</p>
              <p className="mt-1 text-3xl font-black tracking-[-0.04em]">{rubles.format(total)}</p>
              <p className="mt-2 text-sm font-semibold opacity-75">{rubles.format(perPerson)} на 1 человека</p>
            </div>

            <p className="mt-4 text-xs leading-5 text-slate-600">{tripBudgetNotice}</p>

            <div className="no-print mt-5 grid grid-cols-2 gap-2">
              <Button type="button" onClick={saveDraft} variant="outline" className="border-white/10 bg-white/[0.03] text-slate-200 hover:bg-white/[0.08]">
                {saved ? <Check /> : <Save />} {saved ? "Сохранено" : "Сохранить"}
              </Button>
              <Button type="button" onClick={exportCsv} variant="outline" className="border-white/10 bg-white/[0.03] text-slate-200 hover:bg-white/[0.08]">
                <Download /> Excel / CSV
              </Button>
              <Button type="button" onClick={() => window.print()} className="col-span-2 bg-cyan-300 text-[#071011] hover:bg-cyan-200">
                <FileText /> Печать или PDF
              </Button>
            </div>

            <div className="no-print mt-5 grid gap-2 border-t border-white/7 pt-5">
              {plan && <ExternalLink href={plan.flightUrl} icon={Plane}>Проверить перелёт</ExternalLink>}
              {plan?.hotels[0] && <ExternalLink href={plan.hotels[0].bookingUrl} icon={Hotel}>Проверить отель рядом</ExternalLink>}
              {guidance && <ExternalLink href={guidance.registrationUrl} icon={Ticket}>Регистрация на выставку</ExternalLink>}
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}

function NumberField({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return <label className="text-sm text-slate-400"><span>{label}</span><Input type="number" inputMode="numeric" min={min} max={max} value={value} onChange={(event) => onChange(Math.min(max, Math.max(min, safeNumber(event.target.value, min))))} className="mt-2 h-11 border-white/10 bg-[#071011] text-white" /></label>;
}

function MoneyField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label className="text-sm text-slate-400"><span>{label}</span><div className="relative mt-2"><Input type="number" inputMode="numeric" min={0} step={500} value={value} onChange={(event) => onChange(safeNumber(event.target.value))} className="h-11 border-white/10 bg-[#071011] pr-9 text-white" /><span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-slate-600">₽</span></div></label>;
}

function SummaryFact({ icon: Icon, label, value }: { icon: typeof CalendarDays; label: string; value: string }) {
  return <div className="rounded-xl border border-white/8 bg-[#071011]/70 p-4"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-cyan-300"><Icon className="size-4" /> {label}</div><p className="mt-2 text-sm leading-5 text-slate-300">{value}</p></div>;
}

function ExternalLink({ href, icon: Icon, children }: { href: string; icon: typeof Plane; children: React.ReactNode }) {
  return <a href={href} target="_blank" rel="noopener noreferrer" className="flex min-h-10 items-center justify-between gap-3 rounded-lg px-3 text-sm font-medium text-slate-400 hover:bg-white/[0.04] hover:text-white"><span className="inline-flex items-center gap-2"><Icon className="size-4 text-cyan-300" /> {children}</span><ArrowUpRight className="size-4" /></a>;
}
