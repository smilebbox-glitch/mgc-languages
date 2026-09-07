# КОМПАС-3D и T-FLEX CAD — локальная интеграция v3.4

## Зачем отдельный gateway

MGC Engineering AI работает в Linux/Docker, а нативные форматы КОМПАС-3D и T-FLEX требуют установленного и лицензированного ПО/SDK производителя. Поэтому исходный файл никогда не «разбирается» сторонней библиотекой внутри основного контейнера.

Архитектура:

```text
Engineer -> MGC Engineering AI
              |
              +-- original native file: immutable + SHA-256
              |
              +-- internal CAD Gateway (Windows, licensed CAD/SDK)
                        |
                        +-- KOMPAS SDK / Automation
                        +-- T-FLEX Open API
                        |
                        +-- STEP/PDF/DXF derivative
              |
              +-- deterministic STEP/PDF/DXF analysis
              +-- RAG / Drawing<->3D / revision / similarity
```

## КОМПАС-3D

Recognized native files:

| Extension | Meaning | Default derivative |
|---|---|---|
| `.m3d` | detail / 3D model | STEP |
| `.a3d` | assembly | STEP |
| `.t3d` | technological assembly | STEP |
| `.cdw` | drawing | PDF, alternate DXF |
| `.frw` | fragment | PDF, alternate DXF |
| `.spw` | specification | PDF, alternate XLSX/CSV |
| `.kdw` | text document | PDF, alternate TXT |

STEP AP242 is preferred where the installed KOMPAS version and corporate export profile preserve the required semantic content. The MGC core still treats the resulting STEP as a derivative, not as a replacement for the native source.

## T-FLEX CAD

Recognized native file:

| Extension | Meaning | Default derivative |
|---|---|---|
| `.grb` | T-FLEX document; may contain 2D, 3D, or both | `auto` -> STEP/PDF/DXF |

Because GRB is polymorphic, the Windows-side T-FLEX wrapper decides whether the authoritative analysis derivative should be STEP (3D-first), PDF (drawing-first) or DXF (2D vector workflow). It must return the actual format in `X-CAD-Target-Format`.

## Gateway deployment

Use `ops/native-cad-gateway/` on a dedicated Windows host/VM with the licensed CAD application/SDK.

1. Create a dedicated service account with no interactive/admin rights unless the vendor API explicitly requires them.
2. Install the approved KOMPAS/T-FLEX version and license components.
3. Implement an IT-reviewed wrapper executable around the official vendor API.
4. Configure the corresponding `.env.example` file.
5. Generate a long random `CAD_GATEWAY_API_KEY`.
6. Put the gateway behind corporate TLS or mTLS; do not expose it to the Internet.
7. Register the gateway in MGC Integrations with its vendor and extension allowlist.
8. Test with a small golden set before bulk indexing.

The reference gateway launches the converter using an argument array with `shell=False`, enforces extension/size/timeout limits, isolates each job in a temporary directory and removes temporary files after processing. Vendor stdout/stderr is not returned to callers.

## User workflow

For a normal engineer the process is intentionally one-click:

1. upload an M3D/A3D/T3D/CDW/FRW/SPW/KDW/GRB file;
2. MGC identifies the CAD vendor and document kind;
3. press **Подготовить для анализа**;
4. MGC chooses the correct approved gateway and target automatically;
5. the original file remains unchanged;
6. a derivative receives its own SHA-256 and provenance link;
7. STEP/PDF/DXF is processed by the existing Engineering Vision/CAD pipeline.

## Production acceptance set

Use at least:

- one simple part;
- one complex part;
- one assembly;
- one drawing with dimensions/GD&T;
- one specification/BOM example;
- two verified revisions;
- one corrupt file;
- one unsupported file;
- one file above the configured size limit;
- one attempted request with a wrong gateway API key.

For every valid case compare the derivative against the native source using an engineer-approved checklist (geometry, units, product structure, drawing sheets, annotations/PMI as applicable).

## Vendor documentation used for the design

- ASCON KOMPAS-3D Help: native M3D/A3D/T3D document types and STEP AP203/AP214/AP242 export.
- ASCON KOMPAS-3D Help: PDF export dialogs for drawings/fragments/specifications/text documents.
- T-FLEX CAD Help: export of 2D documents to PDF/DXF and 3D models to STEP.
- T-FLEX CAD Help: Open API documentation/examples and GRB document usage.

Exact automation calls depend on the licensed KOMPAS/T-FLEX release installed by your IT department. The repository intentionally does not emulate or reverse-engineer proprietary formats.
