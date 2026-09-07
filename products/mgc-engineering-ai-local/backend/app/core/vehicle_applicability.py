from __future__ import annotations

from typing import Any, Mapping

VEHICLE_CLASSES = (
    "passenger_car",
    "lcv",
    "truck",
    "bus",
    "special_vehicle",
    "component",
)

POWERTRAIN_TYPES = ("ice", "hev", "phev", "bev", "fcev", "other")

PROFILE_KEYS = (
    "vehicle_class",
    "powertrain_type",
    "drivetrain",
    "wheelbase_mm",
    "axle_configuration",
    "plant",
    "cab_type",
    "gross_vehicle_weight_t",
    "payload_t",
    "battery_kwh",
)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_float(value: Any, minimum: float, maximum: float) -> float | None:
    if value is None or value == "":
        return None
    number = float(value)
    if number < minimum or number > maximum:
        raise ValueError(f"value {number} outside [{minimum}, {maximum}]")
    return number


def _clean_int(value: Any, minimum: int, maximum: int) -> int | None:
    if value is None or value == "":
        return None
    number = int(value)
    if number < minimum or number > maximum:
        raise ValueError(f"value {number} outside [{minimum}, {maximum}]")
    return number


def normalize_vehicle_profile(values: Mapping[str, Any], *, partial: bool = False) -> dict[str, Any]:
    """Return a bounded, canonical multi-vehicle profile.

    The profile is stored inside VehicleVariant.attributes_json so v6.3.34 does not
    require a database migration. Unknown/custom attributes remain outside this
    function and are preserved by ``merge_vehicle_profile``.
    """
    out: dict[str, Any] = {}
    for key in PROFILE_KEYS:
        if partial and key not in values:
            continue
        raw = values.get(key)
        if raw is None or raw == "":
            out[key] = None
            continue
        if key == "vehicle_class":
            val = _clean_text(raw)
            if val not in VEHICLE_CLASSES:
                raise ValueError(f"unsupported vehicle_class: {val}")
            out[key] = val
        elif key == "powertrain_type":
            val = _clean_text(raw)
            if val not in POWERTRAIN_TYPES:
                raise ValueError(f"unsupported powertrain_type: {val}")
            out[key] = val
        elif key == "wheelbase_mm":
            out[key] = _clean_int(raw, 1000, 15000)
        elif key in {"gross_vehicle_weight_t", "payload_t"}:
            out[key] = _clean_float(raw, 0, 200)
        elif key == "battery_kwh":
            out[key] = _clean_float(raw, 0, 5000)
        else:
            out[key] = _clean_text(raw)
    return out


def merge_vehicle_profile(attributes: Mapping[str, Any] | None, values: Mapping[str, Any], *, partial: bool = False) -> dict[str, Any]:
    merged = dict(attributes or {})
    profile = normalize_vehicle_profile(values, partial=partial)
    for key, value in profile.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def vehicle_profile(attributes: Mapping[str, Any] | None) -> dict[str, Any]:
    attrs = dict(attributes or {})
    result = {key: attrs.get(key) for key in PROFILE_KEYS if attrs.get(key) is not None}
    return result
