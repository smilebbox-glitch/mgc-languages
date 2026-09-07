const base = process.env.SCHEDULER_APP_URL?.trim() || "http://china-auto-radar:3000";
const token = process.env.SCHEDULER_TOKEN?.trim() || "";
const intervalSeconds = Math.max(60, Number(process.env.SCHEDULER_INTERVAL_SECONDS || 300));
if (!token) {
  console.error(JSON.stringify({ level: "error", event: "scheduler_missing_token" }));
  process.exit(1);
}

async function run() {
  const started = Date.now();
  try {
    const response = await fetch(`${base}/api/internal/refresh`, { method: "POST", headers: { "x-scheduler-token": token }, signal: AbortSignal.timeout(60_000) });
    const body = await response.text();
    console.log(JSON.stringify({ timestamp: new Date().toISOString(), level: response.ok ? "info" : "warn", event: "scheduler_tick", status: response.status, durationMs: Date.now() - started, response: body.slice(0, 2000) }));
  } catch (error) {
    console.error(JSON.stringify({ timestamp: new Date().toISOString(), level: "error", event: "scheduler_tick_failed", durationMs: Date.now() - started, error: error instanceof Error ? error.message : "unknown" }));
  }
}

await new Promise((resolve) => setTimeout(resolve, 5_000));
await run();
setInterval(() => { void run(); }, intervalSeconds * 1000);
