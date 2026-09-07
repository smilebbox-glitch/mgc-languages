import Link from "next/link";
import { Calculator, ShieldCheck, UserRound } from "lucide-react";

const items = [
  { id: "budget", href: "/trip-planner", label: "Расчёт", icon: Calculator },
  { id: "rules", href: "/travel-guide", label: "Правила", icon: ShieldCheck },
  { id: "my", href: "/my", label: "Моя поездка", icon: UserRound },
] as const;

export function TripWorkspaceNav({ active }: { active: (typeof items)[number]["id"] }) {
  return (
    <nav className="flex max-w-full gap-1 overflow-x-auto rounded-xl border border-white/8 bg-[#0a1516]/92 p-1" aria-label="Разделы командировки">
      {items.map(({ id, href, label, icon: Icon }) => (
        <Link
          key={id}
          href={href}
          aria-current={active === id ? "page" : undefined}
          className={`inline-flex min-h-11 flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 text-sm font-semibold transition-colors sm:flex-none ${
            active === id
              ? "bg-cyan-300 text-[#071011]"
              : "text-slate-400 hover:bg-white/[0.05] hover:text-white"
          }`}
        >
          <Icon className="size-4" /> {label}
        </Link>
      ))}
    </nav>
  );
}
