from __future__ import annotations

import re
from pathlib import Path


_SCHEMA = re.compile(r"FILE_SCHEMA\s*\(\s*\((.*?)\)\s*\)\s*;", re.IGNORECASE | re.DOTALL)
_PRODUCT = re.compile(r"\bPRODUCT\s*\([^,]+,\s*'([^']*)'", re.IGNORECASE)

# Presence counts are deliberately reported as semantic *signals*. Full AP242 PMI
# decoding depends on the producer and should be validated against a golden set.
PMI_ENTITY_TOKENS = (
    "GEOMETRIC_TOLERANCE",
    "DATUM_FEATURE",
    "DATUM_REFERENCE",
    "DIMENSIONAL_SIZE",
    "DIMENSIONAL_LOCATION",
    "SHAPE_ASPECT",
    "PLUS_MINUS_TOLERANCE",
    "SURFACE_TEXTURE",
)


def inspect_step_semantics(path: Path, max_bytes: int = 64 * 1024 * 1024) -> dict:
    raw = path.read_bytes()[:max_bytes]
    text = raw.decode("latin-1", errors="ignore")
    schema_match = _SCHEMA.search(text)
    schema_raw = schema_match.group(1) if schema_match else ""
    schemas = sorted({x.strip(" '\"\r\n\t") for x in schema_raw.split(",") if x.strip(" '\"\r\n\t")})
    upper = text.upper()
    entity_counts = {token.lower(): upper.count(token) for token in PMI_ENTITY_TOKENS}
    pmi_signal_count = sum(entity_counts.values())
    products = []
    for m in _PRODUCT.finditer(text):
        value = m.group(1).strip()
        if value and value not in products:
            products.append(value)
        if len(products) >= 25:
            break
    is_ap242 = any("AP242" in s.upper() or "MANAGED_MODEL_BASED_3D_ENGINEERING" in s.upper() for s in schemas)
    return {
        "step_schemas": schemas,
        "ap242_detected": is_ap242,
        "product_names": products,
        "pmi_entity_counts": entity_counts,
        "pmi_semantic_signal_count": pmi_signal_count,
        "pmi_semantics_present": pmi_signal_count > 0,
        "pmi_values_decoded": False,
        "note": "PMI entity presence is deterministic; semantic PMI values require producer-specific AP242 validation.",
    }
