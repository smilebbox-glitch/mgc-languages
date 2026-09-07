import { mkdir, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const mode = process.env.ACCEPTANCE_MODE === "target" ? "target" : "package";
const online = process.env.ONLINE_ACCEPTANCE === "YES";
const steps = [
  ["Security preflight", "node", ["scripts/pilot-security-preflight.mjs"], true],
  ["Operations preflight", "node", ["scripts/pilot-operations-preflight.mjs"], true],
  ["Reliability preflight", "node", ["scripts/pilot-reliability-preflight.mjs"], true],
  ["Governance preflight", "node", ["scripts/pilot-governance-preflight.mjs"], true],
  ["Business operations preflight", "node", ["scripts/pilot-business-preflight.mjs"], true],
  ["One-click deployment preflight", "node", ["scripts/pilot-oneclick-preflight.mjs"], true],
  ["TypeScript syntax", "npm", ["run", "pilot:syntax", "--silent"], true],
  ["SBOM generation", "node", ["scripts/generate-sbom.mjs"], true],
  ["Targeted pilot tests", "node", ["--test", "tests/pilot-operations.test.mjs", "tests/pilot-reliability.test.mjs", "tests/pilot-governance.test.mjs", "tests/pilot-business.test.mjs", "tests/pilot-oneclick.test.mjs"], true],
];
if (mode === "target") {
  steps.push(["Host preflight", "bash", ["scripts/host-preflight.sh"], true]);
  steps.push(["Compose config", "docker", ["compose", "config", "--quiet"], true]);
  steps.push(["Container smoke", "bash", ["scripts/container-smoke.sh"], true]);
}
if (online) steps.push(["Dependency vulnerability audit", "npm", ["audit", "--audit-level=high", "--omit=dev"], true]);
else steps.push(["Dependency vulnerability audit", "bash", ["-lc", "echo 'PENDING: set ONLINE_ACCEPTANCE=YES where registry/advisory network access is available'"], false]);

const results = [];
for (const [name, command, args, required] of steps) {
  const started = Date.now();
  const run = spawnSync(command, args, { encoding: "utf8", env: process.env, maxBuffer: 8 * 1024 * 1024 });
  const ok = run.status === 0;
  results.push({ name, required, ok, exitCode: run.status ?? -1, durationMs: Date.now() - started, stdout: (run.stdout || "").trim().slice(-6000), stderr: (run.stderr || "").trim().slice(-6000) });
  console.log(`${required ? (ok ? "PASS" : "FAIL") : "PENDING"}  ${name}`);
}

const pkg = JSON.parse(readFileSync("package.json", "utf8"));
const shortVersion = String(pkg.version).replace(/-pilot$/u, "");
const sbom = JSON.parse(readFileSync(`SBOM_v${shortVersion}.cdx.json`, "utf8"));
const createdAt = new Date().toISOString();
const failed = results.filter((item) => item.required && !item.ok);
const status = failed.length ? "FAIL" : mode === "target" && online ? "ACCEPT" : "CONDITIONAL";
const payload = { format: "okno-v-kitai-it-acceptance", schema: 1, createdAt, mode, online, appVersion: pkg.version, status, sbomComponents: Array.isArray(sbom.components) ? sbom.components.length : 0, results };
const stamp = createdAt.replace(/[:.]/g, "-");
await mkdir("acceptance", { recursive: true });
const jsonPath = `acceptance/IT_ACCEPTANCE_REPORT_${stamp}.json`;
const mdPath = `acceptance/IT_ACCEPTANCE_REPORT_${stamp}.md`;
await writeFile(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, { mode: 0o600 });
const rows = results.map((item) => `| ${item.name} | ${item.required ? (item.ok ? "PASS" : "FAIL") : "PENDING"} | ${item.durationMs} ms |`).join("\n");
const notes = results.filter((item) => !item.ok || !item.required).map((item) => `### ${item.name}\n\n\`\`\`text\n${item.stderr || item.stdout || "No output"}\n\`\`\``).join("\n\n");
const markdown = `# IT Acceptance Report — Окно в Китай\n\n- Version: **${pkg.version}**\n- Mode: **${mode}**\n- Status: **${status}**\n- Generated: ${createdAt}\n- SBOM components: ${payload.sbomComponents}\n\n| Gate | Status | Duration |\n|---|---|---:|\n${rows}\n\n## Interpretation\n\n- **ACCEPT**: target runtime + online dependency audit passed.\n- **CONDITIONAL**: package gates passed, but target runtime and/or online CVE gate still require execution in corporate infrastructure.\n- **FAIL**: at least one required gate failed.\n\n${notes}\n`;
await writeFile(mdPath, markdown, { mode: 0o600 });
const digest = createHash("sha256").update(JSON.stringify(payload)).digest("hex");
console.log(`Report: ${mdPath}`);
console.log(`JSON: ${jsonPath}`);
console.log(`Report payload SHA-256: ${digest}`);
if (failed.length) process.exit(1);
