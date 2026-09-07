import type { Metadata } from "next";
import { MarketDashboard } from "@/components/market-dashboard";

export const metadata: Metadata = {
  title: "Рынок России — Окно в Китай",
  description: "Продажи основных автомобильных марок в России за 2025 и 2026 годы.",
};

export default function MarketPage() {
  return <MarketDashboard />;
}
