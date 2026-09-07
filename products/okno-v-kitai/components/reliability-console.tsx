"use client";

import { useEffect, useState } from "react";
import { Database, RefreshCw, TimerReset } from "lucide-react";

type ReliabilityPayload = {
  serviceLevel: "HEALTHY" | "STALE" | "DEGRADED" | "WARMING_UP";
  database: { available: boolean; path: string; snapshots: number; contentItems: number; error?: string };
  scheduler: { configured: boolean; intervalSeconds: number };
  content: Record<string, number>;
  reliability: {
    sources: Array<{ sourceKey: string; scope: string; runs: number; avgQuality: number; successfulRuns: number; lastRun: string; lastSuccess: string }>;
    snapshots: Array<{ cacheKey: string; sourceKey: string; scope: string; fetchedAt: string; status: string; qualityScore: number; itemCount: number; state: "fresh" | "stale" | "expired"; ageSeconds: number; error: string }>;
  };
};

function tokenHeaders(token: string): Record<string, string> { return token ? { "x-admin-token": token } : {}; }
function age(value: number) { if (value < 60) return `${value}с`; if (value < 3600) return `${Math.floor(value / 60)}м`; return `${Math.floor(value / 3600)}ч`; }

export function ReliabilityConsole({ token }: { token: string }) {
  const [data, setData] = useState<ReliabilityPayload | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/admin/reliability", { headers: tokenHeaders(token), cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      setData(payload);
    } catch (e) { setError(e instanceof Error ? e.message : "Не удалось получить reliability status."); }
    finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, [token]);

  return <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-2"><Database className="size-5 text-[#6f91ff]"/><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-zinc-500">Reliability</p><h2 className="text-lg font-black text-white">Хранилище и свежесть данных</h2></div></div>
      <button onClick={() => void load()} disabled={busy} className="inline-flex h-9 items-center gap-2 border border-white/10 px-3 text-xs font-bold text-zinc-300 disabled:opacity-50"><RefreshCw className={`size-4 ${busy ? "animate-spin" : ""}`}/> Обновить</button>
    </div>
    {error && <p className="mt-4 text-sm text-amber-300">{error}</p>}
    {data && <>
      <div className="mt-4 flex items-center justify-between border border-white/8 bg-black/10 p-3"><span className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-500">Overall data state</span><span className={data.serviceLevel === "HEALTHY" ? "font-black text-emerald-400" : data.serviceLevel === "WARMING_UP" ? "font-black text-zinc-400" : data.serviceLevel === "STALE" ? "font-black text-amber-400" : "font-black text-red-400"}>{data.serviceLevel}</span></div>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="border border-white/8 bg-black/10 p-3"><p className="text-xs text-zinc-500">SQLite</p><p className={data.database.available ? "mt-1 font-semibold text-emerald-400" : "mt-1 font-semibold text-red-400"}>{data.database.available ? "READY" : "ERROR"}</p><p className="mt-1 truncate font-mono text-[10px] text-zinc-600">{data.database.path}</p></div>
        <div className="border border-white/8 bg-black/10 p-3"><p className="text-xs text-zinc-500">Snapshots</p><p className="mt-1 text-xl font-black text-white">{data.database.snapshots}</p><p className="mt-1 text-[11px] text-zinc-600">persistent cache</p></div>
        <div className="border border-white/8 bg-black/10 p-3"><p className="text-xs text-zinc-500">Scheduler</p><p className={data.scheduler.configured ? "mt-1 font-semibold text-emerald-400" : "mt-1 font-semibold text-amber-400"}>{data.scheduler.configured ? "CONFIGURED" : "TOKEN MISSING"}</p><p className="mt-1 text-[11px] text-zinc-600">каждые {data.scheduler.intervalSeconds} сек.</p></div>
      </div>
      <div className="mt-5 space-y-2">
        {data.reliability.snapshots.length ? data.reliability.snapshots.map((item) => <div key={item.cacheKey} className="grid gap-2 border-b border-white/6 py-3 text-xs md:grid-cols-[1.5fr_90px_90px_90px] md:items-center">
          <div><p className="font-semibold text-zinc-200">{item.sourceKey}{item.scope ? ` · ${item.scope}` : ""}</p><p className="mt-1 truncate font-mono text-[10px] text-zinc-600">{item.cacheKey}</p></div>
          <span className={item.state === "fresh" ? "font-bold text-emerald-400" : item.state === "stale" ? "font-bold text-amber-400" : "font-bold text-red-400"}>{item.state.toUpperCase()}</span>
          <span className="text-zinc-400">Q {item.qualityScore}/100</span>
          <span className="inline-flex items-center gap-1 text-zinc-500"><TimerReset className="size-3"/>{age(item.ageSeconds)}</span>
        </div>) : <p className="text-sm text-zinc-500">Snapshots появятся после первого успешного обновления источников.</p>}
      </div>
      <div className="mt-5 grid gap-2 sm:grid-cols-2">
        {data.reliability.sources.slice(0, 12).map((item) => <div key={`${item.sourceKey}:${item.scope}`} className="border border-white/6 bg-black/10 p-3 text-xs"><div className="flex justify-between gap-3"><span className="truncate font-semibold text-zinc-300">{item.sourceKey}</span><span className={item.avgQuality >= 80 ? "text-emerald-400" : item.avgQuality >= 50 ? "text-amber-400" : "text-red-400"}>{item.avgQuality}/100</span></div><p className="mt-1 text-zinc-600">{item.successfulRuns}/{item.runs} успешных запусков</p></div>)}
      </div>
    </>}
  </section>;
}
