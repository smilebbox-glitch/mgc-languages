# Engineering Vision & CAD Intelligence — v3.8.0

## Purpose

The Engineering Vision layer extracts engineering facts without treating a generative model as the source of truth. The pipeline prefers deterministic source-native evidence and uses the local VLM as a verification/grounding layer.

## Processing order

```text
PDF / image                     STEP / STP / DXF / STL
     |                                   |
     v                                   v
Vector text + drawings                  OCCT/CadQuery
     |                                   |
Docling/OCR fallback              B-Rep/vector/mesh facts
     |                                   |
     +---------------+-------------------+
                     |
                     v
           Structured engineering facts
                     |
                     v
             Local VLM verification
                     |
                     v
          Evidence-first consensus
```

## 2D drawing intelligence

For PDF drawings, PyMuPDF is used before OCR to retain words and their page coordinates. The parser records engineering entities with page, bounding box, extraction method and confidence.

Recognized deterministic entity families include:

- diameter and radius dimensions;
- symmetric and asymmetric tolerances;
- metric thread designations;
- surface roughness (`Ra`);
- explicit thickness annotations (`THK`, `T=`);
- datum identifiers;
- common standards and selected Unicode GD&T symbols.

The title-block heuristic extracts explicitly labelled part number, revision, material, scale, mass and title fields. Ambiguous unlabeled numbers are intentionally ignored.

For scanned PDFs and raster images, Docling/OCR text remains a fallback. Facts without coordinate evidence are marked lower-confidence and can trigger `DRAWING_REVIEW_REQUIRED` during validation.

## Local VLM policy

`POST /api/v1/documents/{document_id}/visual-inspect` invokes the configured local VLM and requests strict structured JSON. The VLM can confirm, disagree with, or add an unmatched observation. It cannot silently overwrite deterministic facts.

Consensus output contains:

- `confirmed` — VLM agrees with a deterministic entity;
- `disagreements` — a mismatch requiring review;
- `unmatched_vlm` — VLM-only observations, non-authoritative;
- `policy` — explicit source-of-truth policy.

## CAD intelligence

### STEP / STP

The deterministic B-Rep layer records:

- solids, shells, wires, faces, edges and vertices;
- volume, surface area, center of mass and bounding box;
- plane/cylinder/cone/sphere/torus/B-spline surface counts;
- cylindrical radius/diameter candidates;
- addressable B-Rep face IDs with cylinder center, axis and bounding box;
- edge type statistics;
- scale-normalized bounding-box ratios;
- compactness and thin-part candidates.

STEP Part 21 content is also inspected for schema and semantic PMI signals. AP242-like schemas and PMI entity families are detected, but v3.8.0 **does not claim full semantic decoding of all PMI/GD&T values**. `pmi_values_decoded` remains `false` until producer-specific semantic mapping is validated.

### DXF

DXF is parsed as deterministic 2D vector geometry via CadQuery/OCCT. The engine records wires, edges, vertices, edge types and bounding box. It does not invent 3D thickness or volume.

### STL

STL remains a mesh-derived evidence source. Surface and watertight volume are recorded where valid, but mesh/tessellation is not treated as dimensional B-Rep metrology.

## Geometry similarity

The v2 deterministic fingerprint is mostly scale-normalized and includes:

- sorted bounding-box ratios;
- normalized volume and area;
- topology counts;
- surface-type distribution;
- compactness;
- cylindrical feature descriptors;
- lower-weight absolute scale.

Similarity responses include `match_factors` so an engineer can see *why* two parts were ranked as similar.

## API

```text
GET  /api/v1/documents/{id}/engineering-analysis
POST /api/v1/documents/{id}/engineering-analyze
POST /api/v1/documents/{id}/visual-inspect?max_pages=3
GET  /api/v1/documents/{id}/similar?limit=8
POST /api/v1/documents/{id}/link-geometry
GET  /api/v1/documents/{id}/geometry-links
```

The simplified Documents UI exposes **Разобрать чертёж**, **Связать с 3D**, **Проверить изображение ИИ**, and **Найти похожие 3D** actions where applicable. The Drawing ↔ CAD result is rendered in user-readable unique/ambiguous/unmatched states; raw metadata is collapsed under expert details.

## Provenance rules

1. Source bytes, hashes, source-system identity, CAD B-Rep and explicit vector text remain deterministic evidence.
2. OCR-derived facts are lower-confidence than vector/source-native evidence.
3. VLM observations are AI-derived and non-authoritative.
4. Conflicts are surfaced for review instead of resolved by hidden model preference.
5. Native proprietary CAD remains source evidence until an approved licensed CAD Gateway creates a traceable STEP derivative.

## Known limitations / next hardening step

- Full AP242 semantic PMI graph decoding is not yet implemented.
- GD&T symbol recognition from difficult raster scans needs an automotive drawing benchmark and targeted tuning.
- Dimension-to-specific-geometry association in 2D drawings is currently entity/bbox based; leader/extension-line graph tracing is the next stage.
- Native CATIA/NX/Creo/JT/SOLIDWORKS parsing still depends on the approved licensed CAD Gateway contract.


## Drawing ↔ CAD linking

The v3.3 linker matches coordinate-backed drawing entities to deterministic B-Rep candidates. Numeric agreement alone is never used to choose one of several repeated equal-size faces. See `DRAWING_CAD_LINKING.md` for status semantics and current spatial/PMI limitations.
