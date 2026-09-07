import type { Metadata } from "next";
import { TravelGuide } from "@/components/travel-guide";

export const metadata: Metadata = {
  title: "Перед поездкой — Окно в Китай",
  description: "Виза, документы, приложения, оплата, багаж и культурные правила для деловой поездки в Китай.",
};

export default function TravelGuidePage() {
  return <TravelGuide />;
}
