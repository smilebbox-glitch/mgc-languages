import Link from "next/link";
import { MaintenanceBanner } from "@/components/maintenance-banner";
import {
  BriefcaseBusiness,
  ChartNoAxesCombined,
  CalendarDays,
  Newspaper,
  Radar,
  Radio,
  Sparkles,
  Settings,
  UserRound,
} from "lucide-react";

const navigation = [
  { href: "/", label: "Новости", icon: Newspaper },
  { href: "/calendar", label: "Календарь", icon: CalendarDays },
  { href: "/analysis", label: "ИИ-анализ", icon: Sparkles },
  { href: "/market", label: "Рынок", icon: ChartNoAxesCombined },
  { href: "/travel-guide", label: "Перед поездкой", icon: BriefcaseBusiness },
  { href: "/my", label: "Моё", icon: UserRound },
];

export function SiteShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#101114]/96 backdrop-blur-xl">
        <div className="mx-auto flex h-17 max-w-[1560px] items-center gap-2 px-3 sm:gap-4 sm:px-6 lg:px-8">
          <Link
            href="/"
            aria-label="Окно в Китай — главная"
            title="Окно в Китай"
            className="group flex shrink-0 items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5f84ff]"
          >
            <span className="relative grid size-11 shrink-0 place-items-center overflow-hidden bg-[#285fff] text-white sm:size-12">
              <Radar className="size-5 transition-transform duration-500 group-hover:rotate-45 sm:size-6" />
              <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-orange-400 shadow-[0_0_10px_#fb923c]" />
            </span>
          </Link>

          <nav className="ml-auto flex shrink-0 items-center gap-0.5 sm:gap-1" aria-label="Основная навигация">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex h-10 items-center gap-2 border-b-2 border-transparent px-2 text-xs font-bold uppercase tracking-[0.08em] text-zinc-400 transition-colors hover:border-[#285fff] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5f84ff] sm:px-3"
                >
                  <Icon className="size-4 text-[#6f91ff]" />
                  <span className="hidden lg:inline">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <Link
            href="/admin"
            aria-label="Администрирование пилота"
            title="Администрирование"
            className="grid size-10 shrink-0 place-items-center border border-white/10 text-zinc-500 transition-colors hover:border-[#5f84ff]/50 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5f84ff]"
          >
            <Settings className="size-4" />
          </Link>

          <div className="hidden items-center gap-2 border border-emerald-400/25 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.1em] text-emerald-300 xl:flex">
            <Radio className="size-3.5" />
            15 мин
          </div>
        </div>
      </header>
      <MaintenanceBanner />

      {children}

      <footer className="border-t border-white/8 bg-[#101114]">
        <div className="mx-auto max-w-[1560px] px-4 py-6 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-600 sm:px-6 lg:px-8">
          Окно в Китай
        </div>
      </footer>
    </div>
  );
}
