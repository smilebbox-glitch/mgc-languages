import type { Metadata } from "next";
import { EventCalendar } from "@/components/event-calendar";

export const metadata: Metadata = {
  title: "Календарь выставок — Окно в Китай",
  description: "Автомобильные выставки, автосалоны и B2B-форумы Китая с планом поездки.",
};

export default function CalendarPage() {
  return <EventCalendar />;
}
