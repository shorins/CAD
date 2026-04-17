"""
Импорт DXF файлов во внутреннюю модель приложения.
"""

from __future__ import annotations

import math
from pathlib import Path

from ..core.geometry import Arc, Circle, Ellipse, Line, Point, PointEntity, Rectangle, Spline
from ..core.layers import LayerRecord, default_layer
from .mapping import display_style_for_layer, entity_metadata_to_dict, effective_linetype_name, map_linetype_to_style

Z_TOLERANCE = 1e-6
MAX_BLOCK_DEPTH = 8


def import_dxf_file(file_path: str | Path) -> dict:
    """Импортирует DXF-файл и возвращает данные для сцены."""
    ezdxf, recover, DXFError, OCS, Vec3 = _load_ezdxf_dependencies()

    file_path = Path(file_path)
    report = {
        "file_path": str(file_path),
        "recovered": False,
        "binary": _is_binary_dxf(file_path),
        "imported_count": 0,
        "skipped_count": 0,
        "warnings": [],
        "skipped_details": [],
        "skipped_summary": {},
        "paperspace_skipped_count": 0,
    }

    try:
        doc = ezdxf.readfile(file_path)
        audit = doc.audit()
        if audit.has_errors:
            report["warnings"].append(f"DXF audit обнаружил ошибок: {len(audit.errors)}")
    except DXFError as exc:
        if report["binary"]:
            raise RuntimeError(f"Не удалось прочитать binary DXF: {exc}") from exc
        doc, audit = recover.readfile(file_path)
        report["recovered"] = True
        report["warnings"].append(f"DXF был открыт через recover: {exc}")
        if audit.has_errors:
            report["warnings"].append(f"recover audit обнаружил ошибок: {len(audit.errors)}")

    layers = _read_layers(doc)
    document_meta = _read_document_meta(doc)
    objects = []

    for entity in doc.modelspace():
        imported_objects = _import_entity(
            entity,
            layers,
            report,
            OCS=OCS,
            Vec3=Vec3,
            block_context=[],
            depth=0,
        )
        objects.extend(imported_objects)

    for layout in doc.layouts:
        if layout.name.lower() == "model":
            continue
        report["paperspace_skipped_count"] += len(layout)

    report["imported_count"] = len(objects)
    report["layer_count"] = len(layers)
    report["dxf_version"] = document_meta.get("dxf_version")

    return {
        "objects": objects,
        "layers": layers,
        "document_meta": document_meta,
        "report": report,
        "current_layer_name": "0",
    }


def _import_entity(entity, layers, report, OCS, Vec3, block_context, depth: int):
    entity_type = entity.dxftype()
    if depth > MAX_BLOCK_DEPTH:
        _skip_entity(report, entity, "Превышена глубина вложенности блоков", block_context)
        return []

    try:
        if entity_type == "INSERT":
            return _import_insert(entity, layers, report, OCS, Vec3, block_context, depth)
        if entity.dxf.paperspace:
            _skip_entity(report, entity, "paperspace layout не поддерживается", block_context)
            return []

        if entity_type == "POINT":
            obj = _import_point(entity, layers, OCS, Vec3)
            return [obj] if obj else []
        if entity_type == "LINE":
            obj = _import_line(entity, layers)
            return [obj] if obj else []
        if entity_type == "CIRCLE":
            obj = _import_circle(entity, layers, OCS, Vec3)
            return [obj] if obj else []
        if entity_type == "ARC":
            obj = _import_arc(entity, layers, OCS, Vec3)
            return [obj] if obj else []
        if entity_type == "ELLIPSE":
            obj = _import_ellipse(entity, layers)
            return [obj] if obj else []
        if entity_type in {"LWPOLYLINE", "POLYLINE"}:
            return _import_virtual_entities(entity, layers, report, OCS, Vec3, block_context, depth)
        if entity_type == "SPLINE":
            obj = _import_spline(entity, layers)
            return [obj] if obj else []
        _skip_entity(report, entity, f"Тип {entity_type} не поддерживается", block_context)
        return []
    except UnsupportedDXFEntity as exc:
        _skip_entity(report, entity, str(exc), block_context)
        return []
    except Exception as exc:
        _skip_entity(report, entity, f"Ошибка импорта: {exc}", block_context)
        return []


def _import_virtual_entities(entity, layers, report, OCS, Vec3, block_context, depth: int):
    objects = []
    try:
        virtual_entities = list(entity.virtual_entities())
    except Exception as exc:
        _skip_entity(report, entity, f"Не удалось разложить сущность: {exc}", block_context)
        return []

    for child in virtual_entities:
        objects.extend(
            _import_entity(
                child,
                layers,
                report,
                OCS=OCS,
                Vec3=Vec3,
                block_context=block_context,
                depth=depth + 1,
            )
        )
    return objects


def _import_insert(entity, layers, report, OCS, Vec3, block_context, depth: int):
    block_name = getattr(entity.dxf, "name", "<unnamed>")
    return _import_virtual_entities(
        entity,
        layers,
        report,
        OCS=OCS,
        Vec3=Vec3,
        block_context=block_context + [block_name],
        depth=depth + 1,
    )


def _import_point(entity, layers, OCS, Vec3):
    location = _to_wcs_point(entity.ocs(), entity.dxf.location, Vec3)
    _ensure_xy_point(location, "POINT вне плоскости XY")
    obj = PointEntity(Point(location.x, location.y))
    _apply_entity_metadata(obj, entity, layers)
    return obj


def _import_line(entity, layers):
    start = Point(float(entity.dxf.start.x), float(entity.dxf.start.y))
    end = Point(float(entity.dxf.end.x), float(entity.dxf.end.y))
    if abs(float(entity.dxf.start.z)) > Z_TOLERANCE or abs(float(entity.dxf.end.z)) > Z_TOLERANCE:
        raise UnsupportedDXFEntity("LINE с Z-координатой не поддерживается")
    obj = Line(start, end)
    _apply_entity_metadata(obj, entity, layers)
    return obj


def _import_circle(entity, layers, OCS, Vec3):
    if not _is_xy_extrusion(getattr(entity.dxf, "extrusion", None)):
        raise UnsupportedDXFEntity("CIRCLE в произвольной OCS-плоскости не поддерживается")
    center = _to_wcs_point(entity.ocs(), entity.dxf.center, Vec3)
    _ensure_xy_point(center, "CIRCLE вне плоскости XY")
    obj = Circle(Point(center.x, center.y), float(entity.dxf.radius))
    _apply_entity_metadata(obj, entity, layers)
    return obj


def _import_arc(entity, layers, OCS, Vec3):
    if not _is_xy_extrusion(getattr(entity.dxf, "extrusion", None)):
        raise UnsupportedDXFEntity("ARC в произвольной OCS-плоскости не поддерживается")

    start = Point(float(entity.start_point.x), float(entity.start_point.y))
    end = Point(float(entity.end_point.x), float(entity.end_point.y))
    if abs(float(entity.start_point.z)) > Z_TOLERANCE or abs(float(entity.end_point.z)) > Z_TOLERANCE:
        raise UnsupportedDXFEntity("ARC вне плоскости XY")

    mid_point = _build_arc_midpoint(entity, Vec3)
    obj = Arc.from_three_points(start, Point(mid_point.x, mid_point.y), end)
    if obj is None:
        raise UnsupportedDXFEntity("ARC не удалось восстановить по трём точкам")
    _apply_entity_metadata(obj, entity, layers)
    return obj


def _import_ellipse(entity, layers):
    start_param = float(entity.dxf.start_param)
    end_param = float(entity.dxf.end_param)
    if not (math.isclose(start_param, 0.0, abs_tol=1e-6) and math.isclose(end_param, math.tau, abs_tol=1e-6)):
        raise UnsupportedDXFEntity("Эллиптические дуги не поддерживаются")

    center = entity.dxf.center
    major_axis = entity.dxf.major_axis
    if abs(float(center.z)) > Z_TOLERANCE or abs(float(major_axis.z)) > Z_TOLERANCE:
        raise UnsupportedDXFEntity("ELLIPSE вне плоскости XY")

    ratio = float(entity.dxf.ratio)
    major_len = math.hypot(float(major_axis.x), float(major_axis.y))
    if major_len <= Z_TOLERANCE:
        raise UnsupportedDXFEntity("ELLIPSE с нулевой большой полуосью")

    if math.isclose(float(major_axis.y), 0.0, abs_tol=1e-6):
        radius_x = major_len
        radius_y = major_len * ratio
    elif math.isclose(float(major_axis.x), 0.0, abs_tol=1e-6):
        radius_x = major_len * ratio
        radius_y = major_len
    else:
        raise UnsupportedDXFEntity("Повернутый ELLIPSE не поддерживается")

    obj = Ellipse(Point(float(center.x), float(center.y)), radius_x, radius_y)
    _apply_entity_metadata(obj, entity, layers)
    return obj


def _import_spline(entity, layers):
    control_points = [Point(float(p[0]), float(p[1])) for p in entity.control_points]
    fit_points = [Point(float(p[0]), float(p[1])) for p in entity.fit_points]

    points_to_check = control_points or fit_points
    if not points_to_check:
        raise UnsupportedDXFEntity("SPLINE без точек не поддерживается")

    for point in points_to_check:
        if hasattr(point, "z") and abs(float(point.z)) > Z_TOLERANCE:
            raise UnsupportedDXFEntity("SPLINE вне плоскости XY")

    raw_points = list(entity.control_points) + list(entity.fit_points)
    for raw_point in raw_points:
        if len(raw_point) >= 3 and abs(float(raw_point[2])) > Z_TOLERANCE:
            raise UnsupportedDXFEntity("SPLINE вне плоскости XY")

    spline = Spline(
        control_points=control_points,
        closed=bool(entity.closed),
        degree=int(entity.dxf.degree),
        knots=list(entity.knots),
        weights=list(entity.weights),
        fit_points=fit_points,
    )
    spline.is_exact_dxf_spline = bool(spline.knots or spline.fit_points)
    _apply_entity_metadata(spline, entity, layers)
    return spline


def _read_layers(doc) -> dict[str, LayerRecord]:
    layers = {"0": default_layer()}
    for layer in doc.layers:
        name = layer.dxf.name
        record = LayerRecord(
            name=name,
            aci_color=int(getattr(layer.dxf, "color", 7)),
            true_color=getattr(layer.dxf, "true_color", None),
            linetype_name=getattr(layer.dxf, "linetype", "CONTINUOUS"),
            lineweight=getattr(layer.dxf, "lineweight", None),
            flags=int(getattr(layer.dxf, "flags", 0)),
            display_style_name=map_linetype_to_style(getattr(layer.dxf, "linetype", "CONTINUOUS")),
            plot=not bool(getattr(layer.dxf, "plot", 0) == 0),
        )
        layers[name] = record
    return layers


def _read_document_meta(doc) -> dict:
    header = doc.header
    extmin = header.get("$EXTMIN")
    extmax = header.get("$EXTMAX")
    return {
        "source_format": "dxf",
        "dxf_version": header.get("$ACADVER", getattr(doc, "dxfversion", None)),
        "insunits": header.get("$INSUNITS"),
        "extmin": tuple(extmin) if extmin is not None else None,
        "extmax": tuple(extmax) if extmax is not None else None,
    }


def _apply_entity_metadata(obj, entity, layers):
    metadata = entity_metadata_to_dict(entity)
    layer = layers.get(metadata["layer_name"])
    effective_linetype = effective_linetype_name(metadata["linetype_name"], layer)
    obj.style_name = map_linetype_to_style(effective_linetype, display_style_for_layer(layer))
    obj.layer_name = metadata["layer_name"]
    obj.aci_color = metadata["aci_color"]
    obj.true_color = metadata["true_color"]
    obj.linetype_name = metadata["linetype_name"]
    obj.lineweight = metadata["lineweight"]
    obj.source_handle = metadata["source_handle"]
    obj.source_entity_type = metadata["source_entity_type"]
    obj.import_flags = list(metadata["import_flags"])


def _build_arc_midpoint(entity, Vec3):
    center = Vec3(entity.dxf.center)
    radius = float(entity.dxf.radius)
    start_angle = float(entity.dxf.start_angle)
    end_angle = float(entity.dxf.end_angle)
    span = end_angle - start_angle
    if span <= 0:
        span += 360.0
    mid_angle = math.radians(start_angle + span / 2.0)
    ocs = entity.ocs()
    point = Vec3(
        center.x + radius * math.cos(mid_angle),
        center.y + radius * math.sin(mid_angle),
        center.z,
    )
    midpoint = ocs.to_wcs(point)
    _ensure_xy_point(midpoint, "ARC midpoint вне плоскости XY")
    return midpoint


def _to_wcs_point(ocs, value, Vec3):
    return ocs.to_wcs(Vec3(value))


def _ensure_xy_point(point, reason: str):
    if abs(float(point.z)) > Z_TOLERANCE:
        raise UnsupportedDXFEntity(reason)


def _is_xy_extrusion(extrusion) -> bool:
    if extrusion is None:
        return True
    return (
        math.isclose(abs(float(extrusion.z)), 1.0, abs_tol=1e-6)
        and math.isclose(float(extrusion.x), 0.0, abs_tol=1e-6)
        and math.isclose(float(extrusion.y), 0.0, abs_tol=1e-6)
    )


def _skip_entity(report, entity, reason: str, block_context):
    entity_type = entity.dxftype()
    report["skipped_count"] += 1
    report["skipped_details"].append(
        {
            "entity_type": entity_type,
            "handle": getattr(entity.dxf, "handle", None),
            "layer": getattr(entity.dxf, "layer", "0"),
            "reason": reason,
            "block_context": list(block_context),
        }
    )
    report["skipped_summary"][reason] = report["skipped_summary"].get(reason, 0) + 1


def _is_binary_dxf(file_path: Path) -> bool:
    with open(file_path, "rb") as stream:
        header = stream.read(24)
    return header.startswith(b"AutoCAD Binary DXF")


def _load_ezdxf_dependencies():
    try:
        import ezdxf
        from ezdxf import recover
        from ezdxf.lldxf.const import DXFError
        from ezdxf.math import OCS, Vec3
    except ImportError as exc:
        raise RuntimeError("Для работы с DXF установите зависимость 'ezdxf'.") from exc
    return ezdxf, recover, DXFError, OCS, Vec3


class UnsupportedDXFEntity(RuntimeError):
    """Ошибка неподдерживаемой DXF-сущности."""
