from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from app.services.step_semantics import inspect_step_semantics


STEP_EXTENSIONS = {".step", ".stp"}
MESH_EXTENSIONS = {".stl"}
DXF_EXTENSIONS = {".dxf"}
CAD_EXTENSIONS = STEP_EXTENSIONS | MESH_EXTENSIONS | DXF_EXTENSIONS


def _vec_xyz(v: Any) -> dict[str, float]:
    return {"x": float(v.x), "y": float(v.y), "z": float(v.z)}


def _rounded(values: list[float], digits: int = 4) -> list[float]:
    return sorted(round(float(x), digits) for x in values)


def _point_xyz(p: Any) -> dict[str, float]:
    return {"x": round(float(p.X()), 6), "y": round(float(p.Y()), 6), "z": round(float(p.Z()), 6)}


def _dir_xyz(p: Any) -> dict[str, float]:
    return {"x": round(float(p.X()), 6), "y": round(float(p.Y()), 6), "z": round(float(p.Z()), 6)}


def _bbox_dict(box: Any) -> dict[str, float | dict[str, float]]:
    return {
        "x": round(float(box.xlen), 6), "y": round(float(box.ylen), 6), "z": round(float(box.zlen), 6),
        "min": {"x": round(float(box.xmin), 6), "y": round(float(box.ymin), 6), "z": round(float(box.zmin), 6)},
        "max": {"x": round(float(box.xmax), 6), "y": round(float(box.ymax), 6), "z": round(float(box.zmax), 6)},
    }


def _surface_stats(shape) -> dict:
    """Return deterministic B-Rep surface statistics and addressable features.

    CadQuery intentionally exposes a small high-level surface API. For exact
    cylinder/cone parameters we use the OCCT adaptors shipped with CadQuery.
    Feature IDs are stable within the imported model and are evidence pointers,
    not persistent PLM identifiers.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    types: dict[str, int] = {}
    cylindrical_radii: list[float] = []
    conical_radii: list[float] = []
    features: list[dict] = []
    for idx, face in enumerate(shape.Faces()):
        try:
            typ = str(face.geomType()).upper()
        except Exception:
            typ = "UNKNOWN"
        types[typ] = types.get(typ, 0) + 1
        base = {
            "feature_id": f"face:{idx:04d}",
            "topology": "face",
            "surface_type": typ.lower(),
            "center_mm": _vec_xyz(face.Center()),
            "bounding_box_mm": _bbox_dict(face.BoundingBox()),
            "area_mm2": round(float(face.Area()), 6),
        }
        if typ == "CYLINDER":
            try:
                adaptor = BRepAdaptor_Surface(face.wrapped, True)
                cyl = adaptor.Cylinder()
                radius = float(cyl.Radius())
                cylindrical_radii.append(radius)
                axis = cyl.Axis()
                base.update({
                    "kind": "cylindrical_face",
                    "radius_mm": round(radius, 6),
                    "diameter_mm": round(2.0 * radius, 6),
                    "axis_origin_mm": _point_xyz(axis.Location()),
                    "axis_direction": _dir_xyz(axis.Direction()),
                })
            except Exception as exc:
                base.update({"kind": "cylindrical_face", "parameter_error": type(exc).__name__})
        elif typ == "CONE":
            try:
                adaptor = BRepAdaptor_Surface(face.wrapped, True)
                cone = adaptor.Cone()
                radius = float(cone.RefRadius())
                conical_radii.append(radius)
                base.update({"kind": "conical_face", "reference_radius_mm": round(radius, 6)})
            except Exception as exc:
                base.update({"kind": "conical_face", "parameter_error": type(exc).__name__})
        elif typ == "PLANE":
            base["kind"] = "planar_face"
        else:
            base["kind"] = f"{typ.lower()}_face"
        features.append(base)
    radii = _rounded(cylindrical_radii)
    return {
        "surface_types": dict(sorted(types.items())),
        "cylindrical_face_count": types.get("CYLINDER", 0),
        "planar_face_count": types.get("PLANE", 0),
        "conical_face_count": types.get("CONE", 0),
        "spherical_face_count": types.get("SPHERE", 0),
        "toroidal_face_count": types.get("TORUS", 0),
        "bspline_face_count": types.get("BSPLINE", 0) + types.get("BSPLINE SURFACE", 0),
        "cylindrical_radii_mm": radii,
        "cylindrical_diameters_mm": _rounded([2.0 * x for x in cylindrical_radii]),
        "candidate_cylindrical_feature_diameters_mm": _rounded([2.0 * x for x in cylindrical_radii]),
        "conical_radii_mm": _rounded(conical_radii),
        "geometry_features": features,
    }


def _edge_stats(shape) -> dict:
    from OCP.BRepAdaptor import BRepAdaptor_Curve

    types: dict[str, int] = {}
    circular_radii: list[float] = []
    features: list[dict] = []
    for idx, edge in enumerate(shape.Edges()):
        try:
            typ = str(edge.geomType()).upper()
        except Exception:
            typ = "UNKNOWN"
        types[typ] = types.get(typ, 0) + 1
        if typ in {"CIRCLE", "ARC"}:
            try:
                adaptor = BRepAdaptor_Curve(edge.wrapped)
                circle = adaptor.Circle()
                radius = float(circle.Radius())
                circular_radii.append(radius)
                axis = circle.Axis()
                features.append({
                    "feature_id": f"edge:{idx:04d}",
                    "topology": "edge",
                    "kind": "circular_edge",
                    "curve_type": typ.lower(),
                    "radius_mm": round(radius, 6),
                    "diameter_mm": round(2.0 * radius, 6),
                    "center_mm": _point_xyz(circle.Location()),
                    "axis_direction": _dir_xyz(axis.Direction()),
                    "bounding_box_mm": _bbox_dict(edge.BoundingBox()),
                })
            except Exception:
                pass
    return {
        "edge_types": dict(sorted(types.items())),
        "circular_edge_count": types.get("CIRCLE", 0) + types.get("ARC", 0),
        "circular_edge_radii_mm": _rounded(circular_radii),
        "geometry_edge_features": features,
    }

def _shape_descriptors(metadata: dict) -> dict:
    b = metadata.get("bounding_box_mm") or {}
    dims = sorted([float(b.get("x") or 0), float(b.get("y") or 0), float(b.get("z") or 0)])
    largest = max(dims) if dims else 0.0
    ratios = [round(x / largest, 6) if largest else 0.0 for x in dims]
    vol = float(metadata.get("volume_mm3") or 0.0)
    area = float(metadata.get("surface_area_mm2") or 0.0)
    compactness = None
    if vol > 0 and area > 0:
        # Isoperimetric quotient: 1.0 for a perfect sphere, lower for elongated/complex parts.
        compactness = 36.0 * math.pi * (vol ** 2) / (area ** 3)
    return {
        "bbox_sorted_mm": [round(x, 6) for x in dims],
        "bbox_ratios": ratios,
        "aspect_ratio_long_to_short": round(largest / max(dims[0], 1e-9), 6) if largest and dims else None,
        "compactness": round(compactness, 8) if compactness is not None else None,
        "thin_part_candidate": bool(largest and dims and dims[0] / largest <= 0.08),
        "bbox_min_thickness_candidate_mm": round(dims[0], 6) if largest and dims and dims[0] / largest <= 0.08 else None,
    }


def analyze_step(path: Path, preview_dir: Path, density_g_cm3: float | None = None) -> tuple[str, dict, Path | None]:
    import cadquery as cq

    wp = cq.importers.importStep(str(path))
    shapes = wp.vals()
    if not shapes:
        raise ValueError("STEP file contains no importable shapes")
    compound = cq.Compound.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
    bbox = compound.BoundingBox()
    center = compound.Center()
    volume = float(compound.Volume())
    surface = float(compound.Area())
    metadata = {
        "cad_kernel": "CadQuery/OCCT",
        "geometry_authority": "deterministic_brep",
        "units": "mm",
        "shape_count": len(shapes),
        "solid_count": len(compound.Solids()),
        "shell_count": len(compound.Shells()),
        "wire_count": len(compound.Wires()),
        "face_count": len(compound.Faces()),
        "edge_count": len(compound.Edges()),
        "vertex_count": len(compound.Vertices()),
        "volume_mm3": volume,
        "surface_area_mm2": surface,
        "center_of_mass_mm": _vec_xyz(center),
        "bounding_box_mm": {
            "x": float(bbox.xlen), "y": float(bbox.ylen), "z": float(bbox.zlen),
            "min": {"x": float(bbox.xmin), "y": float(bbox.ymin), "z": float(bbox.zmin)},
            "max": {"x": float(bbox.xmax), "y": float(bbox.ymax), "z": float(bbox.zmax)},
        },
        **_surface_stats(compound),
        **_edge_stats(compound),
    }
    metadata.update(_shape_descriptors(metadata))
    try:
        metadata["step_semantics"] = inspect_step_semantics(path)
    except Exception as exc:
        metadata["step_semantics"] = {"error": f"{type(exc).__name__}: {exc}"}

    if density_g_cm3:
        # 1 cm3 = 1000 mm3; density g/cm3 -> kg = volume/1000*density/1000
        metadata["estimated_mass_kg"] = volume * density_g_cm3 / 1_000_000.0
        metadata["density_g_cm3"] = density_g_cm3

    preview_dir.mkdir(parents=True, exist_ok=True)
    preview = preview_dir / f"{path.stem}.stl"
    cq.exporters.export(compound, str(preview), tolerance=0.08, angularTolerance=0.15)
    sem = metadata.get("step_semantics") or {}
    summary = (
        f"CAD STEP model {path.name}. Deterministic B-Rep analysis. Solids: {metadata['solid_count']}; "
        f"faces: {metadata['face_count']}; edges: {metadata['edge_count']}; cylindrical faces: {metadata['cylindrical_face_count']}. "
        f"Volume: {volume:.3f} mm3; surface area: {surface:.3f} mm2. "
        f"Bounding box X={bbox.xlen:.3f} mm, Y={bbox.ylen:.3f} mm, Z={bbox.zlen:.3f} mm. "
        f"Center of mass X={center.x:.3f}, Y={center.y:.3f}, Z={center.z:.3f} mm. "
        f"STEP schema: {', '.join(sem.get('step_schemas') or []) or 'unknown'}; AP242 detected: {bool(sem.get('ap242_detected'))}; "
        f"PMI semantic signals: {int(sem.get('pmi_semantic_signal_count') or 0)}."
    )
    return summary, metadata, preview


def analyze_dxf(path: Path, preview_dir: Path, density_g_cm3: float | None = None) -> tuple[str, dict, Path | None]:
    import cadquery as cq

    wp = cq.importers.importDXF(str(path))
    shapes = wp.vals()
    if not shapes:
        raise ValueError("DXF contains no importable geometry")
    compound = cq.Compound.makeCompound(shapes) if len(shapes) > 1 else shapes[0]
    bbox = compound.BoundingBox()
    metadata = {
        "cad_kernel": "CadQuery/OCCT DXF",
        "geometry_authority": "deterministic_2d_vector",
        "units": "mm",
        "shape_count": len(shapes),
        "wire_count": len(compound.Wires()),
        "edge_count": len(compound.Edges()),
        "vertex_count": len(compound.Vertices()),
        "bounding_box_mm": {
            "x": float(bbox.xlen), "y": float(bbox.ylen), "z": float(bbox.zlen),
            "min": {"x": float(bbox.xmin), "y": float(bbox.ymin), "z": float(bbox.zmin)},
            "max": {"x": float(bbox.xmax), "y": float(bbox.ymax), "z": float(bbox.zmax)},
        },
        **_edge_stats(compound),
        "geometry_fidelity": "2d_vector",
    }
    metadata.update(_shape_descriptors(metadata))
    summary = (
        f"DXF vector geometry {path.name}. Wires: {metadata['wire_count']}; edges: {metadata['edge_count']}; "
        f"bounding box X={bbox.xlen:.3f} mm, Y={bbox.ylen:.3f} mm, Z={bbox.zlen:.3f} mm."
    )
    return summary, metadata, None


def analyze_stl(path: Path, preview_dir: Path, density_g_cm3: float | None = None) -> tuple[str, dict, Path | None]:
    import shutil
    import trimesh

    mesh = trimesh.load_mesh(str(path), force="mesh")
    if mesh.is_empty:
        raise ValueError("STL contains no mesh geometry")
    bounds = mesh.bounds
    extents = mesh.extents
    metadata = {
        "cad_kernel": "Trimesh (mesh, not B-Rep)",
        "geometry_authority": "deterministic_mesh",
        "units": "assumed mm",
        "mesh_vertices": int(len(mesh.vertices)),
        "mesh_faces": int(len(mesh.faces)),
        "surface_area_mm2": float(mesh.area),
        "volume_mm3": float(abs(mesh.volume)) if mesh.is_watertight else None,
        "watertight": bool(mesh.is_watertight),
        "bounding_box_mm": {
            "x": float(extents[0]), "y": float(extents[1]), "z": float(extents[2]),
            "min": {"x": float(bounds[0][0]), "y": float(bounds[0][1]), "z": float(bounds[0][2])},
            "max": {"x": float(bounds[1][0]), "y": float(bounds[1][1]), "z": float(bounds[1][2])},
        },
        "geometry_fidelity": "mesh",
    }
    metadata.update(_shape_descriptors(metadata))
    if density_g_cm3 and metadata["volume_mm3"] is not None:
        metadata["estimated_mass_kg"] = metadata["volume_mm3"] * density_g_cm3 / 1_000_000.0
        metadata["density_g_cm3"] = density_g_cm3
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview = preview_dir / path.name
    shutil.copy2(path, preview)
    summary = (f"STL mesh {path.name}. Vertices: {metadata['mesh_vertices']}; faces: {metadata['mesh_faces']}; "
               f"surface area: {metadata['surface_area_mm2']:.3f} mm2; watertight: {metadata['watertight']}. "
               f"Bounding box X={extents[0]:.3f}, Y={extents[1]:.3f}, Z={extents[2]:.3f} mm.")
    if metadata["volume_mm3"] is not None:
        summary += f" Volume: {metadata['volume_mm3']:.3f} mm3."
    return summary, metadata, preview
