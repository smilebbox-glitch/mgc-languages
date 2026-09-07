import type { Metadata } from "next";
import { TripPlanner } from "@/components/trip-planner";

export const metadata: Metadata = {
  title: "Расчёт командировки — Окно в Китай",
  description: "Интерактивный бюджет поездки на автомобильную выставку в Китае.",
};

export default function TripPlannerPage() {
  return <TripPlanner />;
}
