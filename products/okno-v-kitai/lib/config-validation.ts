import { governancePolicy } from "@/lib/governance";

export type ConfigCheck = { level: "pass" | "warn" | "fail"; key: string; message: string };

function secretIsWeak(value: string | undefined, defaultValue?: string) {
  const item = value?.trim() || "";
  return !item || item.length < 24 || (defaultValue ? item === defaultValue : false);
}

export function validatePilotConfiguration() {
  const checks: ConfigCheck[] = [];
  const authMode = process.env.AUTH_MODE?.trim() === "proxy" ? "proxy" : "disabled";
  checks.push({ level: "pass", key: "auth.mode", message: `AUTH_MODE=${authMode}` });
  if (authMode === "proxy") {
    checks.push(secretIsWeak(process.env.AUTH_PROXY_SECRET)
      ? { level: "fail", key: "auth.proxySecret", message: "AUTH_MODE=proxy требует AUTH_PROXY_SECRET длиной не менее 24 символов." }
      : { level: "pass", key: "auth.proxySecret", message: "Trusted proxy secret настроен." });
  } else {
    checks.push(secretIsWeak(process.env.ADMIN_API_TOKEN)
      ? { level: "warn", key: "auth.adminToken", message: "ADMIN_API_TOKEN пустой/короткий; admin mutation недоступны или защита недостаточна." }
      : { level: "pass", key: "auth.adminToken", message: "Pilot admin token настроен." });
  }
  checks.push(secretIsWeak(process.env.SCHEDULER_TOKEN, "change-me-before-pilot")
    ? { level: "fail", key: "scheduler.token", message: "SCHEDULER_TOKEN должен быть заменён на длинный случайный секрет." }
    : { level: "pass", key: "scheduler.token", message: "Scheduler token настроен." });
  checks.push(secretIsWeak(process.env.AUDIT_HMAC_KEY)
    ? { level: "warn", key: "audit.hmac", message: "AUDIT_HMAC_KEY не задан/короткий: audit chain не имеет keyed integrity." }
    : { level: "pass", key: "audit.hmac", message: "Audit HMAC key настроен." });
  checks.push(secretIsWeak(process.env.USER_DATA_HMAC_KEY, "change-me-user-data-hmac-before-pilot")
    ? { level: "fail", key: "privacy.userDataHmac", message: "USER_DATA_HMAC_KEY должен быть заменён на случайный секрет для псевдонимизации персонального контура." }
    : { level: "pass", key: "privacy.userDataHmac", message: "User-data HMAC key настроен." });
  const bind = process.env.APP_BIND_ADDRESS?.trim() || "127.0.0.1";
  checks.push(bind === "127.0.0.1"
    ? { level: "pass", key: "network.bind", message: "Приложение bind только на localhost." }
    : { level: "warn", key: "network.bind", message: `APP_BIND_ADDRESS=${bind}; требуется perimeter/reverse-proxy review.` });
  const policy = governancePolicy();
  checks.push(policy.retention.sourceHistoryDays >= 7
    ? { level: "pass", key: "retention.history", message: `Source history retention: ${policy.retention.sourceHistoryDays} дн.` }
    : { level: "warn", key: "retention.history", message: "Source history retention менее 7 дней." });
  checks.push(policy.scheduler.lockTtlSeconds > 0 && policy.scheduler.lockTtlSeconds < Number(process.env.SCHEDULER_INTERVAL_SECONDS || 300)
    ? { level: "pass", key: "scheduler.lockTtl", message: `Scheduler lock TTL ${policy.scheduler.lockTtlSeconds} сек.` }
    : { level: "warn", key: "scheduler.lockTtl", message: "Scheduler lock TTL должен быть меньше обычного интервала scheduler." });
  const failures = checks.filter((item) => item.level === "fail");
  const warnings = checks.filter((item) => item.level === "warn");
  return { valid: failures.length === 0, checks, failures: failures.length, warnings: warnings.length };
}
