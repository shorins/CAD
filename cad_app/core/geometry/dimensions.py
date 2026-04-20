"""
Размерные объекты по ЕСКД / CAD-like behavior.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .base import ControlPoint, GeometricPrimitive, SnapPoint, SnapType
from .point import Point
from ...settings import settings
from ...font_manager import DIMENSION_FONT_MODE_GOST_ITALIC, resolve_dimension_font


SUPPORTED_DIMENSION_LINE_STYLES = (
    "Сплошная тонкая",
    "Штриховая",
    "Штрихпунктирная тонкая",
    "Штрихпунктирная с двумя точками",
)


def default_dimension_style() -> dict:
    return {
        "dimension_line_style_name": "Сплошная тонкая",
        "extension_line_style_name": "Сплошная тонкая",
        "extension_overshoot_mm": 2.0,
        "object_gap_mm": 10.0,
        "baseline_spacing_mm": 7.0,
        "text_gap_mm": 1.0,
        "arrow_type": "closed_filled",
        "precision": 2,
    }


def global_dimension_text_height_mm() -> float:
    dimensions = settings.get("dimensions") or settings.defaults.get("dimensions", {})
    return float(dimensions.get("text_height_mm", 3.5))


def global_dimension_arrow_size_mm() -> float:
    dimensions = settings.get("dimensions") or settings.defaults.get("dimensions", {})
    return float(dimensions.get("arrow_size_mm", 3.5))


def global_dimension_font_spec() -> tuple[str, bool]:
    dimensions = settings.get("dimensions") or settings.defaults.get("dimensions", {})
    mode = str(dimensions.get("font_mode", DIMENSION_FONT_MODE_GOST_ITALIC)).strip()
    return resolve_dimension_font(mode)


@dataclass
class DimensionAnchor:
    mode: str
    object_id: Optional[str] = None
    selector: Optional[str] = None
    cached_point: Optional[Point] = None

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "object_id": self.object_id,
            "selector": self.selector,
            "cached_point": self.cached_point.to_dict() if self.cached_point else None,
        }

    @staticmethod
    def from_dict(data: dict) -> "DimensionAnchor":
        cached = data.get("cached_point")
        return DimensionAnchor(
            mode=data.get("mode", "fixed"),
            object_id=data.get("object_id"),
            selector=data.get("selector"),
            cached_point=Point.from_dict(cached) if cached else None,
        )


class DimensionBase(GeometricPrimitive):
    dimension_type = "dimension"
    text_prefix = ""
    text_suffix = ""

    def __init__(self, style_name: str = "Сплошная тонкая"):
        super().__init__(style_name)
        self.dimension_style = default_dimension_style()
        self.text_override: Optional[str] = None
        self.text_position_override: Optional[Point] = None
        self.is_associative = True
        self.is_orphaned = False
        self.measured_value_cache = 0.0
        self.dimension_line_anchor = DimensionAnchor(mode="fixed")
        self.text_anchor = DimensionAnchor(mode="fixed")
        self.fit_mode = "best_fit"
        self.layout_state: dict = {}
        self.text_is_outside = False
        self.arrows_are_outside = False
        self.has_leader = False
        self.leader_points: list[Point] = []
        self.landing_points: list[Point] = []
        self.arrows_flipped = False

    def reset_text_position(self):
        self.text_position_override = None

    def flip_arrows(self):
        self.arrows_flipped = not self.arrows_flipped

    @property
    def precision(self) -> int:
        return int(self.dimension_style.get("precision", 2))

    @property
    def display_text(self) -> str:
        if self.text_override:
            return self.text_override
        return self.format_measurement(self.measured_value_cache)

    def format_measurement(self, value: float) -> str:
        text = f"{value:.{self.precision}f}".rstrip("0").rstrip(".")
        if text == "-0":
            text = "0"
        return f"{self.text_prefix}{text}{self.text_suffix}"

    def _serialize_dimension_base(self) -> dict:
        return {
            "dimension_style": dict(self.dimension_style),
            "text_override": self.text_override,
            "text_position_override": self.text_position_override.to_dict() if self.text_position_override else None,
            "is_associative": self.is_associative,
            "is_orphaned": self.is_orphaned,
            "measured_value_cache": self.measured_value_cache,
            "dimension_line_anchor": self.dimension_line_anchor.to_dict(),
            "text_anchor": self.text_anchor.to_dict(),
            "fit_mode": self.fit_mode,
            "text_is_outside": self.text_is_outside,
            "arrows_are_outside": self.arrows_are_outside,
            "has_leader": self.has_leader,
            "leader_points": [p.to_dict() for p in self.leader_points],
            "landing_points": [p.to_dict() for p in self.landing_points],
            "arrows_flipped": self.arrows_flipped,
        }

    def _load_dimension_base(self, data: dict):
        self.dimension_style = {**default_dimension_style(), **data.get("dimension_style", {})}
        if self.dimension_style.get("arrow_type") == "open":
            self.dimension_style.pop("arrow_fill", None)
        elif "arrow_fill" in self.dimension_style:
            self.dimension_style["arrow_type"] = "closed_filled" if self.dimension_style.get("arrow_fill", True) else "closed"
            self.dimension_style.pop("arrow_fill", None)
        self.text_override = data.get("text_override")
        text_pos = data.get("text_position_override")
        self.text_position_override = Point.from_dict(text_pos) if text_pos else None
        self.is_associative = bool(data.get("is_associative", self.is_associative))
        self.is_orphaned = bool(data.get("is_orphaned", self.is_orphaned))
        self.measured_value_cache = float(data.get("measured_value_cache", self.measured_value_cache))
        self.dimension_line_anchor = DimensionAnchor.from_dict(data.get("dimension_line_anchor", {"mode": "fixed"}))
        self.text_anchor = DimensionAnchor.from_dict(data.get("text_anchor", {"mode": "fixed"}))
        self.fit_mode = data.get("fit_mode", self.fit_mode)
        self.text_is_outside = bool(data.get("text_is_outside", self.text_is_outside))
        self.arrows_are_outside = bool(data.get("arrows_are_outside", self.arrows_are_outside))
        self.has_leader = bool(data.get("has_leader", self.has_leader))
        self.leader_points = [Point.from_dict(p) for p in data.get("leader_points", [])]
        self.landing_points = [Point.from_dict(p) for p in data.get("landing_points", [])]
        self.arrows_flipped = bool(data.get("arrows_flipped", self.arrows_flipped))

    def _resolve_anchor(self, scene, anchor: DimensionAnchor) -> Optional[Point]:
        if anchor.mode == "fixed":
            return anchor.cached_point.copy() if anchor.cached_point else None
        obj = scene.get_object_by_id(anchor.object_id) if scene else None
        if obj is None:
            return anchor.cached_point.copy() if anchor.cached_point else None
        point = resolve_selector_point(obj, anchor.selector)
        if point is not None:
            anchor.cached_point = point.copy()
        return point

    def _mark_orphan_if_needed(self, scene, anchors: list[DimensionAnchor]):
        self.is_orphaned = any(
            anchor.mode == "object_snap" and scene.get_object_by_id(anchor.object_id) is None
            for anchor in anchors
        )

    def _estimate_text_size_scene(self) -> tuple[float, float]:
        text = self.display_text or "0"
        height = global_dimension_text_height_mm()
        width = max(height * 1.8, len(text) * height * 0.62)
        return width, height

    def _update_layout_flags(self):
        self.text_is_outside = bool(self.layout_state.get("text_is_outside", False))
        self.arrows_are_outside = bool(self.layout_state.get("arrows_are_outside", False))
        self.has_leader = bool(self.layout_state.get("has_leader", False))
        self.leader_points = [p.copy() for p in self.layout_state.get("leader_points", [])]
        self.landing_points = [p.copy() for p in self.layout_state.get("landing_points", [])]

    def get_snap_points(self):
        points = []
        for point in self.layout_state.get("snap_points", []):
            points.append(SnapPoint(point.x, point.y, SnapType.NODE, self))
        return points

    def get_nearest_point(self, x: float, y: float):
        data = self.get_render_data()
        best_point = None
        best_distance = float("inf")
        target = Point(x, y)
        for start, end in data.get("segments", []):
            candidate = _project_point_to_segment(target, start, end)
            distance = candidate.distance_to(target)
            if distance < best_distance:
                best_distance = distance
                best_point = candidate
        if best_point is None:
            text_position = data.get("text_position")
            if text_position is not None:
                best_point = text_position.copy()
        return SnapPoint(best_point.x, best_point.y, SnapType.NEAREST, self) if best_point else None

    def distance_to_point(self, x: float, y: float) -> float:
        target = Point(x, y)
        distances = []
        for start, end in self.layout_state.get("segments", []):
            distances.append(_distance_point_to_segment(target, start, end))
        text_position = self.layout_state.get("text_position")
        if text_position is not None:
            width, height = self._estimate_text_size_scene()
            distances.append(_distance_point_to_box(target, text_position, width, height))
        return min(distances) if distances else 1e9

    def get_bounding_box(self):
        pts = []
        for start, end in self.layout_state.get("segments", []):
            pts.extend([start, end])
        pts.extend(self.layout_state.get("leader_points", []))
        pts.extend(self.layout_state.get("landing_points", []))
        text_position = self.layout_state.get("text_position")
        if text_position:
            width, height = self._estimate_text_size_scene()
            pts.extend([
                Point(text_position.x - width / 2, text_position.y - height / 2),
                Point(text_position.x + width / 2, text_position.y + height / 2),
            ])
        if not pts:
            return (0.0, 0.0, 0.0, 0.0)
        return (
            min(p.x for p in pts),
            min(p.y for p in pts),
            max(p.x for p in pts),
            max(p.y for p in pts),
        )

    def _base_render_dict(self, kind: str) -> dict:
        data = {
            "kind": kind,
            "segments": list(self.layout_state.get("segments", [])),
            "extension_lines": list(self.layout_state.get("extension_lines", [])),
            "text_position": self.layout_state.get("text_position"),
            "text_angle": self.layout_state.get("text_angle", 0.0),
            "text": self.display_text,
            "text_box": self._estimate_text_size_scene(),
            "arrows": list(self.layout_state.get("arrows", [])),
            "snap_points": list(self.layout_state.get("snap_points", [])),
            "leader_points": list(self.layout_state.get("leader_points", [])),
            "landing_points": list(self.layout_state.get("landing_points", [])),
            "text_is_outside": self.text_is_outside,
            "arrows_are_outside": self.arrows_are_outside,
            "has_leader": self.has_leader,
            "fit_mode": self.fit_mode,
            "fit_result": self.layout_state.get("fit_result", "inside"),
        }
        if "arc" in self.layout_state:
            data["arc"] = self.layout_state["arc"]
        return data

    def recompute(self, scene):
        raise NotImplementedError

    def get_render_data(self) -> dict:
        raise NotImplementedError


class LinearDimension(DimensionBase):
    dimension_type = "linear_dimension"

    def __init__(self, p1_anchor: DimensionAnchor, p2_anchor: DimensionAnchor, mode: str = "aligned"):
        super().__init__()
        self.mode = mode
        self.anchor1 = p1_anchor
        self.anchor2 = p2_anchor

    def to_dict(self) -> dict:
        data = {
            "type": "linear_dimension",
            "mode": self.mode,
            "anchor1": self.anchor1.to_dict(),
            "anchor2": self.anchor2.to_dict(),
        }
        data.update(self._serialize_dimension_base())
        data.update(self._serialize_common())
        return data

    @staticmethod
    def from_dict(data: dict) -> "LinearDimension":
        obj = LinearDimension(
            DimensionAnchor.from_dict(data["anchor1"]),
            DimensionAnchor.from_dict(data["anchor2"]),
            mode=data.get("mode", "aligned"),
        )
        obj._load_dimension_base(data)
        obj._load_common(data)
        return obj

    def recompute(self, scene):
        p1 = self._resolve_anchor(scene, self.anchor1)
        p2 = self._resolve_anchor(scene, self.anchor2)
        placement = self._resolve_anchor(scene, self.dimension_line_anchor)
        self._mark_orphan_if_needed(scene, [self.anchor1, self.anchor2])
        if not p1 or not p2:
            self.layout_state = {}
            return

        gap = float(self.dimension_style.get("object_gap_mm", 10.0))
        if self.mode == "horizontal":
            axis = Point(1.0, 0.0)
            normal = Point(0.0, 1.0)
            base1 = p1
            base2 = p2
            offset = (placement.y - p1.y) if placement else gap
            ext1 = Point(p1.x, p1.y + offset)
            ext2 = Point(p2.x, p2.y + offset)
            measure = abs(p2.x - p1.x)
            text_angle = 0.0
        elif self.mode == "vertical":
            axis = Point(0.0, 1.0)
            normal = Point(1.0, 0.0)
            base1 = p1
            base2 = p2
            offset = (placement.x - p1.x) if placement else gap
            ext1 = Point(p1.x + offset, p1.y)
            ext2 = Point(p2.x + offset, p2.y)
            measure = abs(p2.y - p1.y)
            text_angle = 90.0
        else:
            direction = p2 - p1
            length = math.hypot(direction.x, direction.y)
            if length <= 1e-9:
                self.layout_state = {}
                return
            axis = Point(direction.x / length, direction.y / length)
            normal = Point(-axis.y, axis.x)
            offset = ((placement.x - p1.x) * normal.x + (placement.y - p1.y) * normal.y) if placement else gap
            base1 = p1
            base2 = p2
            ext1 = Point(p1.x + normal.x * offset, p1.y + normal.y * offset)
            ext2 = Point(p2.x + normal.x * offset, p2.y + normal.y * offset)
            measure = length
            text_angle = math.degrees(math.atan2(axis.y, axis.x))

        self.measured_value_cache = measure
        line_length = ext1.distance_to(ext2)
        text_w, text_h = self._estimate_text_size_scene()
        arrow = global_dimension_arrow_size_mm()
        text_gap = float(self.dimension_style.get("text_gap_mm", 1.0))
        inside_text = not self.text_position_override and (text_w + 2 * (arrow + text_gap) <= line_length)
        arrows_inside = (2 * arrow <= line_length) and not self.arrows_flipped
        fit_result = "inside"
        if not inside_text:
            fit_result = "outside_text"
        if not arrows_inside:
            fit_result = "outside_arrows" if fit_result == "inside" else "outside_both"

        midpoint = ext1.midpoint(ext2)
        text_position = midpoint
        leader_points: list[Point] = []
        landing_points: list[Point] = []
        has_leader = False
        if self.text_position_override:
            text_position = self.text_position_override.copy()
            offset_to_text = abs((text_position.x - midpoint.x) * normal.x + (text_position.y - midpoint.y) * normal.y)
            if offset_to_text > max(text_gap * 1.5, text_h):
                fit_result = "outside_text"
                has_leader = True
        elif not inside_text:
            sign = 1.0 if ((placement.x - midpoint.x) * normal.x + (placement.y - midpoint.y) * normal.y) >= 0 else -1.0
            text_position = Point(
                midpoint.x + normal.x * sign * (text_h + text_gap * 2.0),
                midpoint.y + normal.y * sign * (text_h + text_gap * 2.0),
            )
            has_leader = True

        if has_leader:
            if self.text_position_override:
                leader_points, landing_points = _manual_text_leader_layout(midpoint, text_position, text_w, text_h)
                text_angle = 0.0
            else:
                anchor = midpoint
                landing_start = Point(text_position.x - axis.x * text_w * 0.35, text_position.y - axis.y * text_w * 0.35)
                leader_points = [anchor, landing_start]
                landing_points = [landing_start, text_position]

        arrows = _linear_arrows(ext1, ext2, axis, arrow, arrows_inside)
        segments = [(ext1, ext2)] + leader_segments(leader_points, landing_points)
        ext_overshoot = float(self.dimension_style.get("extension_overshoot_mm", 2.0))
        extension_lines = [
            (base1, Point(ext1.x + normal.x * ext_overshoot, ext1.y + normal.y * ext_overshoot)),
            (base2, Point(ext2.x + normal.x * ext_overshoot, ext2.y + normal.y * ext_overshoot)),
        ]
        snap_points = [base1, base2, ext1, ext2, text_position]
        if has_leader:
            snap_points.extend(leader_points + landing_points)

        self.layout_state = {
            "segments": segments,
            "extension_lines": extension_lines,
            "text_position": text_position,
            "text_angle": text_angle,
            "arrows": arrows,
            "snap_points": snap_points,
            "leader_points": leader_points,
            "landing_points": landing_points,
            "text_is_outside": fit_result != "inside",
            "arrows_are_outside": not arrows_inside,
            "has_leader": has_leader,
            "fit_result": fit_result,
        }
        self._update_layout_flags()

    def get_render_data(self) -> dict:
        return self._base_render_dict("linear")

    def get_control_points(self):
        if not self.layout_state:
            return []
        snaps = self.layout_state["snap_points"]
        return [
            ControlPoint(snaps[0].x, snaps[0].y, "Выносная 1", 0),
            ControlPoint(snaps[1].x, snaps[1].y, "Выносная 2", 1),
            ControlPoint(snaps[2].midpoint(snaps[3]).x, snaps[2].midpoint(snaps[3]).y, "Размерная линия", 2),
            ControlPoint(self.layout_state["text_position"].x, self.layout_state["text_position"].y, "Текст", 3),
        ]

    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        point = Point(new_x, new_y)
        if index == 0:
            self.anchor1 = DimensionAnchor(mode="fixed", cached_point=point)
            self.is_associative = False
            return True
        if index == 1:
            self.anchor2 = DimensionAnchor(mode="fixed", cached_point=point)
            self.is_associative = False
            return True
        if index == 2:
            self.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=point)
            return True
        if index == 3:
            self.text_position_override = point
            return True
        return False


class RadialDimension(DimensionBase):
    dimension_type = "radial_dimension"

    def __init__(self, center_anchor: DimensionAnchor, curve_anchor: DimensionAnchor):
        super().__init__()
        self.anchor_center = center_anchor
        self.anchor_curve = curve_anchor
        self.text_prefix = "R"

    def to_dict(self) -> dict:
        data = {
            "type": "radial_dimension",
            "anchor_center": self.anchor_center.to_dict(),
            "anchor_curve": self.anchor_curve.to_dict(),
        }
        data.update(self._serialize_dimension_base())
        data.update(self._serialize_common())
        return data

    @staticmethod
    def from_dict(data: dict) -> "RadialDimension":
        obj = RadialDimension(
            DimensionAnchor.from_dict(data["anchor_center"]),
            DimensionAnchor.from_dict(data["anchor_curve"]),
        )
        obj._load_dimension_base(data)
        obj._load_common(data)
        return obj

    def recompute(self, scene):
        center = self._resolve_anchor(scene, self.anchor_center)
        curve = self._resolve_anchor(scene, self.anchor_curve)
        placement = self._resolve_anchor(scene, self.dimension_line_anchor)
        self._mark_orphan_if_needed(scene, [self.anchor_center, self.anchor_curve])
        if not center or not curve:
            self.layout_state = {}
            return
        radius = center.distance_to(curve)
        if radius <= 1e-9:
            self.layout_state = {}
            return

        if placement is None:
            placement = curve.copy()

        axis = _unit_vector(placement - center)
        if axis is None:
            axis = _unit_vector(curve - center) or Point(1.0, 0.0)

        edge = Point(center.x + axis.x * radius, center.y + axis.y * radius)
        text_w, text_h = self._estimate_text_size_scene()
        arrow = global_dimension_arrow_size_mm()
        text_gap = float(self.dimension_style.get("text_gap_mm", 1.0))
        placement_dist = center.distance_to(placement)
        inside_capacity = max(radius - arrow - text_gap * 3.0, 0.0)
        inside_fit = placement_dist <= radius and text_w <= inside_capacity and not self.arrows_flipped

        fit_result = "inside" if inside_fit else "outside_text"
        text_position = self.text_position_override.copy() if self.text_position_override else None
        leader_points: list[Point] = []
        landing_points: list[Point] = []
        segments: list[tuple[Point, Point]] = []
        arrows = []

        if text_position is None and inside_fit:
            text_position = Point(
                center.x + axis.x * max(radius * 0.45, min(radius - arrow - text_gap, text_w * 0.6)),
                center.y + axis.y * max(radius * 0.45, min(radius - arrow - text_gap, text_w * 0.6)),
            )
        elif text_position is None:
            outside_dist = max(radius + text_h * 1.25 + text_gap * 2.0, placement_dist)
            text_position = Point(center.x + axis.x * outside_dist, center.y + axis.y * outside_dist)

        manual_outside = center.distance_to(text_position) > radius - max(text_gap * 2.0, arrow)
        if not inside_fit or manual_outside or _distance_from_axis(text_position, center, axis) > text_h:
            fit_result = "outside_text"
            if self.text_position_override:
                leader_points, landing_points = _manual_text_leader_layout(edge, text_position, text_w, text_h)
            else:
                kink = Point(center.x + axis.x * (radius + text_gap * 1.5), center.y + axis.y * (radius + text_gap * 1.5))
                landing_start = Point(text_position.x - axis.x * text_w * 0.45, text_position.y - axis.y * text_w * 0.45)
                leader_points = [edge, kink]
                landing_points = [landing_start, text_position]
            segments = [(center, edge)] + leader_segments(leader_points, landing_points)
            arrows = [{"tip": edge, "tail": _single_arrow_tail(edge, axis, arrow, outward=self.arrows_flipped)}]
        else:
            fit_result = "inside"
            segments = [(center, edge)]
            arrows = [{"tip": edge, "tail": _single_arrow_tail(edge, axis, arrow, outward=self.arrows_flipped)}]

        self.measured_value_cache = radius
        self.layout_state = {
            "segments": segments,
            "extension_lines": [],
            "text_position": text_position,
            "text_angle": 0.0 if self.text_position_override else math.degrees(math.atan2(axis.y, axis.x)),
            "arrows": arrows,
            "snap_points": [center, edge, text_position] + leader_points + landing_points,
            "leader_points": leader_points,
            "landing_points": landing_points,
            "text_is_outside": fit_result != "inside",
            "arrows_are_outside": self.arrows_flipped,
            "has_leader": bool(leader_points or landing_points),
            "fit_result": fit_result,
        }
        self._update_layout_flags()

    def get_render_data(self) -> dict:
        return self._base_render_dict("radial")

    def get_control_points(self):
        if not self.layout_state:
            return []
        text_position = self.layout_state["text_position"]
        end = self.layout_state["segments"][-1][1]
        return [
            ControlPoint(end.x, end.y, "Положение", 0),
            ControlPoint(text_position.x, text_position.y, "Текст", 1),
        ]

    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        point = Point(new_x, new_y)
        if index == 0:
            self.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=point)
            return True
        if index == 1:
            self.text_position_override = point
            return True
        return False


class DiameterDimension(DimensionBase):
    dimension_type = "diameter_dimension"

    def __init__(self, center_anchor: DimensionAnchor, curve_anchor: DimensionAnchor):
        super().__init__()
        self.anchor_center = center_anchor
        self.anchor_curve = curve_anchor
        self.text_prefix = "Ø"

    def to_dict(self) -> dict:
        data = {
            "type": "diameter_dimension",
            "anchor_center": self.anchor_center.to_dict(),
            "anchor_curve": self.anchor_curve.to_dict(),
        }
        data.update(self._serialize_dimension_base())
        data.update(self._serialize_common())
        return data

    @staticmethod
    def from_dict(data: dict) -> "DiameterDimension":
        obj = DiameterDimension(
            DimensionAnchor.from_dict(data["anchor_center"]),
            DimensionAnchor.from_dict(data["anchor_curve"]),
        )
        obj._load_dimension_base(data)
        obj._load_common(data)
        return obj

    def recompute(self, scene):
        center = self._resolve_anchor(scene, self.anchor_center)
        curve = self._resolve_anchor(scene, self.anchor_curve)
        placement = self._resolve_anchor(scene, self.dimension_line_anchor)
        self._mark_orphan_if_needed(scene, [self.anchor_center, self.anchor_curve])
        if not center or not curve:
            self.layout_state = {}
            return
        radius = center.distance_to(curve)
        if radius <= 1e-9:
            self.layout_state = {}
            return

        source_obj = scene.get_object_by_id(self.anchor_center.object_id) if scene and self.anchor_center.object_id else None
        is_arc_source = self.anchor_curve.selector in {"arc_start", "arc_mid", "arc_end"} or getattr(source_obj, "__class__", None).__name__ == "Arc"

        if placement is None:
            placement = curve.copy()
        axis = _unit_vector(placement - center)
        if axis is None:
            axis = _unit_vector(curve - center) or Point(1.0, 0.0)

        if is_arc_source:
            self._recompute_arc_diameter(center, radius, axis, placement)
            return

        start = Point(center.x - axis.x * radius, center.y - axis.y * radius)
        end = Point(center.x + axis.x * radius, center.y + axis.y * radius)
        diameter = radius * 2.0
        self.measured_value_cache = diameter
        text_w, text_h = self._estimate_text_size_scene()
        arrow = global_dimension_arrow_size_mm()
        text_gap = float(self.dimension_style.get("text_gap_mm", 1.0))
        placement_dist = center.distance_to(placement)
        placement_requests_outside = placement_dist > radius + text_gap
        inside_fit = (
            (text_w + 2 * (arrow + text_gap) <= diameter)
            and not self.arrows_flipped
            and not placement_requests_outside
        )
        fit_result = "inside" if inside_fit else "outside_text"
        leader_points: list[Point] = []
        landing_points: list[Point] = []
        if self.text_position_override is not None:
            text_position = self.text_position_override.copy()
            if center.distance_to(text_position) > radius:
                fit_result = "outside_text"
        elif inside_fit:
            text_position = center.copy()
        else:
            outside_dist = max(radius + text_h * 1.5, center.distance_to(placement))
            text_position = Point(center.x + axis.x * outside_dist, center.y + axis.y * outside_dist)

        if fit_result != "inside":
            near = end if end.distance_to(text_position) <= start.distance_to(text_position) else start
            if self.text_position_override:
                leader_points, landing_points = _manual_text_leader_layout(near, text_position, text_w, text_h)
            else:
                outward = _unit_vector(text_position - center) or axis
                kink = Point(near.x + outward.x * (text_gap * 1.5), near.y + outward.y * (text_gap * 1.5))
                landing_start = Point(text_position.x - outward.x * text_w * 0.45, text_position.y - outward.y * text_w * 0.45)
                leader_points = [near, kink]
                landing_points = [landing_start, text_position]
            segments = [(start, end)] + leader_segments(leader_points, landing_points)
        else:
            segments = [(start, end)]

        arrows_inside = fit_result == "inside" and not self.arrows_flipped
        arrows = _linear_arrows(start, end, axis, arrow, arrows_inside)
        self.layout_state = {
            "segments": segments,
            "extension_lines": [],
            "text_position": text_position,
            "text_angle": 0.0 if self.text_position_override else math.degrees(math.atan2(axis.y, axis.x)),
            "arrows": arrows,
            "snap_points": [start, center, end, text_position] + leader_points + landing_points,
            "leader_points": leader_points,
            "landing_points": landing_points,
            "text_is_outside": fit_result != "inside",
            "arrows_are_outside": not arrows_inside,
            "has_leader": bool(leader_points or landing_points),
            "fit_result": fit_result,
        }
        self._update_layout_flags()

    def _recompute_arc_diameter(self, center: Point, radius: float, axis: Point, placement: Point):
        edge = Point(center.x + axis.x * radius, center.y + axis.y * radius)
        diameter = radius * 2.0
        self.measured_value_cache = diameter
        text_w, text_h = self._estimate_text_size_scene()
        arrow = global_dimension_arrow_size_mm()
        text_gap = float(self.dimension_style.get("text_gap_mm", 1.0))

        if self.text_position_override is not None:
            text_position = self.text_position_override.copy()
        else:
            text_position = placement.copy()

        inside_fit = center.distance_to(text_position) <= radius and (text_w <= max(radius - arrow - text_gap * 2.0, 0.0)) and not self.arrows_flipped
        fit_result = "inside" if inside_fit else "outside_text"
        leader_points: list[Point] = []
        landing_points: list[Point] = []

        if inside_fit:
            text_position = Point(
                center.x + axis.x * max(radius * 0.45, min(radius - arrow - text_gap, text_w * 0.55)),
                center.y + axis.y * max(radius * 0.45, min(radius - arrow - text_gap, text_w * 0.55)),
            )
            segments = [(center, edge)]
        else:
            if self.text_position_override:
                leader_points, landing_points = _manual_text_leader_layout(edge, text_position, text_w, text_h)
            else:
                outward = _unit_vector(text_position - center) or axis
                kink = Point(edge.x + outward.x * (text_gap * 1.5), edge.y + outward.y * (text_gap * 1.5))
                landing_start = Point(text_position.x - outward.x * text_w * 0.45, text_position.y - outward.y * text_w * 0.45)
                leader_points = [edge, kink]
                landing_points = [landing_start, text_position]
            segments = [(center, edge)] + leader_segments(leader_points, landing_points)

        self.layout_state = {
            "segments": segments,
            "extension_lines": [],
            "text_position": text_position,
            "text_angle": 0.0 if self.text_position_override else math.degrees(math.atan2(axis.y, axis.x)),
            "arrows": [{"tip": edge, "tail": _single_arrow_tail(edge, axis, arrow, outward=self.arrows_flipped)}],
            "snap_points": [center, edge, text_position] + leader_points + landing_points,
            "leader_points": leader_points,
            "landing_points": landing_points,
            "text_is_outside": fit_result != "inside",
            "arrows_are_outside": self.arrows_flipped,
            "has_leader": bool(leader_points or landing_points),
            "fit_result": fit_result,
        }
        self._update_layout_flags()

    def get_render_data(self) -> dict:
        return self._base_render_dict("diameter")

    def get_control_points(self):
        if not self.layout_state:
            return []
        text_position = self.layout_state["text_position"]
        center = self.layout_state["snap_points"][1]
        return [
            ControlPoint(center.x, center.y, "Ось", 0),
            ControlPoint(text_position.x, text_position.y, "Текст", 1),
        ]

    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        point = Point(new_x, new_y)
        if index == 0:
            self.dimension_line_anchor = DimensionAnchor(mode="fixed", cached_point=point)
            return True
        if index == 1:
            self.text_position_override = point
            return True
        return False


class AngularDimension(DimensionBase):
    dimension_type = "angular_dimension"
    text_suffix = "°"

    def __init__(self, vertex_anchor: DimensionAnchor, ray1_anchor: DimensionAnchor, ray2_anchor: DimensionAnchor):
        super().__init__()
        self.vertex_anchor = vertex_anchor
        self.ray1_anchor = ray1_anchor
        self.ray2_anchor = ray2_anchor
        self.dimension_style["precision"] = 1

    def to_dict(self) -> dict:
        data = {
            "type": "angular_dimension",
            "vertex_anchor": self.vertex_anchor.to_dict(),
            "ray1_anchor": self.ray1_anchor.to_dict(),
            "ray2_anchor": self.ray2_anchor.to_dict(),
        }
        data.update(self._serialize_dimension_base())
        data.update(self._serialize_common())
        return data

    @staticmethod
    def from_dict(data: dict) -> "AngularDimension":
        obj = AngularDimension(
            DimensionAnchor.from_dict(data["vertex_anchor"]),
            DimensionAnchor.from_dict(data["ray1_anchor"]),
            DimensionAnchor.from_dict(data["ray2_anchor"]),
        )
        obj._load_dimension_base(data)
        obj._load_common(data)
        return obj

    def recompute(self, scene):
        vertex = self._resolve_anchor(scene, self.vertex_anchor)
        ray1 = self._resolve_anchor(scene, self.ray1_anchor)
        ray2 = self._resolve_anchor(scene, self.ray2_anchor)
        placement = self._resolve_anchor(scene, self.dimension_line_anchor)
        self._mark_orphan_if_needed(scene, [self.vertex_anchor, self.ray1_anchor, self.ray2_anchor])
        if not vertex or not ray1 or not ray2:
            self.layout_state = {}
            return

        a1 = math.atan2(ray1.y - vertex.y, ray1.x - vertex.x)
        a2 = math.atan2(ray2.y - vertex.y, ray2.x - vertex.x)
        span = _normalize_positive_angle(a2 - a1)
        if placement:
            placement_angle = math.atan2(placement.y - vertex.y, placement.x - vertex.x)
            interior_contains = _angle_is_between_ccw(placement_angle, a1, a2)
            if not interior_contains:
                a1, a2 = a2, a1
                span = _normalize_positive_angle(a2 - a1)
        elif span > math.pi:
            a1, a2 = a2, a1
            span = _normalize_positive_angle(a2 - a1)

        radius = max(1.0, vertex.distance_to(placement) if placement else min(vertex.distance_to(ray1), vertex.distance_to(ray2)) * 0.7)
        mid_angle = a1 + span / 2.0
        start = Point(vertex.x + math.cos(a1) * radius, vertex.y + math.sin(a1) * radius)
        end = Point(vertex.x + math.cos(a2) * radius, vertex.y + math.sin(a2) * radius)
        text_w, text_h = self._estimate_text_size_scene()
        default_text = Point(vertex.x + math.cos(mid_angle) * radius, vertex.y + math.sin(mid_angle) * radius)
        text_position = self.text_position_override.copy() if self.text_position_override else default_text
        has_leader = text_position.distance_to(default_text) > max(text_h, 2.0)
        leader_points = []
        landing_points = []
        if has_leader:
            if self.text_position_override:
                leader_points, landing_points = _manual_text_leader_layout(default_text, text_position, text_w, text_h)
            else:
                text_dir = _unit_vector(text_position - vertex) or Point(math.cos(mid_angle), math.sin(mid_angle))
                landing_start = Point(text_position.x - text_dir.x * text_w * 0.35, text_position.y - text_dir.y * text_w * 0.35)
                leader_points = [default_text, landing_start]
                landing_points = [landing_start, text_position]

        self.measured_value_cache = math.degrees(span)
        arrow = global_dimension_arrow_size_mm()
        tangent_start = _angular_arrow_tail(start, a1, arrow, reverse=self.arrows_flipped, at_start=True)
        tangent_end = _angular_arrow_tail(end, a2, arrow, reverse=self.arrows_flipped, at_start=False)
        self.layout_state = {
            "segments": leader_segments(leader_points, landing_points),
            "extension_lines": [(vertex, start), (vertex, end)],
            "arc": {
                "center": vertex,
                "radius": radius,
                "start_angle_deg": math.degrees(a1),
                "span_angle_deg": math.degrees(span),
            },
            "text_position": text_position,
            "text_angle": 0.0 if self.text_position_override else math.degrees(mid_angle),
            "arrows": [
                {"tip": start, "tail": tangent_start},
                {"tip": end, "tail": tangent_end},
            ],
            "snap_points": [vertex, start, end, text_position] + leader_points + landing_points,
            "leader_points": leader_points,
            "landing_points": landing_points,
            "text_is_outside": has_leader,
            "arrows_are_outside": self.arrows_flipped,
            "has_leader": has_leader,
            "fit_result": "outside_text" if has_leader else "inside",
        }
        self._update_layout_flags()

    def get_render_data(self) -> dict:
        data = self._base_render_dict("angular")
        if "arc" in self.layout_state:
            data["arc"] = self.layout_state["arc"]
        return data

    def get_control_points(self):
        if not self.layout_state:
            return []
        snaps = self.layout_state["snap_points"]
        return [
            ControlPoint(snaps[0].x, snaps[0].y, "Вершина", 0),
            ControlPoint(snaps[1].x, snaps[1].y, "Луч 1", 1),
            ControlPoint(snaps[2].x, snaps[2].y, "Луч 2", 2),
            ControlPoint(self.layout_state["text_position"].x, self.layout_state["text_position"].y, "Текст", 3),
        ]

    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        point = Point(new_x, new_y)
        if index == 0:
            self.vertex_anchor = DimensionAnchor(mode="fixed", cached_point=point)
            self.is_associative = False
            return True
        if index == 1:
            self.ray1_anchor = DimensionAnchor(mode="fixed", cached_point=point)
            self.is_associative = False
            return True
        if index == 2:
            self.ray2_anchor = DimensionAnchor(mode="fixed", cached_point=point)
            self.is_associative = False
            return True
        if index == 3:
            self.text_position_override = point
            return True
        return False


def resolve_selector_point(obj, selector: Optional[str]) -> Optional[Point]:
    if obj is None or not selector:
        return None
    if selector == "start":
        return getattr(obj, "start", None)
    if selector == "end":
        return getattr(obj, "end", None)
    if selector == "mid":
        return getattr(obj, "midpoint", None) or getattr(obj, "mid_point", None)
    if selector == "center":
        return getattr(obj, "center", None)
    if selector == "radius_point":
        center = getattr(obj, "center", None)
        radius = getattr(obj, "radius", None)
        if center is not None and radius is not None:
            return Point(center.x + radius, center.y)
    if selector == "arc_start":
        return getattr(obj, "start_point", None)
    if selector == "arc_end":
        return getattr(obj, "end_point", None)
    if selector == "arc_mid":
        return getattr(obj, "mid_point", None)
    if selector == "ellipse_q0":
        return getattr(obj, "major_axis_endpoint", None)
    if selector == "ellipse_center":
        return getattr(obj, "center", None)
    if selector and selector.startswith("vertex:"):
        try:
            index = int(selector.split(":", 1)[1])
        except ValueError:
            return None
        vertices = getattr(obj, "vertices", None)
        if vertices is None and hasattr(obj, "corners"):
            vertices = obj.corners
        if vertices and 0 <= index < len(vertices):
            return vertices[index]
    if selector and selector.startswith("midpoint:"):
        try:
            index = int(selector.split(":", 1)[1])
        except ValueError:
            return None
        vertices = getattr(obj, "vertices", None)
        if vertices is None and hasattr(obj, "corners"):
            vertices = obj.corners
        if vertices and len(vertices) >= 2:
            p1 = vertices[index % len(vertices)]
            p2 = vertices[(index + 1) % len(vertices)]
            return p1.midpoint(p2)
    if selector and selector.startswith("spline_cp:"):
        try:
            index = int(selector.split(":", 1)[1])
        except ValueError:
            return None
        points = getattr(obj, "control_points", None)
        if points and 0 <= index < len(points):
            return points[index]
    return None


def leader_segments(leader_points: list[Point], landing_points: list[Point]) -> list[tuple[Point, Point]]:
    points = list(leader_points) + list(landing_points)
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)] if len(points) >= 2 else []


def _manual_text_leader_layout(anchor: Point, text_position: Point, text_width: float, text_height: float) -> tuple[list[Point], list[Point]]:
    landing_y = text_position.y - text_height * 0.75
    left = Point(text_position.x - text_width * 0.55, landing_y)
    right = Point(text_position.x + text_width * 0.55, landing_y)
    attach = left if anchor.x <= text_position.x else right
    return [anchor, attach], [left, right]


def _single_arrow_tail(tip: Point, axis: Point, arrow_size: float, outward: bool) -> Point:
    direction = 1.0 if outward else -1.0
    return Point(tip.x + axis.x * arrow_size * direction, tip.y + axis.y * arrow_size * direction)


def _angular_arrow_tail(tip: Point, angle: float, arrow_size: float, reverse: bool, at_start: bool) -> Point:
    tangent = Point(math.sin(angle), -math.cos(angle)) if at_start else Point(-math.sin(angle), math.cos(angle))
    if reverse:
        tangent = Point(-tangent.x, -tangent.y)
    return Point(tip.x + tangent.x * arrow_size, tip.y + tangent.y * arrow_size)


def _linear_arrows(start: Point, end: Point, axis: Point, arrow_size: float, inside: bool) -> list[dict]:
    if inside:
        return [
            {"tip": start, "tail": Point(start.x + axis.x * arrow_size, start.y + axis.y * arrow_size)},
            {"tip": end, "tail": Point(end.x - axis.x * arrow_size, end.y - axis.y * arrow_size)},
        ]
    return [
        {"tip": start, "tail": Point(start.x - axis.x * arrow_size, start.y - axis.y * arrow_size)},
        {"tip": end, "tail": Point(end.x + axis.x * arrow_size, end.y + axis.y * arrow_size)},
    ]


def _unit_vector(point: Point) -> Optional[Point]:
    length = math.hypot(point.x, point.y)
    if length <= 1e-9:
        return None
    return Point(point.x / length, point.y / length)


def _normalize_positive_angle(value: float) -> float:
    while value < 0:
        value += math.tau
    while value >= math.tau:
        value -= math.tau
    return value


def _angle_is_between_ccw(test_angle: float, start_angle: float, end_angle: float) -> bool:
    test = _normalize_positive_angle(test_angle - start_angle)
    span = _normalize_positive_angle(end_angle - start_angle)
    return test <= span


def _project_point_to_segment(point: Point, start: Point, end: Point) -> Point:
    dx = end.x - start.x
    dy = end.y - start.y
    if math.isclose(dx, 0.0) and math.isclose(dy, 0.0):
        return start.copy()
    t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return Point(start.x + dx * t, start.y + dy * t)


def _distance_point_to_segment(point: Point, start: Point, end: Point) -> float:
    return point.distance_to(_project_point_to_segment(point, start, end))


def _distance_point_to_box(point: Point, center: Point, width: float, height: float) -> float:
    dx = max(abs(point.x - center.x) - width / 2.0, 0.0)
    dy = max(abs(point.y - center.y) - height / 2.0, 0.0)
    return math.hypot(dx, dy)


def _distance_from_axis(point: Point, origin: Point, axis: Point) -> float:
    normal = Point(-axis.y, axis.x)
    return abs((point.x - origin.x) * normal.x + (point.y - origin.y) * normal.y)
