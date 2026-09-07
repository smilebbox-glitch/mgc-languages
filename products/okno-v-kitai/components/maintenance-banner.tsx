"use client";

import { useEffect, useState } from "react";
import { Wrench } from "lucide-react";

type Session = { maintenance?: { enabled: boolean; message: string } };

export function MaintenanceBanner() {
  const [maintenance, setMaintenance] = useState<Session["maintenance"]>(undefined);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await fetch("/api/session", { cache: "no-store" });
        if (!response.ok) return;
        const data = await response.json() as Session;
        if (active) setMaintenance(data.maintenance);
      } catch { /* non-critical banner */ }
    }
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  if (!maintenance?.enabled) return null;
  return <div className="border-b border-amber-400/20 bg-amber-400/10 px-4 py-2 text-center text-xs font-semibold text-amber-200"><span className="inline-flex items-center gap-2"><Wrench className="size-3.5" />{maintenance.message}</span></div>;
}
