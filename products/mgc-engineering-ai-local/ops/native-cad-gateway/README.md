# Native CAD Gateway — KOMPAS-3D / T-FLEX CAD

This gateway is intentionally **outside** the Linux MGC core. KOMPAS-3D and
T-FLEX CAD native formats are processed on an approved Windows host where the
licensed CAD installation/API is available.

The bundled FastAPI gateway is a hardened process adapter. It never uses a
shell: an IT-approved converter executable is launched with an argument array.
The converter executable is the small vendor-specific component built against
KOMPAS SDK/Automation or T-FLEX Open API.

## Flow

`MGC core -> HTTPS/mTLS or protected LAN -> gateway -> vendor SDK -> STEP/PDF`

The original native file remains immutable in MGC. The returned derivative is
SHA-256 hashed, stored separately and linked by provenance.

## KOMPAS profiles

- `.m3d`, `.a3d`, `.t3d` -> STEP (STEP AP242 preferred)
- `.cdw`, `.frw` -> PDF (DXF optional)
- `.spw`, `.kdw` -> PDF/text/table derivative as approved

## T-FLEX profile

- `.grb` is polymorphic. With `target_format=auto`, the vendor wrapper inspects
  the document and emits exactly one of `converted.step`, `converted.pdf`, or
  `converted.dxf`.

## Run on Windows

1. Install the approved CAD application/API and Python runtime on an isolated
   service host, or package this adapter under the company's service standard.
2. `pip install -r requirements.txt`
3. Copy the corresponding `.env.example` values into the service environment.
4. Implement/approve the vendor wrapper executable.
5. Run `uvicorn gateway:app --host 127.0.0.1 --port 8181` behind the corporate
   reverse proxy with TLS/mTLS.
6. Register the gateway in MGC as `connector_type=cad_gateway`, declaring
   `vendor` and `extensions`.

Do not expose the gateway directly to the Internet. Do not grant it write
access to PLM/PDM source folders. Use a dedicated service account and a vendor
license that permits server-side conversion.
