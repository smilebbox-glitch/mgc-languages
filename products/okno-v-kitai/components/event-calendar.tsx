"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ArrowUpRight,
  BadgeInfo,
  CalendarPlus,
  Check,
  ChevronDown,
  Clock3,
  DoorOpen,
  FileCheck2,
  Hotel,
  Luggage,
  MapPin,
  Plane,
  Sparkles,
  Ticket,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FavoriteButton } from "@/components/favorite-button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { autoEvents, eventGuidance, type AutoEvent } from "@/lib/data";
import {
  eventTravelPlans,
  travelPriceNotice,
  tripDocuments,
  type EventTravelPlan,
} from "@/lib/travel";

type RangeFilter = "upcoming" | "all" | "past";

const fullDate = new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const monthDate = new Intl.DateTimeFormat("ru-RU", {
  month: "short",
  timeZone: "UTC",
});

function parseDate(value: string) {
  return new Date(`${value}T12:00:00Z`);
}

function formatRange(event: AutoEvent) {
  if (event.start === event.end) return fullDate.format(parseDate(event.start));
  const start = parseDate(event.start);
  const end = parseDate(event.end);
  const sameMonth = start.getUTCMonth() === end.getUTCMonth();
  if (sameMonth) {
    return `${start.getUTCDate()}–${fullDate.format(end)}`;
  }
  return `${fullDate.format(start)} — ${fullDate.format(end)}`;
}

function statusOf(event: AutoEvent, today: string) {
  if (event.end < today) return "past" as const;
  if (event.start <= today && event.end >= today) return "now" as const;
  return "upcoming" as const;
}

function toIcsDate(value: string, addOneDay = false) {
  const date = parseDate(value);
  if (addOneDay) date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().slice(0, 10).replaceAll("-", "");
}

function downloadIcs(event: AutoEvent) {
  const content = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Окно в Китай//RU",
    "BEGIN:VEVENT",
    `UID:${event.id}@okno-v-kitay`,
    `DTSTART;VALUE=DATE:${toIcsDate(event.start)}`,
    `DTEND;VALUE=DATE:${toIcsDate(event.end, true)}`,
    `SUMMARY:${event.name.replaceAll(",", "\\,")}`,
    `LOCATION:${event.venue.replaceAll(",", "\\,")}, ${event.city}`,
    `DESCRIPTION:${event.note.replaceAll("\n", "\\n")}\\n${event.url}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
  const url = URL.createObjectURL(new Blob([content], { type: "text/calendar;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${event.id}.ics`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function EventCalendar() {
  const [range, setRange] = useState<RangeFilter>("upcoming");
  const [category, setCategory] = useState("Все форматы");
  const today = new Date().toISOString().slice(0, 10);

  const filteredEvents = useMemo(() => {
    return [...autoEvents]
      .sort((left, right) => left.start.localeCompare(right.start))
      .filter((event) => {
        const status = statusOf(event, today);
        const matchesRange =
          range === "all" ||
          (range === "past" ? status === "past" : status !== "past");
        const matchesCategory = category === "Все форматы" || event.category === category;
        return event.country === "Китай" && matchesRange && matchesCategory;
      });
  }, [category, range, today]);

  const nextEvent = autoEvents
    .filter((event) => event.end >= today)
    .sort((left, right) => left.start.localeCompare(right.start))[0];

  return (
    <main className="radar-grid min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
        <section className="mb-6 grid overflow-hidden rounded-2xl border border-white/9 bg-[#0a1516]/92 lg:grid-cols-[minmax(0,1fr)_390px]">
          <div className="p-5 sm:p-7 lg:p-8">
            <div className="mb-3 flex items-center gap-2 text-sm text-cyan-300">
              <CalendarPlus className="size-4" />
              Проверенный календарь
            </div>
            <h1 className="text-3xl font-semibold tracking-[-0.035em] text-white sm:text-4xl">
              Автосалоны и B2B-выставки
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-400">
              Только Китай: автосалоны, компоненты, шины, спецтехника и
              коммерческий транспорт.
            </p>
          </div>

          {nextEvent && (
            <div className="border-t border-orange-400/15 bg-orange-400/[0.045] p-5 sm:p-7 lg:border-l lg:border-t-0">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-orange-300">
                <Sparkles className="size-4" /> Ближайшее событие
              </div>
              <p className="mt-4 text-xl font-semibold text-white">{nextEvent.shortName}</p>
              <p className="mt-1 text-sm text-slate-400">
                {formatRange(nextEvent)} · {nextEvent.city}
              </p>
              <a
                href={nextEvent.url}
                target="_blank"
                rel="noreferrer"
                className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-orange-300 hover:text-orange-200"
              >
                Официальный сайт <ArrowUpRight className="size-4" />
              </a>
            </div>
          )}
        </section>

        <section>
          <div className="min-w-0">
            <div className="mb-5 flex flex-col gap-3 rounded-xl border border-white/8 bg-[#0a1516]/78 p-3 md:flex-row md:items-center md:justify-between">
              <Tabs value={range} onValueChange={(value) => setRange(value as RangeFilter)}>
                <TabsList className="h-auto bg-white/5 p-1">
                  <TabsTrigger value="upcoming" className="min-h-9 px-3 data-[state=active]:bg-white/10">
                    Предстоящие
                  </TabsTrigger>
                  <TabsTrigger value="all" className="min-h-9 px-3 data-[state=active]:bg-white/10">
                    Все
                  </TabsTrigger>
                  <TabsTrigger value="past" className="min-h-9 px-3 data-[state=active]:bg-white/10">
                    Архив
                  </TabsTrigger>
                </TabsList>
              </Tabs>

              <div className="flex flex-col gap-2 sm:flex-row">
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger className="h-10 w-full border-white/10 bg-[#071011] text-slate-300 sm:w-44">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent position="popper" className="border-zinc-300 bg-white text-zinc-900">
                    <SelectItem value="Все форматы">Все форматы</SelectItem>
                    <SelectItem value="Автосалон">Автосалон</SelectItem>
                    <SelectItem value="Компоненты">Компоненты</SelectItem>
                    <SelectItem value="Коммерческий транспорт">Коммерческий транспорт</SelectItem>
                    <SelectItem value="B2B-форум">B2B-форум</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3">
              {filteredEvents.map((event) => {
                const status = statusOf(event, today);
                const guidance = eventGuidance[event.id];
                const travelPlan = eventTravelPlans[event.id];
                return (
                  <article
                    key={event.id}
                    className="group grid gap-4 rounded-2xl border border-white/8 bg-[#0a1516]/86 p-5 transition-colors hover:border-white/14 sm:grid-cols-[86px_minmax(0,1fr)_auto] sm:p-6"
                  >
                    <div className="flex h-[82px] w-[82px] shrink-0 flex-col items-center justify-center rounded-xl border border-white/8 bg-[#071011]">
                      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-cyan-300">
                        {monthDate.format(parseDate(event.start)).replace(".", "")}
                      </span>
                      <span className="mt-1 text-3xl font-semibold leading-none text-white">
                        {parseDate(event.start).getUTCDate()}
                      </span>
                      <span className="mt-1 text-[11px] text-slate-600">
                        {parseDate(event.start).getUTCFullYear()}
                      </span>
                    </div>

                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Badge
                          variant="outline"
                          className="border-cyan-400/20 bg-cyan-400/7 text-cyan-300"
                        >
                          {event.category}
                        </Badge>
                        {event.priority === "high" && (
                          <Badge
                            variant="outline"
                            className="border-orange-400/20 bg-orange-400/7 text-orange-300"
                          >
                            приоритет
                          </Badge>
                        )}
                        {status === "now" && (
                          <Badge className="bg-emerald-400 text-[#061011]">идёт сейчас</Badge>
                        )}
                        {status === "past" && (
                          <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                            <Check className="size-3.5" /> завершено
                          </span>
                        )}
                      </div>

                      <h2 className="text-lg font-semibold leading-7 text-white">{event.name}</h2>
                      <p className="mt-2 text-sm leading-6 text-slate-400">{event.note}</p>
                      {guidance && (
                        <div className="mt-5 grid gap-3 lg:grid-cols-3">
                          <EventDetail icon={BadgeInfo} label="Зачем ехать" text={guidance.whyGo} />
                          <EventDetail icon={DoorOpen} label="Как попасть" text={guidance.access} />
                          <EventDetail icon={Ticket} label="Билет на 1 человека" text={guidance.ticketPrice} />
                        </div>
                      )}
                      {travelPlan && status !== "past" && <EventTravelDetails plan={travelPlan} />}
                      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500">
                        <span className="inline-flex items-center gap-1.5">
                          <Clock3 className="size-3.5" /> {formatRange(event)}
                        </span>
                        <span className="inline-flex items-center gap-1.5">
                          <MapPin className="size-3.5" /> {event.city}, {event.venue}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-end justify-between gap-3 sm:w-48 sm:flex-col sm:items-end">
                      <span className="text-xs text-slate-600">{event.source}</span>
                      <div className="flex flex-wrap justify-end gap-2">
                        <FavoriteButton item={{itemType:"event",itemId:event.id,title:event.name,url:event.url,metadata:{city:event.city,start:event.start,end:event.end}}} className="border-white/10 bg-white/4 text-slate-300 hover:bg-white/8 hover:text-white"/>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => downloadIcs(event)}
                          aria-label={`Добавить ${event.shortName} в календарь`}
                          title="Скачать .ics"
                          className="cursor-pointer border-white/10 bg-white/4 text-slate-300 hover:bg-white/8 hover:text-white"
                        >
                          <CalendarPlus /> В календарь
                        </Button>
                        <Button
                          asChild
                          className="cursor-pointer bg-cyan-300 text-[#071011] hover:bg-cyan-200"
                        >
                          <a href={guidance?.registrationUrl ?? event.url} target="_blank" rel="noopener noreferrer" aria-label={`Регистрация на ${event.shortName}`}>
                            Регистрация <ArrowUpRight />
                          </a>
                        </Button>
                      </div>
                    </div>
                  </article>
                );
              })}

              {filteredEvents.length === 0 && (
                <div className="rounded-2xl border border-dashed border-white/12 py-20 text-center text-sm text-slate-500">
                  Для выбранных фильтров событий нет.
                </div>
              )}
            </div>
          </div>

        </section>
      </div>
    </main>
  );
}

function EventDetail({ icon: Icon, label, text }: { icon: typeof Ticket; label: string; text: string }) {
  return (
    <div className="rounded-xl border border-white/8 bg-[#071011]/70 p-4">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-cyan-300">
        <Icon className="size-4" /> {label}
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-400">{text}</p>
    </div>
  );
}

function EventTravelDetails({ plan }: { plan: EventTravelPlan }) {
  return (
    <details className="group/travel mt-5 overflow-hidden rounded-xl border border-violet-300/15 bg-violet-300/[0.035]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-violet-200 marker:hidden">
        <span className="inline-flex items-center gap-2">
          <Luggage className="size-4" /> Перелёт, отели, документы и город
        </span>
        <ChevronDown className="size-4 transition-transform group-open/travel:rotate-180" />
      </summary>

      <div className="border-t border-violet-300/10 p-4">
        <div className="grid gap-3 lg:grid-cols-2">
          <div className="rounded-xl border border-white/8 bg-[#071011]/70 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-cyan-300">
              <Plane className="size-4" /> Перелёт из Москвы
            </div>
            <p className="mt-2 text-sm font-medium text-slate-200">{plan.flightPrice}</p>
            <p className="mt-1 text-xs text-slate-500">{plan.travelWindow}</p>
            <div className="mt-3 border-t border-white/7 pt-3">
              <p className="text-xs font-semibold text-slate-300">Из Шереметьево до площадки: {plan.journeyFromSvo}</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">{plan.journeyBreakdown}</p>
            </div>
            <a
              href={plan.flightUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-300 hover:text-cyan-200"
            >
              Проверить на Aviasales <ArrowUpRight className="size-3.5" />
            </a>
          </div>

          <div className="rounded-xl border border-white/8 bg-[#071011]/70 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-violet-300">
              <Hotel className="size-4" /> Рядом с площадкой
            </div>
            <p className="mt-2 text-sm font-medium text-slate-200">{plan.stayBudget}</p>
            <div className="mt-3 space-y-2">
              {plan.hotels.map((hotel) => (
                <a
                  key={hotel.name}
                  href={hotel.bookingUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start justify-between gap-3 text-xs text-slate-400 hover:text-white"
                >
                  <span>{hotel.name} · {hotel.chineseName}</span>
                  <span className="shrink-0 text-violet-300">{hotel.nightlyPrice}</span>
                </a>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-white/8 bg-[#071011]/70 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-amber-300">
              <FileCheck2 className="size-4" /> Документы
            </div>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-slate-400">
              {tripDocuments.map((document) => (
                <li key={document} className="flex gap-2">
                  <span className="text-amber-300">•</span> {document}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-white/8 bg-[#071011]/70 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-orange-300">
              <MapPin className="size-4" /> Что посмотреть
            </div>
            <div className="mt-3 space-y-3">
              {plan.attractions.map((place) => (
                <div key={place.chineseName} className="text-xs text-slate-400">
                  <span className="font-medium text-slate-200">{place.name} · {place.chineseName}</span>
                  <span className="mt-0.5 block text-slate-600">{place.addressZh}</span>
                  <span className="mt-1 block leading-5 text-slate-500">{place.note}</span>
                  <span className="mt-1.5 flex gap-3">
                    <a href={place.wikipediaUrl} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-300 hover:text-orange-200">Wikipedia</a>
                    <a href={place.mapUrl} target="_blank" rel="noopener noreferrer" className="font-semibold text-cyan-300 hover:text-cyan-200">Карта</a>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 border-t border-white/7 pt-4 text-xs leading-5 text-slate-600 sm:flex-row sm:items-start sm:justify-between">
          <p className="max-w-3xl">{travelPriceNotice}</p>
          <Link href="/travel-guide" className="inline-flex shrink-0 items-center gap-1.5 font-semibold text-cyan-300 hover:text-cyan-200">
            Все правила <ArrowUpRight className="size-3.5" />
          </Link>
        </div>
      </div>
    </details>
  );
}
