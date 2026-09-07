# Native CAD Gateway Contract v3.4

## Purpose

Native proprietary CAD is preserved as immutable source evidence. A separately licensed, internal gateway creates a neutral derivative that the MGC Linux/Docker core can process deterministically.

Built-in v3.4 vendor profiles include КОМПАС-3D and T-FLEX CAD. The contract remains extensible to CATIA/NX/Creo/JT/SOLIDWORKS gateways.

## Health

```text
GET /health
X-API-Key: <gateway-secret>
```

Expected: HTTP 200.

## Capabilities

```text
GET /capabilities
X-API-Key: <gateway-secret>
```

Example KOMPAS response:

```json
{
  "vendor": "kompas",
  "product": "КОМПАС-3D",
  "formats": [".m3d", ".a3d", ".t3d", ".cdw", ".frw", ".spw", ".kdw"],
  "targets": ["step", "pdf", "dxf"],
  "supports_auto_target": true,
  "sdk": "KOMPAS SDK/Automation",
  "sdk_version": "approved-version",
  "gateway_build": "company-build-id"
}
```

Example T-FLEX response:

```json
{
  "vendor": "tflex",
  "product": "T-FLEX CAD",
  "formats": [".grb"],
  "targets": ["step", "pdf", "dxf"],
  "supports_auto_target": true,
  "sdk": "T-FLEX Open API",
  "sdk_version": "approved-version",
  "gateway_build": "company-build-id"
}
```

## Convert

```text
POST /convert
Content-Type: multipart/form-data
X-API-Key: <gateway-secret>
```

Fields:
- `file`: native source;
- `target_format`: `auto`, `step`, `pdf`, `dxf`, or another explicitly configured target.

Successful response headers:

- `X-CAD-Vendor`;
- `X-CAD-SDK`;
- `X-CAD-SDK-Version`;
- `X-CAD-Gateway-Build`;
- `X-CAD-Target-Format` — mandatory when `auto` was requested.

The MGC core computes SHA-256 itself, stores the derivative under a new immutable path, and records source -> derivative provenance. A derivative never overwrites the native document.

## Secure reference implementation

`ops/native-cad-gateway/gateway.py` is a process-adapter for an approved vendor wrapper executable.

Security defaults:

- API key required unless explicitly disabled for a lab;
- filename normalized to basename;
- extension allowlist;
- target allowlist;
- maximum input size;
- converter timeout;
- `subprocess.run([...], shell=False)`;
- gateway API key removed from converter child environment;
- vendor stdout/stderr not returned to callers;
- isolated temporary directory per job;
- temporary source/derivative cleanup;
- exact SDK version and gateway build returned for provenance.

## Production requirements

- use only vendor-supported/licensed server automation;
- isolate gateway in a dedicated Windows service account/security zone;
- TLS/mTLS at the service boundary in addition to the API key;
- allow network access only from MGC API/worker nodes and required license servers;
- use antivirus/content scanning according to company policy;
- configure explicit upload limits and timeouts;
- record vendor application/SDK/build/license configuration;
- do not use tessellated visualization as authoritative dimensional metrology;
- validate derivative fidelity on a golden set before enabling bulk ingestion.
