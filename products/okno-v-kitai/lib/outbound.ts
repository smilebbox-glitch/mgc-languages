import { logEvent, logSecurityEvent } from "@/lib/logger";
import { recordExternal } from "@/lib/metrics";

const defaultHosts = [
  "www.cbr.ru",
  "bankiros.ru",
  "t.me",
  "www.autostat.ru",
  "www.sxqc.com",
  "auto.people.com.cn",
  "www.xinhuanet.com",
  "www.news.cn",
  "auto.news.cn",
  "auto.cctv.com",
  "www.autohome.com.cn",
  "www.yiche.com",
  "www.pcauto.com.cn",
  "translate.googleapis.com",
  "host.docker.internal",
];

function configuredHosts() {
  const configured = process.env.OUTBOUND_ALLOWLIST?.split(",").map((item) => item.trim()).filter(Boolean) ?? [];
  const rag = process.env.RAG_API_URL?.trim();
  let ragHost = "";
  try { if (rag) ragHost = new URL(rag).hostname; } catch { ragHost = ""; }
  return new Set([...defaultHosts, ...configured, ragHost].filter(Boolean).map((host) => host.toLocaleLowerCase("en-US")));
}

function httpHosts() {
  return new Set(
    (process.env.OUTBOUND_ALLOW_HTTP_HOSTS || "host.docker.internal")
      .split(",")
      .map((item) => item.trim().toLocaleLowerCase("en-US"))
      .filter(Boolean),
  );
}

export function outboundPolicy() {
  return {
    hosts: [...configuredHosts()].sort(),
    httpHosts: [...httpHosts()].sort(),
  };
}

export function assertOutboundUrl(input: string | URL) {
  const url = input instanceof URL ? new URL(input) : new URL(input);
  const host = url.hostname.toLocaleLowerCase("en-US");
  if (!configuredHosts().has(host)) {
    logSecurityEvent("outbound_policy_blocked", { outcome: "blocked", host, reason: "host_not_allowlisted" });
    throw new Error(`Outbound host is not allow-listed: ${host}`);
  }
  if (url.protocol !== "https:" && !(url.protocol === "http:" && httpHosts().has(host))) {
    logSecurityEvent("outbound_policy_blocked", { outcome: "blocked", host, protocol: url.protocol, reason: "protocol_not_allowed" });
    throw new Error(`Outbound protocol is blocked for ${host}: ${url.protocol}`);
  }
  if (url.username || url.password) {
    logSecurityEvent("outbound_policy_blocked", { outcome: "blocked", host, reason: "embedded_credentials" });
    throw new Error("Credentials in outbound URL are blocked");
  }
  return url;
}

export async function safeFetch(input: string | URL, init: RequestInit = {}) {
  let url = assertOutboundUrl(input);
  const method = (init.method || "GET").toUpperCase();
  for (let redirect = 0; redirect <= 4; redirect += 1) {
    const started = performance.now();
    try {
      const response = await fetch(url, { ...init, redirect: "manual" });
      recordExternal(url.hostname, response.status < 400, response.status, performance.now() - started);
      const location = response.headers.get("location");
      if (response.status >= 300 && response.status < 400 && location) {
        if (redirect === 4) throw new Error("Too many outbound redirects");
        if (method !== "GET" && method !== "HEAD") {
          throw new Error(`Redirect blocked for non-idempotent outbound ${method}`);
        }
        const next = assertOutboundUrl(new URL(location, url));
        logEvent("info", "outbound_redirect", { fromHost: url.hostname, toHost: next.hostname, status: response.status });
        url = next;
        continue;
      }
      if (!response.ok) logEvent("warn", "outbound_http_non_2xx", { host: url.hostname, status: response.status });
      return response;
    } catch (error) {
      recordExternal(url.hostname, false, 0, performance.now() - started);
      logEvent("warn", "outbound_http_failed", { host: url.hostname, error });
      throw error;
    }
  }
  throw new Error("Outbound redirect loop");
}
