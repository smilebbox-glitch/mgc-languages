import { sourceReliabilitySummary } from "@/lib/source-cache";
import { sourceSlaStatus } from "@/lib/governance";
type ExternalState = {
  requests: number;
  failures: number;
  lastStatus: number;
  lastDurationMs: number;
  lastSuccessAt: string;
  lastFailureAt: string;
};

type MetricsStore = {
  external: Map<string, ExternalState>;
  rateLimited: Map<string, number>;
  auditWrites: number;
};

const globalMetrics = globalThis as typeof globalThis & { __oknoMetrics?: MetricsStore };
const store = globalMetrics.__oknoMetrics ?? {
  external: new Map<string, ExternalState>(),
  rateLimited: new Map<string, number>(),
  auditWrites: 0,
};
globalMetrics.__oknoMetrics = store;

export function recordExternal(host: string, ok: boolean, status: number, durationMs: number) {
  const current = store.external.get(host) ?? {
    requests: 0,
    failures: 0,
    lastStatus: 0,
    lastDurationMs: 0,
    lastSuccessAt: "",
    lastFailureAt: "",
  };
  current.requests += 1;
  current.lastStatus = status;
  current.lastDurationMs = Math.round(durationMs);
  if (ok) current.lastSuccessAt = new Date().toISOString();
  else {
    current.failures += 1;
    current.lastFailureAt = new Date().toISOString();
  }
  store.external.set(host, current);
}

export function recordRateLimit(scope: string) {
  store.rateLimited.set(scope, (store.rateLimited.get(scope) ?? 0) + 1);
}

export function recordAuditWrite() {
  store.auditWrites += 1;
}

export function externalSnapshot() {
  return [...store.external.entries()].map(([host, state]) => ({ host, ...state }));
}

function metricLabel(value: string) {
  return value.replaceAll("\\", "\\\\").replaceAll('"', '\\"').replaceAll("\n", "\\n");
}

export function prometheusMetrics(sourceStates: Record<string, boolean>) {
  const memory = process.memoryUsage();
  let cacheMetrics: string[] = [];
  try {
    const snapshots = sourceReliabilitySummary(50).snapshots;
    cacheMetrics = [
      "# HELP okno_cache_state Current persistent cache state (1 for the labelled state).",
      "# TYPE okno_cache_state gauge",
      ...snapshots.map((item) => `okno_cache_state{source="${metricLabel(item.sourceKey)}",scope="${metricLabel(item.scope)}",state="${metricLabel(item.state)}"} 1`),
      "# HELP okno_cache_age_seconds Age of the persistent source snapshot.",
      "# TYPE okno_cache_age_seconds gauge",
      ...snapshots.map((item) => `okno_cache_age_seconds{source="${metricLabel(item.sourceKey)}",scope="${metricLabel(item.scope)}"} ${item.ageSeconds}`),
      "# HELP okno_cache_quality_score Last persistent source snapshot quality score (0-100).",
      "# TYPE okno_cache_quality_score gauge",
      ...snapshots.map((item) => `okno_cache_quality_score{source="${metricLabel(item.sourceKey)}",scope="${metricLabel(item.scope)}"} ${item.qualityScore}`),
    ];
  } catch { cacheMetrics = []; }
  let slaMetrics: string[] = [];
  try {
    slaMetrics = [
      "# HELP okno_source_sla_met Whether the current persistent source snapshot meets configured SLA (1=yes).",
      "# TYPE okno_source_sla_met gauge",
      ...sourceSlaStatus().map((item) => `okno_source_sla_met{source="${metricLabel(item.sourceKey)}",scope="${metricLabel(item.scope)}"} ${item.status === "MET" ? 1 : 0}`),
    ];
  } catch { slaMetrics = []; }
  const lines = [
    "# HELP okno_process_uptime_seconds Process uptime in seconds.",
    "# TYPE okno_process_uptime_seconds gauge",
    `okno_process_uptime_seconds ${process.uptime().toFixed(3)}`,
    "# HELP okno_process_resident_memory_bytes Resident memory in bytes.",
    "# TYPE okno_process_resident_memory_bytes gauge",
    `okno_process_resident_memory_bytes ${memory.rss}`,
    "# HELP okno_process_heap_used_bytes Heap used in bytes.",
    "# TYPE okno_process_heap_used_bytes gauge",
    `okno_process_heap_used_bytes ${memory.heapUsed}`,
    "# HELP okno_source_enabled Runtime source switch state.",
    "# TYPE okno_source_enabled gauge",
    ...Object.entries(sourceStates).map(([source, enabled]) => `okno_source_enabled{source="${metricLabel(source)}"} ${enabled ? 1 : 0}`),
    "# HELP okno_external_requests_total External HTTP attempts by host.",
    "# TYPE okno_external_requests_total counter",
    ...externalSnapshot().map((item) => `okno_external_requests_total{host="${metricLabel(item.host)}"} ${item.requests}`),
    "# HELP okno_external_failures_total External HTTP failures by host.",
    "# TYPE okno_external_failures_total counter",
    ...externalSnapshot().map((item) => `okno_external_failures_total{host="${metricLabel(item.host)}"} ${item.failures}`),
    "# HELP okno_external_last_duration_ms Last external HTTP duration in milliseconds.",
    "# TYPE okno_external_last_duration_ms gauge",
    ...externalSnapshot().map((item) => `okno_external_last_duration_ms{host="${metricLabel(item.host)}"} ${item.lastDurationMs}`),
    "# HELP okno_rate_limited_requests_total Requests rejected by the in-process rate limiter.",
    "# TYPE okno_rate_limited_requests_total counter",
    ...[...store.rateLimited.entries()].map(([scope, count]) => `okno_rate_limited_requests_total{scope="${metricLabel(scope)}"} ${count}`),
    "# HELP okno_audit_writes_total Audit events successfully appended during this process lifetime.",
    "# TYPE okno_audit_writes_total counter",
    `okno_audit_writes_total ${store.auditWrites}`,
    ...cacheMetrics,
    ...slaMetrics,
  ];
  return `${lines.join("\n")}\n`;
}
