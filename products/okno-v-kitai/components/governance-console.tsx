"use client";

import { useEffect, useState } from "react";
import { DatabaseZap, RefreshCw, ShieldCheck, Wrench } from "lucide-react";

function tokenHeaders(token: string): Record<string, string> { return token ? { "x-admin-token": token } : {}; }

type GovernanceData = {
  maintenance: { enabled: boolean; message: string };
  migrations: { current: number; latest: number; pending: number; applied: Array<{ version: number; name: string; appliedAt: string }> };
  policy: { retention: { sourceHistoryDays: number; sourceHistoryMaxRows: number; expiredSnapshotDays: number; archivedContentDays: number }; scheduler: { lockTtlSeconds: number } };
  locks: Array<{ lockName: string; owner: string; expiresAt: string; active: boolean }>;
  sla: Array<{ sourceKey: string; scope: string; status: string; ageSeconds: number | null; qualityScore: number | null; maxAgeSeconds: number; minQuality: number }>;
  validation: { valid: boolean; failures: number; warnings: number; checks: Array<{ level: "pass" | "warn" | "fail"; key: string; message: string }> };
};

export function GovernanceConsole({ token, canAdmin }: { token: string; canAdmin: boolean }) {
  const [data, setData] = useState<GovernanceData | null>(null);
  const [maintenance, setMaintenance] = useState({ enabled: false, message: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function load() {
    setBusy(true); setMessage("");
    try {
      const r = await fetch("/api/admin/governance", { headers: tokenHeaders(token), cache: "no-store" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
      setData(d); setMaintenance(d.maintenance);
    } catch (e) { setMessage(e instanceof Error ? e.message : "Не удалось загрузить governance status."); }
    finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, [token]);
  async function saveMaintenance() {
    setBusy(true); setMessage("");
    try {
      const r = await fetch("/api/admin/governance", { method: "PUT", headers: { "content-type": "application/json", ...tokenHeaders(token) }, body: JSON.stringify({ maintenance }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
      setMessage(d.maintenance.enabled ? "Maintenance mode включён." : "Maintenance mode выключен.");
      await load();
    } catch (e) { setMessage(e instanceof Error ? e.message : "Не удалось изменить maintenance mode."); }
    finally { setBusy(false); }
  }
  return <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
    <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2"><ShieldCheck className="size-5 text-[#6f91ff]"/><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-zinc-500">Governance</p><h2 className="text-lg font-black text-white">Политики и готовность</h2></div></div><button onClick={()=>void load()} disabled={busy} className="border border-white/10 p-2 text-zinc-400"><RefreshCw className={`size-4 ${busy?"animate-spin":""}`}/></button></div>
    {data && <>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="border border-white/8 bg-black/10 p-3"><p className="text-xs text-zinc-500">DB migrations</p><p className={data.migrations.pending===0?"mt-1 font-black text-emerald-400":"mt-1 font-black text-red-400"}>v{data.migrations.current} / v{data.migrations.latest}</p></div>
        <div className="border border-white/8 bg-black/10 p-3"><p className="text-xs text-zinc-500">Config validation</p><p className={data.validation.valid?"mt-1 font-black text-emerald-400":"mt-1 font-black text-red-400"}>{data.validation.valid?"VALID":"BLOCKED"}</p><p className="mt-1 text-[11px] text-zinc-600">{data.validation.warnings} warning(s)</p></div>
        <div className="border border-white/8 bg-black/10 p-3"><p className="text-xs text-zinc-500">Scheduler lock</p><p className="mt-1 font-black text-zinc-200">{data.locks.some(x=>x.active)?"ACTIVE":"FREE"}</p><p className="mt-1 text-[11px] text-zinc-600">TTL {data.policy.scheduler.lockTtlSeconds} сек.</p></div>
      </div>
      <div className="mt-5 border border-white/8 bg-black/10 p-4"><div className="flex items-center gap-2"><Wrench className="size-4 text-amber-300"/><p className="font-bold text-zinc-200">Maintenance mode</p></div><label className="mt-3 flex items-center gap-3 text-sm text-zinc-300"><input type="checkbox" checked={maintenance.enabled} disabled={!canAdmin||busy} onChange={e=>setMaintenance(v=>({...v,enabled:e.target.checked}))} className="size-5 accent-[#285fff]"/>Включить технические работы</label><input value={maintenance.message} disabled={!canAdmin||busy} onChange={e=>setMaintenance(v=>({...v,message:e.target.value}))} className="mt-3 h-10 w-full border border-white/10 bg-black/20 px-3 text-sm text-white outline-none"/><button onClick={()=>void saveMaintenance()} disabled={!canAdmin||busy} className="mt-3 h-9 bg-[#285fff] px-3 text-xs font-black uppercase tracking-[0.1em] text-white disabled:opacity-40">Сохранить режим</button></div>
      <div className="mt-5"><div className="flex items-center gap-2"><DatabaseZap className="size-4 text-[#6f91ff]"/><p className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-500">Source SLA</p></div><div className="mt-2 space-y-2">{data.sla.map((item,index)=><div key={`${item.sourceKey}:${item.scope}:${index}`} className="grid gap-1 border-b border-white/6 py-2 text-xs md:grid-cols-[1fr_90px_180px]"><span className="text-zinc-300">{item.sourceKey}{item.scope?` · ${item.scope}`:""}</span><span className={item.status==="MET"?"font-bold text-emerald-400":item.status==="NO_DATA"?"font-bold text-zinc-500":"font-bold text-red-400"}>{item.status}</span><span className="text-zinc-600">age {item.ageSeconds??"—"}/{item.maxAgeSeconds}s · Q {item.qualityScore??"—"}/{item.minQuality}</span></div>)}</div></div>
      <details className="mt-5"><summary className="cursor-pointer text-xs font-bold uppercase tracking-[0.12em] text-zinc-500">Configuration checks</summary><div className="mt-3 space-y-2">{data.validation.checks.map(item=><div key={item.key} className="flex gap-3 text-xs"><span className={item.level==="pass"?"w-12 font-bold text-emerald-400":item.level==="warn"?"w-12 font-bold text-amber-400":"w-12 font-bold text-red-400"}>{item.level.toUpperCase()}</span><span className="text-zinc-400">{item.message}</span></div>)}</div></details>
    </>}
    {message&&<p className="mt-4 text-xs text-zinc-500">{message}</p>}
  </section>;
}
