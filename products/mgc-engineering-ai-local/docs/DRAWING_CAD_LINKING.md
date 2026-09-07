# Drawing ↔ CAD Linking — v3.8.0

## Goal

Link structured dimensions extracted from engineering drawings to deterministic STEP/OCCT B-Rep candidates without inventing a geometric identity.

## Data flow

```text
Vector PDF / OCR
      |
      v
Engineering entities
(diameter/radius/thickness/thread/dimension)
      |
      v
Drawing-CAD Linker
      |
      +--> STEP B-Rep geometry feature inventory
      |       face:0000 ... face:NNNN
      |       radius / diameter / center / axis / bbox
      |
      v
linked_unique | linked_multiple | unmatched
```

## Status semantics

- `linked_unique`: one deterministic B-Rep candidate matches the engineering value. If the drawing entity also has a coordinate bbox, `verified=true`.
- `linked_multiple`: two or more equal geometry candidates match. The system **does not choose one**.
- `unmatched`: no deterministic candidate is within the conservative numeric threshold.

Repeated holes are a common `linked_multiple` case. A drawing label `Ø8` cannot, by numeric value alone, prove which one of four Ø8 holes is intended.

## Geometry feature inventory

STEP parsing now records addressable face features. Cylindrical features include:

- `feature_id` (for example `face:0009`);
- exact OCCT radius and diameter;
- face center;
- cylinder axis origin and direction;
- face bounding box;
- surface area.

The parameters come from `BRepAdaptor_Surface`, not from tessellated STL geometry.

## API

```text
POST /api/v1/documents/{drawing_document_id}/link-geometry
GET  /api/v1/documents/{drawing_document_id}/geometry-links
GET  /api/v1/documents/{document_id}/engineering-analysis
```

Optional explicit pairing:

```text
POST /api/v1/documents/{drawing_document_id}/link-geometry?cad_document_id=<id>
```

Automatic pairing requires the same part number and, when known, the same revision. If several CAD models exist for one revision the system asks for an explicit selection instead of guessing.

## Validation rules

v3.3 adds:

- `DRAWING_CAD_PAIR_MISSING` — exact CAD revision is unavailable;
- `DRAWING_CAD_DIMENSION_UNMATCHED` — drawing dimensions have no deterministic CAD candidate;
- `DRAWING_CAD_LINK_AMBIGUOUS` — repeated geometry candidates require spatial/PMI disambiguation.

## Current boundary

v3.3 is deterministic **candidate linking**, not full drawing-view reconstruction. Full face-specific disambiguation for repeated equal features requires one or more of:

1. semantic AP242 PMI that carries feature references;
2. validated drawing-view / 3D projection transforms;
3. leader/extension-line geometry linked to projected CAD edges;
4. engineer confirmation stored as a controlled relationship.

This boundary is intentional: false certainty is worse than an explicit ambiguous result in engineering review.
