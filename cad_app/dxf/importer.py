"""
Импорт DXF файлов во внутреннюю модель приложения.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..core.geometry import (
    Arc,
    Circle,
    Ellipse,
    Line,
    Point,
    PointEntity,
    Polygon,
    PolygonType,
    Rectangle,
    Spline,
)
from ..core.layers import LayerRecord, default_layer
from .mapping import (
    display_style_for_layer,
    entity_metadata_to_dict,
    style_from_dxf_attributes,
)

Z_TOLERANCE = 1e-6
MAX_BLOCK_DEPTH = 8
MIN_SPLINE_PROMOTION_POINTS = 8


@dataclass
class ImportCandidate:
    """Промежуточное представление DXF-сущности перед импортом в сцену."""

    entity: object
    entity_type: str
    block_context: list[str]
    sequence: int
    is_virtual: bool = False
    from_insert: bool = False
    forced_style_name: str | None = None
    forced_style_reason: str | None = None


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
        "promoted_count": 0,
        "promoted_details": [],
        "promoted_summary": {},
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
    flattened: list[ImportCandidate] = []
    sequence = [0]

    for entity in doc.modelspace():
        _flatten_entity(
            entity,
            report,
            flattened,
            block_context=[],
            depth=0,
            from_insert=False,
            sequence=sequence,
        )

    _apply_tflex_r14_continuous_style_fallback(doc, flattened, report)

    tolerance = _compute_import_tolerance(document_meta)
    objects = _import_candidates(flattened, layers, report, Vec3=Vec3, tolerance=tolerance)

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


def _flatten_entity(entity, report, candidates: list[ImportCandidate], block_context, depth: int, from_insert: bool, sequence):
    entity_type = entity.dxftype()
    if depth > MAX_BLOCK_DEPTH:
        _skip_entity(report, entity, "Превышена глубина вложенности блоков", block_context)
        return

    if getattr(entity.dxf, "paperspace", 0):
        _skip_entity(report, entity, "paperspace layout не поддерживается", block_context)
        return

    if entity_type == "INSERT":
        try:
            virtual_entities = list(entity.virtual_entities())
        except Exception as exc:
            _skip_entity(report, entity, f"Не удалось раскрыть INSERT: {exc}", block_context)
            return

        block_name = getattr(entity.dxf, "name", "<unnamed>")
        next_context = list(block_context) + [block_name]
        for child in virtual_entities:
            _flatten_entity(
                child,
                report,
                candidates,
                block_context=next_context,
                depth=depth + 1,
                from_insert=True,
                sequence=sequence,
            )
        return

    candidates.append(
        ImportCandidate(
            entity=entity,
            entity_type=entity_type,
            block_context=list(block_context),
            sequence=sequence[0],
            is_virtual=bool(block_context),
            from_insert=from_insert,
        )
    )
    sequence[0] += 1


def _apply_tflex_r14_continuous_style_fallback(doc, candidates: list[ImportCandidate], report):
    """Восстанавливает тонкую sample-линию в старых T-FLEX DXF без lineweight.

    В R14-файлах T-FLEX встречается набор демонстрационных линий, где
    "Сплошная основная" и "Сплошная тонкая" обе записаны как CONTINUOUS без
    group code 370. Стандартного признака толщины там уже нет, поэтому
    fallback включается только для T-FLEX-подобных файлов с именами типов
    линий вида CENTER_PER.../HIDDEN_PER... и только для второй линии первой
    непрерывной группы sample-линий.
    """
    if not _looks_like_tflex_r14_line_sample_doc(doc):
        return

    first_continuous_run: list[ImportCandidate] = []
    for candidate in sorted(candidates, key=lambda item: item.sequence):
        if candidate.entity_type != "LINE":
            if first_continuous_run:
                break
            continue

        metadata = entity_metadata_to_dict(candidate.entity)
        if _is_plain_continuous_entity(metadata):
            first_continuous_run.append(candidate)
            continue

        if first_continuous_run:
            break

    if len(first_continuous_run) < 2:
        return

    thin_candidate = first_continuous_run[1]
    thin_candidate.forced_style_name = "Сплошная тонкая"
    thin_candidate.forced_style_reason = "tflex_r14_continuous_thin_fallback"
    report["warnings"].append(
        "T-FLEX R14 DXF не содержит lineweight для второй CONTINUOUS sample-линии; "
        "она импортирована как 'Сплошная тонкая' по совместимой эвристике."
    )


def _looks_like_tflex_r14_line_sample_doc(doc) -> bool:
    if getattr(doc, "dxfversion", "") != "AC1015":
        return False

    linetype_names = {linetype.dxf.name.upper() for linetype in doc.linetypes}
    return any(re.match(r"^(CENTER|HIDDEN|PHANTOM)_PER", name) for name in linetype_names)


def _is_plain_continuous_entity(metadata: dict) -> bool:
    linetype = str(metadata.get("linetype_name") or "BYLAYER").strip().upper()
    return linetype in {"CONTINUOUS", "BYLAYER", "BYBLOCK"} and metadata.get("lineweight") in {None, -1, -2, -3}


def _import_candidates(candidates: list[ImportCandidate], layers, report, Vec3, tolerance: float):
    imported_items: list[tuple[int, int, object]] = []
    line_candidates: list[ImportCandidate] = []

    for candidate in candidates:
        if candidate.entity_type == "LINE":
            line_candidates.append(candidate)
            continue

        if candidate.entity_type in {"LWPOLYLINE", "POLYLINE"}:
            imported_items.extend(_import_polyline_candidate(candidate, layers, report, Vec3, tolerance))
            continue

        if candidate.entity_type not in {"POINT", "CIRCLE", "ARC", "ELLIPSE", "SPLINE"}:
            _skip_entity(report, candidate.entity, f"Тип {candidate.entity_type} не поддерживается", candidate.block_context)
            continue

        try:
            obj = _import_direct_candidate(candidate, layers, promotion_kind="direct", Vec3=Vec3)
        except UnsupportedDXFEntity as exc:
            _skip_entity(report, candidate.entity, str(exc), candidate.block_context)
            continue
        if obj is not None:
            imported_items.append((candidate.sequence, 0, obj))

    imported_items.extend(_promote_line_candidates(line_candidates, layers, report, tolerance))
    imported_items.sort(key=lambda item: (item[0], item[1]))
    return [obj for _, _, obj in imported_items]


def _import_direct_candidate(candidate: ImportCandidate, layers, promotion_kind: str, Vec3, extra_flags=None):
    entity = candidate.entity

    try:
        if candidate.entity_type == "POINT":
            obj = _import_point(entity, layers, Vec3)
        elif candidate.entity_type == "LINE":
            obj = _import_line(entity, layers)
        elif candidate.entity_type == "CIRCLE":
            obj = _import_circle(entity, layers, Vec3)
        elif candidate.entity_type == "ARC":
            obj = _import_arc(entity, layers, Vec3)
        elif candidate.entity_type == "ELLIPSE":
            obj = _import_ellipse(entity, layers)
        elif candidate.entity_type == "SPLINE":
            obj = _import_spline(entity, layers)
        else:
            return None
    except UnsupportedDXFEntity:
        raise
    except Exception as exc:
        raise UnsupportedDXFEntity(str(exc)) from exc

    _apply_candidate_metadata(obj, candidate, layers, promotion_kind=promotion_kind, extra_flags=extra_flags)
    return obj


def _import_polyline_candidate(candidate: ImportCandidate, layers, report, Vec3, tolerance: float):
    entity = candidate.entity
    sequence = candidate.sequence

    try:
        points, bulges, closed = _extract_polyline_geometry(entity, Vec3)
    except UnsupportedDXFEntity as exc:
        _skip_entity(report, entity, str(exc), candidate.block_context)
        return []

    if not points:
        _skip_entity(report, entity, "POLYLINE/LWPOLYLINE без вершин", candidate.block_context)
        return []

    if any(abs(bulge) > 1e-9 for bulge in bulges):
        return _decompose_polyline_candidate(candidate, layers, report, Vec3)

    metadata = entity_metadata_to_dict(entity)

    rectangle = _try_build_rectangle_from_vertices(points, closed, tolerance, metadata.get("layer_name", "0"))
    if rectangle is not None:
        _apply_candidate_metadata(rectangle, candidate, layers, promotion_kind="exact_promotion")
        _record_promotion(
            report,
            rectangle,
            source="polyline",
            reason="closed polyline распознана как Rectangle",
            confidence="exact",
        )
        return [(sequence, 0, rectangle)]

    polygon = _try_build_polygon_from_vertices(points, closed, tolerance)
    if polygon is not None:
        _apply_candidate_metadata(polygon, candidate, layers, promotion_kind="exact_promotion")
        _record_promotion(
            report,
            polygon,
            source="polyline",
            reason="closed polyline распознана как Polygon",
            confidence="exact",
        )
        return [(sequence, 0, polygon)]

    spline = _try_build_spline_from_vertices(points, closed, tolerance)
    if spline is not None:
        _apply_candidate_metadata(spline, candidate, layers, promotion_kind="heuristic_promotion")
        _record_promotion(
            report,
            spline,
            source="polyline",
            reason="open polyline эвристически распознана как Spline",
            confidence="heuristic",
        )
        return [(sequence, 0, spline)]

    return _decompose_polyline_candidate(candidate, layers, report, Vec3)


def _decompose_polyline_candidate(candidate: ImportCandidate, layers, report, Vec3):
    try:
        children = list(candidate.entity.virtual_entities())
    except Exception as exc:
        _skip_entity(report, candidate.entity, f"Не удалось разложить сущность: {exc}", candidate.block_context)
        return []

    imported_items: list[tuple[int, int, object]] = []
    for index, child in enumerate(children):
        child_candidate = ImportCandidate(
            entity=child,
            entity_type=child.dxftype(),
            block_context=list(candidate.block_context),
            sequence=candidate.sequence,
            is_virtual=True,
            from_insert=candidate.from_insert,
            forced_style_name=candidate.forced_style_name,
            forced_style_reason=candidate.forced_style_reason,
        )
        try:
            obj = _import_direct_candidate(
                child_candidate,
                layers,
                promotion_kind="decomposed",
                Vec3=Vec3,
                extra_flags=["decomposed_from_polyline"],
            )
        except UnsupportedDXFEntity as exc:
            _skip_entity(report, child, str(exc), child_candidate.block_context)
            continue

        if obj is not None:
            imported_items.append((candidate.sequence, index, obj))

    return imported_items


def _promote_line_candidates(line_candidates: list[ImportCandidate], layers, report, tolerance: float):
    imported_items: list[tuple[int, int, object]] = []
    consumed_ids: set[int] = set()

    candidates_by_signature: dict[tuple, list[ImportCandidate]] = defaultdict(list)
    for candidate in line_candidates:
        metadata = entity_metadata_to_dict(candidate.entity)
        layer = layers.get(metadata["layer_name"])
        style_name = candidate.forced_style_name or style_from_dxf_attributes(
            metadata["linetype_name"],
            metadata["lineweight"],
            layer,
            display_style_for_layer(layer),
        )
        if style_name in {"Сплошная волнистая", "Сплошная с изломами"}:
            continue
        candidates_by_signature[_line_candidate_signature(candidate)].append(candidate)

    for grouped_candidates in candidates_by_signature.values():
        for component in _find_closed_line_components(grouped_candidates, tolerance):
            ordered_points = _ordered_cycle_points(component, tolerance)
            if ordered_points is None:
                continue

            metadata = entity_metadata_to_dict(component[0].entity)
            layer_name = metadata.get("layer_name", "0")
            rectangle = _try_build_rectangle_from_vertices(ordered_points, True, tolerance, layer_name)
            if rectangle is not None:
                _apply_candidate_metadata(rectangle, component[0], layers, promotion_kind="exact_promotion")
                rectangle.import_flags.extend(["promoted_from_line_chain"])
                _record_promotion(
                    report,
                    rectangle,
                    source="line-chain",
                    reason="Замкнутая цепочка линий распознана как Rectangle",
                    confidence="exact",
                )
                for candidate in component:
                    consumed_ids.add(id(candidate))
                imported_items.append((min(candidate.sequence for candidate in component), 0, rectangle))
                continue

            polygon = _try_build_polygon_from_vertices(ordered_points, True, tolerance)
            if polygon is not None:
                _apply_candidate_metadata(polygon, component[0], layers, promotion_kind="exact_promotion")
                polygon.import_flags.extend(["promoted_from_line_chain"])
                _record_promotion(
                    report,
                    polygon,
                    source="line-chain",
                    reason="Замкнутая цепочка линий распознана как Polygon",
                    confidence="exact",
                )
                for candidate in component:
                    consumed_ids.add(id(candidate))
                imported_items.append((min(candidate.sequence for candidate in component), 0, polygon))

    for candidate in line_candidates:
        if id(candidate) in consumed_ids:
            continue
        try:
            obj = _import_direct_candidate(candidate, layers, promotion_kind="direct", Vec3=None)
        except UnsupportedDXFEntity as exc:
            _skip_entity(report, candidate.entity, str(exc), candidate.block_context)
            continue
        if obj is not None:
            imported_items.append((candidate.sequence, 0, obj))

    return imported_items


def _find_closed_line_components(candidates: list[ImportCandidate], tolerance: float):
    if len(candidates) < 3:
        return []

    key_to_candidates: dict[tuple[int, int], list[ImportCandidate]] = defaultdict(list)
    candidate_vertices: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {}
    key_to_point: dict[tuple[int, int], Point] = {}

    for candidate in candidates:
        start = Point(float(candidate.entity.dxf.start.x), float(candidate.entity.dxf.start.y))
        end = Point(float(candidate.entity.dxf.end.x), float(candidate.entity.dxf.end.y))
        key1 = _point_key(start, tolerance)
        key2 = _point_key(end, tolerance)
        candidate_vertices[id(candidate)] = (key1, key2)
        key_to_candidates[key1].append(candidate)
        key_to_candidates[key2].append(candidate)
        key_to_point.setdefault(key1, start)
        key_to_point.setdefault(key2, end)

    remaining = {id(candidate): candidate for candidate in candidates}
    components = []

    while remaining:
        _, seed = remaining.popitem()
        stack = [seed]
        component = [seed]

        while stack:
            current = stack.pop()
            for vertex_key in candidate_vertices[id(current)]:
                for neighbour in key_to_candidates[vertex_key]:
                    neighbour_id = id(neighbour)
                    if neighbour_id in remaining:
                        stack.append(neighbour)
                        component.append(neighbour)
                        remaining.pop(neighbour_id)

        degree_count: dict[tuple[int, int], int] = defaultdict(int)
        unique_vertices = set()
        for candidate in component:
            v1, v2 = candidate_vertices[id(candidate)]
            degree_count[v1] += 1
            degree_count[v2] += 1
            unique_vertices.update((v1, v2))

        if len(component) >= 3 and len(unique_vertices) == len(component) and all(degree == 2 for degree in degree_count.values()):
            components.append(component)

    return components


def _ordered_cycle_points(component: list[ImportCandidate], tolerance: float):
    key_to_candidates: dict[tuple[int, int], list[ImportCandidate]] = defaultdict(list)
    endpoints: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {}
    key_to_point: dict[tuple[int, int], Point] = {}

    for candidate in component:
        start = Point(float(candidate.entity.dxf.start.x), float(candidate.entity.dxf.start.y))
        end = Point(float(candidate.entity.dxf.end.x), float(candidate.entity.dxf.end.y))
        start_key = _point_key(start, tolerance)
        end_key = _point_key(end, tolerance)
        endpoints[id(candidate)] = (start_key, end_key)
        key_to_candidates[start_key].append(candidate)
        key_to_candidates[end_key].append(candidate)
        key_to_point.setdefault(start_key, start)
        key_to_point.setdefault(end_key, end)

    start_key = min(key_to_point.keys())
    current_key = start_key
    previous_candidate_id = None
    points = [key_to_point[start_key]]
    used_candidates: set[int] = set()

    while True:
        options = [
            candidate
            for candidate in key_to_candidates[current_key]
            if id(candidate) != previous_candidate_id and id(candidate) not in used_candidates
        ]
        if not options:
            return None

        candidate = options[0]
        used_candidates.add(id(candidate))
        key1, key2 = endpoints[id(candidate)]
        next_key = key2 if key1 == current_key else key1
        points.append(key_to_point[next_key])

        if next_key == start_key:
            break

        current_key = next_key
        previous_candidate_id = id(candidate)

        if len(used_candidates) > len(component):
            return None

    if len(used_candidates) != len(component):
        return None

    return points[:-1]


def _try_build_rectangle_from_vertices(points: list[Point], closed: bool, tolerance: float, layer_name: str):
    if not closed or len(points) != 4:
        return None

    xs = sorted(point.x for point in points)
    ys = sorted(point.y for point in points)
    if not (
        math.isclose(xs[0], xs[1], abs_tol=tolerance)
        and math.isclose(xs[2], xs[3], abs_tol=tolerance)
        and math.isclose(ys[0], ys[1], abs_tol=tolerance)
        and math.isclose(ys[2], ys[3], abs_tol=tolerance)
    ):
        return None

    min_x = (xs[0] + xs[1]) / 2.0
    max_x = (xs[2] + xs[3]) / 2.0
    min_y = (ys[0] + ys[1]) / 2.0
    max_y = (ys[2] + ys[3]) / 2.0
    if math.isclose(min_x, max_x, abs_tol=tolerance) or math.isclose(min_y, max_y, abs_tol=tolerance):
        return None

    expected = {
        (_point_key(Point(min_x, min_y), tolerance)),
        (_point_key(Point(max_x, min_y), tolerance)),
        (_point_key(Point(max_x, max_y), tolerance)),
        (_point_key(Point(min_x, max_y), tolerance)),
    }
    actual = {_point_key(point, tolerance) for point in points}
    if expected != actual:
        return None

    rectangle = Rectangle(Point(min_x, min_y), Point(max_x, max_y))
    rectangle.layer_name = layer_name
    return rectangle


def _try_build_polygon_from_vertices(points: list[Point], closed: bool, tolerance: float):
    if not closed or len(points) < 3:
        return None

    center = Point(
        sum(point.x for point in points) / len(points),
        sum(point.y for point in points) / len(points),
    )
    radii = [center.distance_to(point) for point in points]
    average_radius = sum(radii) / len(radii)
    if average_radius <= tolerance:
        return None

    max_radius_delta = max(abs(radius - average_radius) for radius in radii)
    if max_radius_delta > max(tolerance * 5.0, average_radius * 0.03):
        return None

    side_lengths = [points[i].distance_to(points[(i + 1) % len(points)]) for i in range(len(points))]
    average_side = sum(side_lengths) / len(side_lengths)
    if average_side <= tolerance:
        return None

    max_side_delta = max(abs(length - average_side) for length in side_lengths)
    if max_side_delta > max(tolerance * 5.0, average_side * 0.03):
        return None

    rotation = math.degrees(center.angle_to(points[0]))
    return Polygon(center, average_radius, num_sides=len(points), polygon_type=PolygonType.INSCRIBED, rotation=rotation)


def _try_build_spline_from_vertices(points: list[Point], closed: bool, tolerance: float):
    if closed or len(points) < MIN_SPLINE_PROMOTION_POINTS:
        return None

    segment_vectors = []
    segment_lengths = []
    for start, end in zip(points, points[1:]):
        dx = end.x - start.x
        dy = end.y - start.y
        length = math.hypot(dx, dy)
        if length <= tolerance:
            return None
        segment_vectors.append((dx / length, dy / length))
        segment_lengths.append(length)

    total_length = sum(segment_lengths)
    direct_length = points[0].distance_to(points[-1])
    if total_length <= tolerance or direct_length <= tolerance:
        return None

    if total_length / direct_length < 1.03:
        return None

    turns = []
    sharp_turns = 0
    for first, second in zip(segment_vectors, segment_vectors[1:]):
        dot = max(-1.0, min(1.0, first[0] * second[0] + first[1] * second[1]))
        turn_deg = math.degrees(math.acos(dot))
        turns.append(turn_deg)
        if turn_deg > 45.0:
            sharp_turns += 1

    if not turns:
        return None

    if max(turns) > 85.0:
        return None

    if sharp_turns > max(1, len(turns) // 10):
        return None

    if sum(turns) / len(turns) < 2.0:
        return None

    return Spline(control_points=[point.copy() for point in points], closed=False)


def _extract_polyline_geometry(entity, Vec3):
    entity_type = entity.dxftype()
    points: list[Point] = []
    bulges: list[float] = []

    if entity_type == "LWPOLYLINE":
        if not _is_xy_extrusion(getattr(entity.dxf, "extrusion", None)):
            raise UnsupportedDXFEntity("LWPOLYLINE в произвольной OCS-плоскости не поддерживается")
        elevation = getattr(entity.dxf, "elevation", 0.0)
        if isinstance(elevation, (tuple, list)):
            elevation = elevation[-1]
        if abs(float(elevation)) > Z_TOLERANCE:
            raise UnsupportedDXFEntity("LWPOLYLINE вне плоскости XY")

        for x, y, bulge in entity.get_points("xyb"):
            points.append(Point(float(x), float(y)))
            bulges.append(float(bulge))
        return points, bulges, bool(entity.closed)

    if entity_type == "POLYLINE":
        if not getattr(entity, "is_2d_polyline", False):
            raise UnsupportedDXFEntity("Поддерживаются только 2D POLYLINE")

        for vertex in entity.vertices:
            location = vertex.dxf.location
            if abs(float(location.z)) > Z_TOLERANCE:
                raise UnsupportedDXFEntity("POLYLINE вне плоскости XY")
            points.append(Point(float(location.x), float(location.y)))
            bulges.append(float(getattr(vertex.dxf, "bulge", 0.0)))

        return points, bulges, bool(entity.is_closed)

    raise UnsupportedDXFEntity(f"Тип {entity_type} не является POLYLINE")


def _import_point(entity, layers, Vec3):
    location = _to_wcs_point(entity.ocs(), entity.dxf.location, Vec3)
    _ensure_xy_point(location, "POINT вне плоскости XY")
    return PointEntity(Point(location.x, location.y))


def _import_line(entity, layers):
    start = Point(float(entity.dxf.start.x), float(entity.dxf.start.y))
    end = Point(float(entity.dxf.end.x), float(entity.dxf.end.y))
    if abs(float(entity.dxf.start.z)) > Z_TOLERANCE or abs(float(entity.dxf.end.z)) > Z_TOLERANCE:
        raise UnsupportedDXFEntity("LINE с Z-координатой не поддерживается")
    return Line(start, end)


def _import_circle(entity, layers, Vec3):
    if not _is_xy_extrusion(getattr(entity.dxf, "extrusion", None)):
        raise UnsupportedDXFEntity("CIRCLE в произвольной OCS-плоскости не поддерживается")
    center = _to_wcs_point(entity.ocs(), entity.dxf.center, Vec3)
    _ensure_xy_point(center, "CIRCLE вне плоскости XY")
    return Circle(Point(center.x, center.y), float(entity.dxf.radius))


def _import_arc(entity, layers, Vec3):
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

    minor_len = abs(major_len * ratio)
    major_angle = math.degrees(math.atan2(float(major_axis.y), float(major_axis.x)))

    if major_len >= minor_len:
        radius_x = major_len
        radius_y = minor_len
        rotation = major_angle
    else:
        radius_x = minor_len
        radius_y = major_len
        rotation = major_angle - 90.0

    return Ellipse(Point(float(center.x), float(center.y)), radius_x, radius_y, rotation=rotation)


def _import_spline(entity, layers):
    control_points = [Point(float(p[0]), float(p[1])) for p in entity.control_points]
    fit_points = [Point(float(p[0]), float(p[1])) for p in entity.fit_points]

    points_to_check = control_points or fit_points
    if not points_to_check:
        raise UnsupportedDXFEntity("SPLINE без точек не поддерживается")

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
            display_style_name=style_from_dxf_attributes(
                getattr(layer.dxf, "linetype", "CONTINUOUS"),
                getattr(layer.dxf, "lineweight", None),
                None,
            ),
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


def _apply_candidate_metadata(obj, candidate: ImportCandidate, layers, promotion_kind: str, extra_flags=None):
    metadata = entity_metadata_to_dict(candidate.entity)
    layer = layers.get(metadata["layer_name"])

    obj.style_name = candidate.forced_style_name or style_from_dxf_attributes(
        metadata["linetype_name"],
        metadata["lineweight"],
        layer,
        display_style_for_layer(layer),
    )
    obj.layer_name = metadata["layer_name"]
    obj.aci_color = metadata["aci_color"]
    obj.true_color = metadata["true_color"]
    obj.linetype_name = metadata["linetype_name"]
    obj.lineweight = metadata["lineweight"]
    obj.imported_from_dxf = True
    obj.source_handle = metadata["source_handle"]
    obj.source_entity_type = metadata["source_entity_type"]
    obj.source_linetype_name = metadata["linetype_name"]
    obj.promotion_kind = promotion_kind
    obj.import_flags = list(metadata["import_flags"])

    if candidate.from_insert:
        obj.import_flags.append("from_insert")
    if candidate.is_virtual:
        obj.import_flags.append("virtual_entity")
    if candidate.block_context:
        obj.import_flags.append(f"block_context:{'/'.join(candidate.block_context)}")
    if candidate.forced_style_reason:
        obj.import_flags.append(candidate.forced_style_reason)
    if extra_flags:
        obj.import_flags.extend(extra_flags)


def _record_promotion(report, obj, source: str, reason: str, confidence: str):
    report["promoted_count"] += 1
    key = f"{obj.__class__.__name__}:{reason}"
    report["promoted_summary"][key] = report["promoted_summary"].get(key, 0) + 1
    report["promoted_details"].append(
        {
            "object_type": obj.__class__.__name__,
            "source": source,
            "reason": reason,
            "confidence": confidence,
            "layer": getattr(obj, "layer_name", "0"),
            "source_handle": getattr(obj, "source_handle", None),
            "source_entity_type": getattr(obj, "source_entity_type", None),
        }
    )


def _line_candidate_signature(candidate: ImportCandidate):
    metadata = entity_metadata_to_dict(candidate.entity)
    return (
        metadata["layer_name"],
        metadata["aci_color"],
        metadata["true_color"],
        metadata["linetype_name"],
        metadata["lineweight"],
        candidate.forced_style_name,
        tuple(candidate.block_context),
    )


def _point_key(point: Point, tolerance: float):
    scale = max(tolerance, 1e-9)
    return (round(point.x / scale), round(point.y / scale))


def _compute_import_tolerance(document_meta: dict) -> float:
    extmin = document_meta.get("extmin")
    extmax = document_meta.get("extmax")
    if extmin and extmax and len(extmin) >= 2 and len(extmax) >= 2:
        span_x = abs(float(extmax[0]) - float(extmin[0]))
        span_y = abs(float(extmax[1]) - float(extmin[1]))
        span = max(span_x, span_y)
        if 0 < span < 1e12:
            return max(1e-6, span * 1e-6)
    return 1e-5


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
