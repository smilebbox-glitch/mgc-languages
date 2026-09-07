# Field Reliability & Product Lifecycle Intelligence — v5.8

## Purpose

v5.8 connects field/warranty evidence back to the controlled Engineering Digital Thread. It is an engineering intelligence/evidence layer, not a DMS, warranty-payment platform, CRM, recall authority or customer-profiling system.

Core flow:

```text
VIN / field claim
  -> build genealogy
  -> part / revision / supplier
  -> field exposure + reliability
  -> DFMEA / validation review
  -> 8D / ECR / ECO
  -> service action / next revision
  -> observed field effectiveness
  -> Engineering Knowledge Memory
```

## Reliability math

The deterministic core reports failure rate per population, failures per 1,000 vehicles and, when exposure-km is supplied, failures per million km.

The Weibull estimate is two-parameter and uses grouped right-censoring. Failure mileages are exact field events; the non-failed population is represented by `censored_count` at `censor_mileage_km`. When there are fewer than three mileage-bearing failures, no censored population, or no censor mileage, the system returns `INSUFFICIENT_DATA` instead of fitting a curve.

Weibull output is advisory and does not establish root cause. `beta < 1`, approximately `beta ~= 1`, and `beta > 1` are surfaced only as observed early/random/wear-out patterns.

## DFMEA and validation feedback

Field clusters are matched to controlled DFMEA failure modes and engineering requirements by deterministic part/token evidence. A field rate that appears inconsistent with a low occurrence assumption produces `DFMEA_REVIEW_REQUIRED`; the DFMEA is never edited automatically.

Validation effectiveness checks matching passed verification evidence and optional recorded `validated_mileage_km`. Field failure beyond that recorded exposure or absence of a matching passed verification becomes `VALIDATION_COVERAGE_GAP`; the V&V scope remains human-approved.

## Field clusters and campaign assessment

Failure clustering is an investigation aid. Part/revision/supplier/market/climate associations are explicitly `causal_claim=false`.

High/critical field signals may produce a `campaign candidate: REVIEW_REQUIRED`, but the platform cannot declare a recall, service campaign or safety defect. Those decisions require the corporate Quality, Engineering, Legal/Homologation and Management authorities.

## VIN trace and service actions

VIN trace resolves accessible build genealogy, field claims and TSB/field-containment/campaign-assessment applicability. Applicability uses explicit VIN scope and/or actual genealogy (part/revision/supplier). Unknown evidence remains unknown; no hidden data is inferred.

## Privacy / access

The platform does not build driver/customer profiles. Market and climate are technical aggregates only. Project, manufacturing-area, part and document ACL are authoritative. If a field/exposure/action record references mixed visible/hidden evidence, the entire record fails closed.
