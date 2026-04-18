"""
Экспорт внутренней сцены приложения в DXF.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from pathlib import Path

from ..core.geometry import Arc, Circle, Ellipse, Line, PointEntity, Polygon, Rectangle, Spline
from ..core.layers import LayerRecord, default_layer
from .mapping import DEFAULT_DXF_VERSION, apply_common_entity_attributes, map_style_to_linetype


def export_dxf_file(scene, file_path: str | Path, version: str = DEFAULT_DXF_VERSION) -> dict:
    """Экспортирует сцену в DXF файл."""
    ezdxf = _load_ezdxf()
    file_path = Path(file_path)

    doc = ezdxf.new(version, setup=True)
    msp = doc.modelspace()
    report = {
        "file_path": str(file_path),
        "version": version,
        "written_entities": 0,
        "decomposed_objects": 0,
        "created_layers": [],
        "created_linetypes": [],
        "warnings": [],
    }

    insunits = scene.document_meta.get("insunits")
    if insunits is not None:
        doc.header["$INSUNITS"] = int(insunits)

    _ensure_linetypes(doc, scene, report)
    _ensure_layers(doc, scene, report)

    for obj in scene.objects:
        written = _export_object(doc, msp, obj, scene, report)
        report["written_entities"] += written

    auditor = doc.audit()
    if auditor.has_errors:
        raise RuntimeError(f"DXF audit завершился с ошибками: {len(auditor.errors)}")

    doc.saveas(file_path)
    return report


def _export_object(doc, msp, obj, scene, report: dict) -> int:
    layer = scene.layers.get(getattr(obj, "layer_name", "0"), default_layer())

    if isinstance(obj, PointEntity):
        entity = msp.add_point((obj.position.x, obj.position.y, 0.0))
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    if isinstance(obj, Line):
        if getattr(obj, "style_name", None) == "Сплошная волнистая":
            entity = _export_wavy_line_as_spline(msp, obj)
            apply_common_entity_attributes(entity, _linetype_override(obj, linetype_name="CONTINUOUS"), layer)
            return 1
        entity = msp.add_line((obj.start.x, obj.start.y, 0.0), (obj.end.x, obj.end.y, 0.0))
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    if isinstance(obj, Circle):
        entity = msp.add_circle((obj.center.x, obj.center.y, 0.0), obj.radius)
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    if isinstance(obj, Arc):
        end_angle = obj.start_angle + obj.span_angle
        entity = msp.add_arc((obj.center.x, obj.center.y, 0.0), obj.radius, obj.start_angle, end_angle)
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    if isinstance(obj, Ellipse):
        major_axis = (obj.radius_x, 0.0, 0.0)
        ratio = 0.0 if obj.radius_x == 0 else obj.radius_y / obj.radius_x
        entity = msp.add_ellipse((obj.center.x, obj.center.y, 0.0), major_axis=major_axis, ratio=ratio)
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    if isinstance(obj, Polygon):
        points = [(vertex.x, vertex.y) for vertex in obj.vertices]
        entity = msp.add_lwpolyline(points, close=True)
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    if isinstance(obj, Rectangle):
        return _export_rectangle(msp, obj, layer, report)

    if isinstance(obj, Spline):
        entity = _export_spline(msp, obj)
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    report["warnings"].append(f"Неизвестный объект {type(obj).__name__} пропущен при экспорте")
    return 0


def _export_rectangle(msp, obj: Rectangle, layer: LayerRecord, report: dict) -> int:
    points = [(corner.x, corner.y) for corner in obj.corners]
    if obj.corner_radius <= 0 and obj.chamfer_size <= 0:
        entity = msp.add_lwpolyline(points, close=True)
        apply_common_entity_attributes(entity, obj, layer)
        return 1

    if obj.chamfer_size > 0:
        x1, y1 = obj.left, obj.bottom
        x2, y2 = obj.right, obj.top
        c = min(obj.chamfer_size, obj.width / 2, obj.height / 2)
        chamfer_points = [
            (x1 + c, y1),
            (x2 - c, y1),
            (x2, y1 + c),
            (x2, y2 - c),
            (x2 - c, y2),
            (x1 + c, y2),
            (x1, y2 - c),
            (x1, y1 + c),
        ]
        entity = msp.add_lwpolyline(chamfer_points, close=True)
        apply_common_entity_attributes(entity, obj, layer)
        report["decomposed_objects"] += 1
        return 1

    written = 0
    r = min(obj.corner_radius, obj.width / 2, obj.height / 2)
    corners = [
        ((obj.left + r, obj.bottom), (obj.right - r, obj.bottom)),
        ((obj.right, obj.bottom + r), (obj.right, obj.top - r)),
        ((obj.right - r, obj.top), (obj.left + r, obj.top)),
        ((obj.left, obj.top - r), (obj.left, obj.bottom + r)),
    ]

    for start, end in corners:
        entity = msp.add_line((start[0], start[1], 0.0), (end[0], end[1], 0.0))
        apply_common_entity_attributes(entity, obj, layer)
        written += 1

    arc_specs = [
        ((obj.right - r, obj.bottom + r), 270, 360),
        ((obj.right - r, obj.top - r), 0, 90),
        ((obj.left + r, obj.top - r), 90, 180),
        ((obj.left + r, obj.bottom + r), 180, 270),
    ]
    for center, start_angle, end_angle in arc_specs:
        entity = msp.add_arc((center[0], center[1], 0.0), r, start_angle, end_angle)
        apply_common_entity_attributes(entity, obj, layer)
        written += 1

    report["decomposed_objects"] += 1
    return written


def _export_spline(msp, obj: Spline):
    if obj.control_points and obj.knots:
        control_points = [(point.x, point.y, 0.0) for point in obj.control_points]
        if obj.weights:
            entity = msp.add_rational_spline(control_points, obj.weights, degree=obj.degree, knots=obj.knots)
        else:
            entity = msp.add_open_spline(control_points, degree=obj.degree, knots=obj.knots)
        return entity

    fit_points = obj.fit_points or obj.control_points
    return msp.add_spline([(point.x, point.y, 0.0) for point in fit_points], degree=max(2, obj.degree))


def _export_wavy_line_as_spline(msp, obj: Line):
    dx = obj.end.x - obj.start.x
    dy = obj.end.y - obj.start.y
    length = math.hypot(dx, dy)
    if length <= 1e-6:
        return msp.add_line((obj.start.x, obj.start.y, 0.0), (obj.end.x, obj.end.y, 0.0))

    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux

    # Экспортируем волнистую линию как одну геометрическую кривую, а не как custom linetype.
    periods = max(3, min(12, int(round(length / 25.0)) or 1))
    amplitude = max(length * 0.03, 0.75)
    sample_count = max(25, periods * 16)
    step = length / sample_count
    fit_points = []

    for index in range(sample_count + 1):
        t = step * index
        if index == sample_count:
            t = length
        offset = amplitude * math.sin(2.0 * math.pi * periods * (t / length))
        px = obj.start.x + ux * t + nx * offset
        py = obj.start.y + uy * t + ny * offset
        fit_points.append((px, py, 0.0))

    return msp.add_spline(fit_points, degree=3)


def _linetype_override(obj, linetype_name: str):
    proxy = SimpleNamespace(**obj.__dict__)
    proxy.linetype_name = linetype_name
    return proxy


def _ensure_layers(doc, scene, report):
    if not scene.layers:
        scene.ensure_layer("0")

    for name, layer in scene.layers.items():
        if name in doc.layers:
            table_layer = doc.layers.get(name)
        else:
            table_layer = doc.layers.new(name)
            report["created_layers"].append(name)

        table_layer.dxf.color = int(layer.aci_color if layer.aci_color is not None else 7)
        table_layer.dxf.linetype = layer.linetype_name or map_style_to_linetype(layer.display_style_name)
        if layer.true_color is not None:
            table_layer.dxf.true_color = int(layer.true_color)
        if layer.lineweight is not None:
            table_layer.dxf.lineweight = int(layer.lineweight)
        table_layer.dxf.flags = int(layer.flags)


def _ensure_linetypes(doc, scene, report):
    required = set()

    for layer in scene.layers.values():
        if layer.linetype_name:
            required.add(layer.linetype_name)
        elif layer.display_style_name:
            required.add(map_style_to_linetype(layer.display_style_name))

    for obj in scene.objects:
        linetype_name = getattr(obj, "linetype_name", None)
        if linetype_name and linetype_name not in {"BYLAYER", "BYBLOCK"}:
            required.add(linetype_name)
        elif getattr(obj, "style_name", None):
            required.add(map_style_to_linetype(obj.style_name))

    custom_patterns = {
        # AutoCAD-compatible names used by downstream CAD systems. The exact
        # AutoCAD definitions are complex shape-based linetypes, so here we keep
        # the standard names and provide safe simple surrogates for interoperability.
        "HIDDEN": ([0.6, 0.5, -0.1], "Hidden __ __ __ __"),
        "ZIGZAG": ([1.2, 0.3, -0.15, 0.3, -0.15, 0.3, -0.15], "Zigzag surrogate"),
    }

    existing = {linetype.dxf.name.upper() for linetype in doc.linetypes}
    for name in sorted(required):
        normalized = str(name).upper()
        if normalized in {"BYLAYER", "BYBLOCK"} or normalized in existing:
            continue
        pattern = custom_patterns.get(normalized)
        if pattern is None:
            report["warnings"].append(f"Неизвестный linetype {name} не создан автоматически")
            continue
        values, description = pattern
        doc.linetypes.add(normalized, values, description=description)
        report["created_linetypes"].append(normalized)


def _load_ezdxf():
    try:
        import ezdxf
    except ImportError as exc:
        raise RuntimeError("Для работы с DXF установите зависимость 'ezdxf'.") from exc
    return ezdxf
