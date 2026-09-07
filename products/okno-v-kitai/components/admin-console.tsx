"use client";

import { useEffect, useState } from "react";
import { Activity, ClipboardList, Download, RefreshCw, Save, ShieldCheck, ShieldX, Upload } from "lucide-react";
import { ReliabilityConsole } from "@/components/reliability-console";
import { ContentAdmin } from "@/components/content-admin";
import { GovernanceConsole } from "@/components/governance-console";
import { UsageAnalytics } from "@/components/usage-analytics";

const sourceLabels: Record<string, string> = {
  "fx.cbr": "ЦБ РФ — официальный курс CNY/RUB",
  "fx.banks": "Банковские курсы CNY",
  "news.telegram": "Telegram-источники автопрома",
  "news.autostat": "АВТОСТАТ RSS",
  "news.chinaPortals": "Китайские автомобильные порталы",
  "translate.google": "Перевод китайских публикаций",
  "rag.model": "Генеративный RAG / LLM endpoint",
};

type Status = {
  version: string;
  requestId: string;
  uptimeSeconds: number;
  principal: { subject: string; role: string; authenticated: boolean; mode: string };
  auth: { mode: string; proxySecretConfigured: boolean; adminTokenConfigured: boolean };
  integrations: { ragConfigured: boolean; outbound: { hosts: string[]; httpHosts: string[] } };
  operations: {
    audit: { integrity: string; hmacConfigured: boolean; maxBytes: number };
    rateLimit: { implementation: string; note: string };
    backup: { format: string; schema: number; secretsIncluded: boolean };
  };
  runtime: { updatedAt: string; updatedBy: string; sources: Record<string, boolean> };
  external: Array<{ host: string; requests: number; failures: number; lastStatus: number; lastDurationMs: number; lastSuccessAt: string; lastFailureAt: string }>;
};

type AuditRecord = {
  timestamp: string;
  eventId: string;
  requestId: string;
  actor: string;
  action: string;
  target: string;
  outcome: "success" | "failure" | "blocked";
  hash: string;
};

type AuditPayload = { records: AuditRecord[]; verified: boolean };

function fmtUptime(seconds: number) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days ? `${days}д ` : ""}${hours}ч ${minutes}м`;
}

function tokenHeaders(token: string): Record<string, string> {
  return token ? { "x-admin-token": token } : {};
}

export function AdminConsole() {
  const [status, setStatus] = useState<Status | null>(null);
  const [audit, setAudit] = useState<AuditPayload | null>(null);
  const [sources, setSources] = useState<Record<string, boolean>>({});
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(tokenValue = token) {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/admin/status", { headers: tokenHeaders(tokenValue), cache: "no-store" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setStatus(data);
      setSources(data.runtime.sources);
      if (data.principal.role === "admin") {
        const auditResponse = await fetch("/api/admin/audit?limit=30", { headers: tokenHeaders(tokenValue), cache: "no-store" });
        setAudit(auditResponse.ok ? await auditResponse.json() : null);
      } else {
        setAudit(null);
      }
    } catch (error) {
      setStatus(null);
      setAudit(null);
      setMessage(error instanceof Error ? error.message : "Не удалось получить статус.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const stored = sessionStorage.getItem("okno-admin-token") || "";
    setToken(stored);
    void load(stored);
    // Initial runtime status only. Subsequent refresh is explicit to avoid requests on each token keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function authenticate() {
    if (token) sessionStorage.setItem("okno-admin-token", token);
    else sessionStorage.removeItem("okno-admin-token");
    await load(token);
  }

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      if (token) sessionStorage.setItem("okno-admin-token", token);
      const response = await fetch("/api/admin/config", {
        method: "PUT",
        headers: { "content-type": "application/json", ...tokenHeaders(token) },
        body: JSON.stringify({ sources }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setMessage(data.unchanged ? "Изменений нет." : "Настройки сохранены и записаны в audit trail.");
      await load(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось сохранить настройки.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadBackup() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/admin/backup", { headers: tokenHeaders(token), cache: "no-store" });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const disposition = response.headers.get("content-disposition") || "";
      link.download = disposition.match(/filename="([^"]+)"/u)?.[1] || "okno-runtime-backup.json";
      link.click();
      URL.revokeObjectURL(url);
      setMessage("Backup runtime-настроек сформирован без секретов.");
      await load(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось создать backup.");
    } finally {
      setBusy(false);
    }
  }

  async function restoreBackup(file: File | null) {
    if (!file) return;
    if (file.size > 262_144) { setMessage("Backup слишком большой: максимум 256 КБ."); return; }
    setBusy(true);
    setMessage("");
    try {
      const parsed = JSON.parse(await file.text());
      const response = await fetch("/api/admin/restore", {
        method: "POST",
        headers: { "content-type": "application/json", ...tokenHeaders(token) },
        body: JSON.stringify(parsed),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setMessage("Runtime-конфигурация восстановлена; операция записана в audit trail.");
      await load(token);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось восстановить backup.");
    } finally {
      setBusy(false);
    }
  }

  const canAdmin = status?.principal.role === "admin";
  const canEdit = status?.principal.role === "admin" || status?.principal.role === "editor";

  return (
    <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
      <div className="space-y-5">
        <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-zinc-500">Runtime sources</p>
              <h2 className="mt-1 text-xl font-black text-white">Управление источниками</h2>
            </div>
            <button onClick={() => void load(token)} disabled={busy} className="inline-flex h-10 items-center gap-2 border border-white/10 px-3 text-xs font-bold uppercase tracking-[0.1em] text-zinc-300 hover:border-[#5f84ff]/60 hover:text-white disabled:opacity-50">
              <RefreshCw className={`size-4 ${busy ? "animate-spin" : ""}`} /> Обновить
            </button>
          </div>

          <div className="mt-5 space-y-2">
            {Object.entries(sources).map(([key, enabled]) => (
              <label key={key} className="flex items-center justify-between gap-4 border border-white/8 bg-black/10 px-4 py-3">
                <span>
                  <span className="block text-sm font-semibold text-zinc-200">{sourceLabels[key] || key}</span>
                  <span className="mt-0.5 block font-mono text-[11px] text-zinc-600">{key}</span>
                </span>
                <input type="checkbox" checked={enabled} disabled={!canAdmin || busy} onChange={(event) => setSources((current) => ({ ...current, [key]: event.target.checked }))} className="size-5 accent-[#285fff] disabled:opacity-40" />
              </label>
            ))}
          </div>

          {status?.auth.mode === "disabled" && (
            <div className="mt-5">
              <label className="text-xs font-bold uppercase tracking-[0.12em] text-zinc-500">Локальный admin token для пилота</label>
              <div className="mt-2 flex gap-2">
                <input value={token} type="password" autoComplete="off" onChange={(event) => setToken(event.target.value)} placeholder="ADMIN_API_TOKEN" className="h-11 min-w-0 flex-1 border border-white/10 bg-black/20 px-3 text-sm text-white outline-none focus:border-[#5f84ff]" />
                <button onClick={() => void authenticate()} disabled={busy} className="h-11 border border-white/10 px-3 text-xs font-bold uppercase tracking-[0.1em] text-zinc-300 hover:border-[#5f84ff]/60 hover:text-white disabled:opacity-50">Применить</button>
              </div>
              <p className="mt-2 text-xs leading-5 text-zinc-600">В корпоративном AUTH_MODE=proxy поле не используется: роль приходит от SSO/reverse proxy.</p>
            </div>
          )}

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button onClick={() => void save()} disabled={!canAdmin || busy} className="inline-flex h-11 items-center gap-2 bg-[#285fff] px-4 text-xs font-black uppercase tracking-[0.12em] text-white disabled:cursor-not-allowed disabled:opacity-40"><Save className="size-4" /> Сохранить</button>
            {message && <span className="text-sm text-zinc-400">{message}</span>}
          </div>
        </section>

        <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
          <div className="flex items-center gap-2"><Download className="size-5 text-[#6f91ff]" /><h2 className="text-lg font-black text-white">Backup / Restore</h2></div>
          <p className="mt-2 text-sm leading-6 text-zinc-500">Экспортируются только runtime-переключатели источников. SSO secret, API keys, admin/metrics tokens и другие env-секреты в backup не включаются.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button onClick={() => void downloadBackup()} disabled={!canAdmin || busy} className="inline-flex h-10 items-center gap-2 border border-white/10 px-3 text-xs font-bold uppercase tracking-[0.1em] text-zinc-300 hover:border-[#5f84ff]/60 disabled:opacity-40"><Download className="size-4" /> Скачать backup</button>
            <label className={`inline-flex h-10 cursor-pointer items-center gap-2 border border-white/10 px-3 text-xs font-bold uppercase tracking-[0.1em] text-zinc-300 hover:border-[#5f84ff]/60 ${!canAdmin || busy ? "pointer-events-none opacity-40" : ""}`}>
              <Upload className="size-4" /> Восстановить JSON
              <input type="file" accept="application/json,.json" className="hidden" onChange={(event) => { void restoreBackup(event.target.files?.[0] ?? null); event.currentTarget.value = ""; }} />
            </label>
          </div>
        </section>
      </div>

      <div className="space-y-5">
        <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
          <div className="flex items-center gap-2">{status?.principal.role === "admin" ? <ShieldCheck className="size-5 text-emerald-400" /> : <ShieldX className="size-5 text-amber-400" />}<h2 className="text-lg font-black text-white">RBAC / Operations</h2></div>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <dt className="text-zinc-500">Режим</dt><dd className="text-right font-semibold text-zinc-200">{status?.auth.mode || "—"}</dd>
            <dt className="text-zinc-500">Пользователь</dt><dd className="truncate text-right font-semibold text-zinc-200">{status?.principal.subject || "—"}</dd>
            <dt className="text-zinc-500">Роль</dt><dd className="text-right font-semibold uppercase text-[#8aa5ff]">{status?.principal.role || "—"}</dd>
            <dt className="text-zinc-500">Версия</dt><dd className="text-right font-mono text-zinc-300">{status?.version || "—"}</dd>
            <dt className="text-zinc-500">Uptime</dt><dd className="text-right text-zinc-300">{status ? fmtUptime(status.uptimeSeconds) : "—"}</dd>
            <dt className="text-zinc-500">Audit integrity</dt><dd className="text-right font-mono text-xs text-zinc-300">{status?.operations.audit.integrity || "—"}</dd>
            <dt className="text-zinc-500">Request ID</dt><dd className="truncate text-right font-mono text-[11px] text-zinc-500">{status?.requestId || "—"}</dd>
          </dl>
        </section>

        <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
          <div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2"><ClipboardList className="size-5 text-[#6f91ff]" /><h2 className="text-lg font-black text-white">Audit trail</h2></div>{audit && <span className={audit.verified ? "text-xs font-bold text-emerald-400" : "text-xs font-bold text-red-400"}>{audit.verified ? "CHAIN OK" : "CHAIN ERROR"}</span>}</div>
          <div className="mt-4 max-h-[330px] space-y-2 overflow-auto pr-1">
            {audit?.records.length ? [...audit.records].reverse().map((item) => (
              <div key={item.eventId} className="border-b border-white/6 pb-2 text-xs last:border-0">
                <div className="flex items-start justify-between gap-3"><span className="font-semibold text-zinc-200">{item.action}</span><span className={item.outcome === "success" ? "text-emerald-400" : item.outcome === "blocked" ? "text-amber-400" : "text-red-400"}>{item.outcome}</span></div>
                <p className="mt-1 truncate text-zinc-600">{item.actor} · {new Date(item.timestamp).toLocaleString("ru-RU")}</p>
                <p className="mt-1 truncate font-mono text-[10px] text-zinc-700">req {item.requestId}</p>
              </div>
            )) : <p className="text-sm text-zinc-500">Audit-событий пока нет или текущая роль не admin.</p>}
          </div>
        </section>

        <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
          <div className="flex items-center gap-2"><Activity className="size-5 text-[#6f91ff]" /><h2 className="text-lg font-black text-white">Внешние интеграции</h2></div>
          <div className="mt-4 space-y-2">
            {status?.external.length ? status.external.map((item) => (
              <div key={item.host} className="grid grid-cols-[1fr_auto] gap-3 border-b border-white/6 py-2 text-sm last:border-0">
                <div><p className="font-semibold text-zinc-200">{item.host}</p><p className="mt-0.5 text-xs text-zinc-600">{item.requests} запросов · {item.failures} ошибок</p></div>
                <div className="text-right"><p className={item.lastStatus >= 200 && item.lastStatus < 400 ? "text-emerald-400" : "text-amber-400"}>{item.lastStatus || "—"}</p><p className="text-xs text-zinc-600">{item.lastDurationMs} ms</p></div>
              </div>
            )) : <p className="text-sm text-zinc-500">Пока нет внешних запросов после запуска процесса.</p>}
          </div>
        </section>

        <section className="border border-white/10 bg-[#14161a] p-5 sm:p-6">
          <h2 className="text-lg font-black text-white">Outbound allow-list</h2>
          <div className="mt-3 flex flex-wrap gap-1.5">{status?.integrations.outbound.hosts.map((host) => <span key={host} className="border border-white/8 bg-black/15 px-2 py-1 font-mono text-[11px] text-zinc-500">{host}</span>)}</div>
        </section>
      </div>
      <div className="xl:col-span-2 space-y-5">
        <GovernanceConsole token={token} canAdmin={Boolean(canAdmin)} />
        <UsageAnalytics token={token} canAdmin={Boolean(canAdmin)} />
        <ReliabilityConsole token={token} />
        <ContentAdmin token={token} canEdit={Boolean(canEdit)} />
      </div>
    </div>
  );
}
