import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";

const lock = JSON.parse(await readFile("package-lock.json", "utf8"));
const pkg = JSON.parse(await readFile("package.json", "utf8"));
const components = [];

for (const [path, meta] of Object.entries(lock.packages ?? {})) {
  if (!path.startsWith("node_modules/") || !meta?.version) continue;
  const name = path.replace(/^node_modules\//u, "");
  const version = String(meta.version);
  const ref = `pkg:npm/${encodeURIComponent(name).replaceAll("%2F", "/")}@${encodeURIComponent(version)}`;
  const component = {
    type: "library",
    "bom-ref": ref,
    name,
    version,
    purl: ref,
    scope: meta.dev ? "optional" : "required",
    properties: [
      { name: "okno:lockfilePath", value: path },
      ...(meta.resolved ? [{ name: "okno:resolved", value: String(meta.resolved) }] : []),
    ],
  };
  if (typeof meta.integrity === "string" && meta.integrity.startsWith("sha512-")) {
    try {
      component.hashes = [{ alg: "SHA-512", content: Buffer.from(meta.integrity.slice(7), "base64").toString("hex") }];
    } catch {
      // Keep component without hash if integrity is malformed.
    }
  }
  components.push(component);
}

components.sort((a, b) => `${a.name}@${a.version}`.localeCompare(`${b.name}@${b.version}`));
const serialSeed = createHash("sha256").update(JSON.stringify(lock)).digest("hex").slice(0, 32);
const bom = {
  bomFormat: "CycloneDX",
  specVersion: "1.5",
  serialNumber: `urn:uuid:${serialSeed.slice(0, 8)}-${serialSeed.slice(8, 12)}-4${serialSeed.slice(13, 16)}-8${serialSeed.slice(17, 20)}-${serialSeed.slice(20, 32)}`,
  version: 1,
  metadata: {
    timestamp: new Date().toISOString(),
    component: { type: "application", name: pkg.name, version: pkg.version },
    tools: { components: [{ type: "application", name: "okno-offline-sbom-generator", version: "1.0" }] },
  },
  components,
};

const shortVersion = String(pkg.version).replace(/-pilot$/u, "");
const output = process.env.SBOM_OUTPUT || `SBOM_v${shortVersion}.cdx.json`;
await writeFile(output, `${JSON.stringify(bom, null, 2)}\n`);
console.log(`SBOM written: ${output} (${components.length} components)`);
