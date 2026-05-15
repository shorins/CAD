"""
Экспорт внутренней сцены приложения в DXF.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from pathlib import Path

from ..core.geometry import (
    Arc, Circle, Ellipse, Line, PointEntity, Polygon, Rectangle, Spline,
    DimensionBase, LinearDimension, RadialDimension, DiameterDimension, AngularDimension,
)
from ..core.geometry.dimensions import global_dimension_text_height_mm, global_dimension_arrow_size_mm
from ..core.layers import LayerRecord, default_layer
from .mapping import DEFAULT_DXF_VERSION, apply_common_entity_attributes, map_style_to_linetype


# ---------------------------------------------------------------------------
#  Dimension style name used for all exported dimensions
# ---------------------------------------------------------------------------
_DIM_STYLE_NAME = "CAD_DIM"


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
    _ensure_dimension_style(doc)

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

    if isinstance(obj, DimensionBase):
        return _export_dimension(doc, msp, obj, scene, layer, report)

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
        if obj.radius_x >= obj.radius_y:
            major_length = obj.radius_x
            minor_length = obj.radius_y
            major_angle = math.radians(obj.rotation)
        else:
            major_length = obj.radius_y
            minor_length = obj.radius_x
            major_angle = math.radians(obj.rotation + 90.0)

        major_axis = (
            major_length * math.cos(major_angle),
            major_length * math.sin(major_angle),
            0.0,
        )
        ratio = 0.0 if major_length == 0 else minor_length / major_length
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


# ---------------------------------------------------------------------------
#  Dimension export
# ---------------------------------------------------------------------------

def _ensure_dimension_style(doc):
    """Создаёт единый DIMSTYLE для всех экспортируемых размеров."""
    if _DIM_STYLE_NAME in doc.dimstyles:
        return
    text_height = global_dimension_text_height_mm()
    arrow_size = global_dimension_arrow_size_mm()
    doc.dimstyles.new(
        _DIM_STYLE_NAME,
        dxfattribs={
            "dimtxt": text_height,       # высота текста
            "dimasz": arrow_size,        # размер стрелки
            "dimexe": 2.5,               # выступ выносной линии за размерную
            "dimexo": 0.0,               # зазор от объекта до выносной
            "dimgap": text_height * 0.1, # зазор текста
            "dimtad": 1,                 # текст над линией
            "dimtih": 0,                 # текст повторяет наклон
            "dimtoh": 0,                 # текст повторяет наклон (снаружи)
            "dimdec": 2,                 # кол-во десятичных знаков
        },
    )


def _export_dimension(doc, msp, obj: DimensionBase, scene, layer: LayerRecord, report: dict) -> int:
    """Экспортирует размерный объект как DXF DIMENSION entity."""
    layer_name = getattr(obj, "layer_name", "0") or "0"
    dxfattribs = {"layer": layer_name}

    try:
        if isinstance(obj, LinearDimension):
            return _export_linear_dimension(msp, obj, scene, dxfattribs, report)
        if isinstance(obj, RadialDimension):
            return _export_radial_dimension(msp, obj, scene, dxfattribs, report)
        if isinstance(obj, DiameterDimension):
            return _export_diameter_dimension(msp, obj, scene, dxfattribs, report)
        if isinstance(obj, AngularDimension):
            return _export_angular_dimension(msp, obj, scene, dxfattribs, report)
    except Exception as exc:
        report["warnings"].append(
            f"Ошибка экспорта размера {type(obj).__name__}: {exc}"
        )
        return 0

    report["warnings"].append(
        f"Неизвестный тип размера {type(obj).__name__} пропущен при DXF-экспорте"
    )
    return 0


def _resolve_dim_points(obj, scene, anchor_names: list[str]) -> list | None:
    """Извлекает и разрешает точки из якорей размера.

    Возвращает список точек (x, y, 0) или None если не удалось.
    """
    points = []
    for name in anchor_names:
        anchor = getattr(obj, name, None)
        if anchor is None:
            return None
        pt = obj._resolve_anchor(scene, anchor)
        if pt is None:
            return None
        points.append((pt.x, pt.y, 0.0))
    return points


def _dim_text_override(obj: DimensionBase) -> str:
    """Возвращает строку text override для DXF DIMENSION.

    '<>' означает что CAD покажет вычисленное значение.
    """
    native_prefix = ""
    if isinstance(obj, RadialDimension):
        native_prefix = "R"
    elif isinstance(obj, DiameterDimension):
        native_prefix = "Ø"

    prefix = obj.text_prefix or ""
    suffix = obj.text_suffix or ""
    
    # Заменяем символ диаметра на DXF-код
    prefix_dxf = prefix.replace("Ø", "%%c")
    suffix_dxf = suffix.replace("Ø", "%%c")

    if obj.text_override:
        override_dxf = obj.text_override.replace("Ø", "%%c")
        return f"{prefix_dxf}{override_dxf}{suffix_dxf}"
    
    if prefix == native_prefix:
        # CAD сам подставит R или Ø вместо <>
        if suffix:
            return f"<>{suffix_dxf}"
        return "<>"
    else:
        # Если префикс не совпадает с нативным (например, убрали 'R' или заменили на 'Ø'),
        # использование <> приведёт к двойному префиксу (например, RØ50) или неудаляемому R.
        # В таком случае вынужденно отдаём хардкод строку, чтобы перебить нативное поведение.
        display = obj.format_measurement(obj.measured_value_cache)
        return display.replace("Ø", "%%c")


def _export_linear_dimension(msp, obj: LinearDimension, scene, dxfattribs: dict, report: dict) -> int:
    """Экспортирует линейный размер (aligned / horizontal / vertical)."""
    points = _resolve_dim_points(obj, scene, ["anchor1", "anchor2"])
    if not points:
        report["warnings"].append("LinearDimension: не удалось разрешить точки привязки")
        return 0

    p1, p2 = points[0], points[1]

    # Определяем положение размерной линии из layout_state
    text_pos = obj.layout_state.get("text_position")
    dim_line_pos = None
    segments = obj.layout_state.get("segments", [])
    if segments:
        # Первый сегмент — это размерная линия (ext1 → ext2)
        ext1, ext2 = segments[0]
        mid = ((ext1.x + ext2.x) / 2, (ext1.y + ext2.y) / 2, 0.0)
        dim_line_pos = mid

    text = _dim_text_override(obj)
    override = _make_dim_style_override(obj)

    if obj.mode == "horizontal":
        base = dim_line_pos or (p1[0], p1[1] + 10, 0.0)
        dim = msp.add_linear_dim(
            base=base, p1=p1, p2=p2,
            angle=0,
            text=text,
            dimstyle=_DIM_STYLE_NAME,
            override=override,
            dxfattribs=dxfattribs,
        )
    elif obj.mode == "vertical":
        base = dim_line_pos or (p1[0] + 10, p1[1], 0.0)
        dim = msp.add_linear_dim(
            base=base, p1=p1, p2=p2,
            angle=90,
            text=text,
            dimstyle=_DIM_STYLE_NAME,
            override=override,
            dxfattribs=dxfattribs,
        )
    else:
        # aligned
        # Вычисляем расстояние от p1 до размерной линии
        if dim_line_pos:
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.hypot(dx, dy)
            if length > 1e-9:
                nx, ny = -dy / length, dx / length
                distance = (dim_line_pos[0] - p1[0]) * nx + (dim_line_pos[1] - p1[1]) * ny
            else:
                distance = 10.0
        else:
            distance = 10.0

        dim = msp.add_aligned_dim(
            p1=p1, p2=p2,
            distance=distance,
            text=text,
            dimstyle=_DIM_STYLE_NAME,
            override=override,
            dxfattribs=dxfattribs,
        )

    if text_pos and obj.text_position_override:
        dim.dimension.dxf.text_midpoint = (text_pos.x, text_pos.y, 0.0)
    dim.render()
    return 1


def _export_radial_dimension(msp, obj: RadialDimension, scene, dxfattribs: dict, report: dict) -> int:
    """Экспортирует радиальный размер."""
    points = _resolve_dim_points(obj, scene, ["anchor_center", "anchor_curve"])
    if not points:
        report["warnings"].append("RadialDimension: не удалось разрешить точки привязки")
        return 0

    center, curve = points[0], points[1]
    radius = math.hypot(curve[0] - center[0], curve[1] - center[1])
    if radius <= 1e-9:
        report["warnings"].append("RadialDimension: нулевой радиус")
        return 0

    # Определяем направление размерной линии
    placement = obj._resolve_anchor(scene, obj.dimension_line_anchor)
    if placement:
        dx = placement.x - center[0]
        dy = placement.y - center[1]
        angle = math.degrees(math.atan2(dy, dx))
    else:
        dx = curve[0] - center[0]
        dy = curve[1] - center[1]
        angle = math.degrees(math.atan2(dy, dx))

    # Точка на окружности в направлении размерной линии
    mpoint = (
        center[0] + radius * math.cos(math.radians(angle)),
        center[1] + radius * math.sin(math.radians(angle)),
        0.0,
    )

    text = _dim_text_override(obj)
    override = _make_dim_style_override(obj)

    dim = msp.add_radius_dim(
        center=center,
        mpoint=mpoint,
        text=text,
        dimstyle=_DIM_STYLE_NAME,
        override=override,
        dxfattribs=dxfattribs,
    )
    dim.render()
    return 1


def _export_diameter_dimension(msp, obj: DiameterDimension, scene, dxfattribs: dict, report: dict) -> int:
    """Экспортирует диаметральный размер."""
    points = _resolve_dim_points(obj, scene, ["anchor_center", "anchor_curve"])
    if not points:
        report["warnings"].append("DiameterDimension: не удалось разрешить точки привязки")
        return 0

    center, curve = points[0], points[1]
    radius = math.hypot(curve[0] - center[0], curve[1] - center[1])
    if radius <= 1e-9:
        report["warnings"].append("DiameterDimension: нулевой радиус")
        return 0

    # Определяем направление
    placement = obj._resolve_anchor(scene, obj.dimension_line_anchor)
    if placement:
        dx = placement.x - center[0]
        dy = placement.y - center[1]
        angle = math.degrees(math.atan2(dy, dx))
    else:
        dx = curve[0] - center[0]
        dy = curve[1] - center[1]
        angle = math.degrees(math.atan2(dy, dx))

    mpoint = (
        center[0] + radius * math.cos(math.radians(angle)),
        center[1] + radius * math.sin(math.radians(angle)),
        0.0,
    )

    text = _dim_text_override(obj)
    override = _make_dim_style_override(obj)

    dim = msp.add_diameter_dim(
        center=center,
        mpoint=mpoint,
        text=text,
        dimstyle=_DIM_STYLE_NAME,
        override=override,
        dxfattribs=dxfattribs,
    )
    dim.render()
    return 1


def _export_angular_dimension(msp, obj: AngularDimension, scene, dxfattribs: dict, report: dict) -> int:
    """Экспортирует угловой размер."""
    points = _resolve_dim_points(obj, scene, ["vertex_anchor", "ray1_anchor", "ray2_anchor"])
    if not points:
        report["warnings"].append("AngularDimension: не удалось разрешить точки привязки")
        return 0

    vertex, ray1, ray2 = points[0], points[1], points[2]

    # base — точка на дуге размерной линии, определяющая радиус
    # Также извлекаем фактические p1 и p2, так как CAD мог поменять их местами для отрисовки внутри/снаружи угла
    arc_data = obj.layout_state.get("arc")
    if arc_data:
        arc_center = arc_data["center"]
        arc_radius = arc_data["radius"]
        start_deg = arc_data["start_angle_deg"]
        span_deg = arc_data["span_angle_deg"]
        mid_angle_rad = math.radians(start_deg + span_deg / 2.0)
        base = (
            arc_center.x + arc_radius * math.cos(mid_angle_rad),
            arc_center.y + arc_radius * math.sin(mid_angle_rad),
            0.0,
        )
        # Чтобы выносные линии рисовались правильно (от исходных объектов до размерной линии), 
        # мы должны передать исходные ray1 и ray2 в качестве p1 и p2. 
        # Но если CAD нарисовал угол "с другой стороны", он поменял a1 и a2 местами. 
        # Мы проверяем, соответствует ли start_angle_deg углу луча ray1. Если нет — меняем p1 и p2 местами.
        orig_a1 = math.degrees(math.atan2(ray1[1] - vertex[1], ray1[0] - vertex[0]))
        diff = abs((start_deg % 360) - (orig_a1 % 360))
        if diff > 1e-3 and abs(diff - 360) > 1e-3:
            p1, p2 = ray2, ray1
        else:
            p1, p2 = ray1, ray2
    else:
        # Если нет arc data, используем placement
        placement = obj._resolve_anchor(scene, obj.dimension_line_anchor)
        if placement:
            base = (placement.x, placement.y, 0.0)
        else:
            # Фоллбэк — средняя точка
            base = ((ray1[0] + ray2[0]) / 2, (ray1[1] + ray2[1]) / 2, 0.0)
        p1, p2 = ray1, ray2

    text = _dim_text_override(obj)
    override = _make_dim_style_override(obj)
    override["dimdec"] = obj.precision

    text_pos = obj.layout_state.get("text_position")
    location = (text_pos.x, text_pos.y, 0.0) if text_pos and obj.text_position_override else None

    dim = msp.add_angular_dim_3p(
        base=base,
        center=vertex,
        p1=p1,
        p2=p2,
        text=text,
        dimstyle=_DIM_STYLE_NAME,
        override=override,
        location=location,
        dxfattribs=dxfattribs,
    )
    dim.render()
    return 1


def _make_dim_style_override(obj: DimensionBase) -> dict:
    """Создаёт словарь override для DimStyle на основе параметров объекта."""
    override = {}
    precision = obj.dimension_style.get("precision")
    if precision is not None:
        override["dimdec"] = int(precision)
    return override


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
    """Экспорт сплайна в DXF.

    Для сплайнов с точными DXF-данными (knots/weights) — записываем нативный
    SPLINE, чтобы сохранить математическую точность.

    Для пользовательских сплайнов (Catmull-Rom без knot-вектора) — сэмплируем
    кривую в точки и записываем как LWPOLYLINE.  Это гарантирует, что визуальная
    форма в T-FLEX / AutoCAD / любом другом CAD будет совпадать с тем, что
    пользователь видит на экране.  Передача контрольных точек Catmull-Rom
    в ``add_spline`` как fit-points приводила к тому, что принимающий CAD
    перестраивал B-spline по-своему и форма менялась.
    """
    # --- Точный DXF-сплайн (импортированный с knot-вектором) ----------------
    if obj.is_exact_dxf_spline and obj.control_points and obj.knots:
        control_points = [(point.x, point.y, 0.0) for point in obj.control_points]
        if obj.weights:
            return msp.add_rational_spline(
                control_points, obj.weights,
                degree=obj.degree, knots=obj.knots,
            )
        return msp.add_open_spline(
            control_points, degree=obj.degree, knots=obj.knots,
        )

    # --- Пользовательский (Catmull-Rom) сплайн → полилиния ------------------
    curve_points = obj.get_curve_points()
    if len(curve_points) < 2:
        # Слишком мало точек — записываем как нативный SPLINE-fallback
        pts = obj.fit_points or obj.control_points
        return msp.add_spline(
            [(p.x, p.y, 0.0) for p in pts], degree=max(2, obj.degree),
        )

    polyline_points = [(p.x, p.y) for p in curve_points]
    return msp.add_lwpolyline(polyline_points, close=obj.closed)


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
