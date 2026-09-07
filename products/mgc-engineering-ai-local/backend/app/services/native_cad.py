from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class NativeCadProfile:
    vendor: str
    product: str
    source_format: str
    document_kind: str
    preferred_target: str
    alternate_targets: tuple[str, ...]
    deterministic_after_conversion: bool = True
    note: str = ""


_KOMPAS = {
    ".m3d": ("model", "step", ("x_t", "stl")),
    ".a3d": ("assembly", "step", ("x_t",)),
    ".t3d": ("technology_assembly", "step", ("x_t",)),
    ".cdw": ("drawing", "pdf", ("dxf",)),
    ".frw": ("fragment", "pdf", ("dxf",)),
    ".spw": ("specification", "pdf", ("xlsx", "csv")),
    ".kdw": ("text_document", "pdf", ("txt",)),
}

_TFLEX = {
    # A GRB may contain a 2D document, 3D model or both. The gateway must inspect
    # the document and choose STEP for geometry or PDF for drawing-first content.
    ".grb": ("mixed", "auto", ("step", "pdf", "dxf")),
}


def native_cad_profile(path_or_extension: str | Path) -> NativeCadProfile | None:
    raw = str(path_or_extension)
    ext = Path(raw).suffix.lower() if not raw.startswith(".") else raw.lower()
    if ext in _KOMPAS:
        kind, preferred, alternates = _KOMPAS[ext]
        return NativeCadProfile(
            vendor="kompas",
            product="КОМПАС-3D",
            source_format=ext.lstrip("."),
            document_kind=kind,
            preferred_target=preferred,
            alternate_targets=alternates,
            note="Native source remains immutable; conversion is performed by an approved local KOMPAS gateway.",
        )
    if ext in _TFLEX:
        kind, preferred, alternates = _TFLEX[ext]
        return NativeCadProfile(
            vendor="tflex",
            product="T-FLEX CAD",
            source_format=ext.lstrip("."),
            document_kind=kind,
            preferred_target=preferred,
            alternate_targets=alternates,
            note="GRB is polymorphic; the local T-FLEX gateway must inspect the document before selecting STEP/PDF.",
        )
    return None


def native_cad_metadata(path_or_extension: str | Path) -> dict:
    profile = native_cad_profile(path_or_extension)
    if not profile:
        return {}
    data = asdict(profile)
    data["alternate_targets"] = list(profile.alternate_targets)
    data["native_cad"] = True
    data["conversion_required"] = True
    return data


def preferred_conversion_target(path_or_extension: str | Path) -> str:
    profile = native_cad_profile(path_or_extension)
    return profile.preferred_target if profile else "step"


def native_vendor(path_or_extension: str | Path) -> str | None:
    profile = native_cad_profile(path_or_extension)
    return profile.vendor if profile else None


def gateway_config_supports(config: dict, path_or_extension: str | Path) -> bool:
    """Check whether a configured CAD gateway declares support for this source.

    Backward compatibility: a gateway with no vendor/extensions declaration is
    considered generic and may be used only as the final fallback.
    """
    profile = native_cad_profile(path_or_extension)
    ext = Path(str(path_or_extension)).suffix.lower() if not str(path_or_extension).startswith(".") else str(path_or_extension).lower()
    vendors = {str(x).strip().lower() for x in config.get("vendors", []) if str(x).strip()}
    if config.get("vendor"):
        vendors.add(str(config["vendor"]).strip().lower())
    extensions = {str(x).strip().lower() for x in config.get("extensions", []) if str(x).strip()}
    if extensions and ext not in extensions:
        return False
    if profile and vendors and profile.vendor not in vendors:
        return False
    return bool(vendors or extensions)
