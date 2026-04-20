"""
Геометрический примитив: Эллипс.
"""

import math
from typing import List, Tuple

from .base import ControlPoint, GeometricPrimitive, SnapPoint, SnapType
from .point import Point


class Ellipse(GeometricPrimitive):
    """
    Геометрический примитив: Эллипс.
    Задается центром, двумя полуосями и углом поворота локальной оси X.
    """

    def __init__(
        self,
        center: Point,
        radius_x: float,
        radius_y: float,
        style_name: str = "Сплошная основная",
        rotation: float = 0.0,
    ):
        super().__init__(style_name)
        self.center = center
        self.radius_x = abs(radius_x)
        self.radius_y = abs(radius_y)
        self.rotation = float(rotation)

    @classmethod
    def from_center_and_axis_points(
        cls,
        center: Point,
        axis_point_x: Point,
        axis_point_y: Point,
        style_name: str = "Сплошная основная",
    ) -> "Ellipse":
        axis_vector = axis_point_x - center
        radius_x = center.distance_to(axis_point_x)
        rotation = math.degrees(math.atan2(axis_vector.y, axis_vector.x))

        normal_x, normal_y = cls._unit_normal(rotation)
        dy = axis_point_y.y - center.y
        dx = axis_point_y.x - center.x
        radius_y = abs(dx * normal_x + dy * normal_y)
        return cls(center, radius_x, radius_y, style_name, rotation)

    @classmethod
    def from_bounding_rectangle(
        cls,
        p1: Point,
        p2: Point,
        style_name: str = "Сплошная основная",
        rotation: float = 0.0,
    ) -> "Ellipse":
        center = p1.midpoint(p2)
        radius_x = abs(p2.x - p1.x) / 2
        radius_y = abs(p2.y - p1.y) / 2
        return cls(center, radius_x, radius_y, style_name, rotation)

    @property
    def major_radius(self) -> float:
        return max(self.radius_x, self.radius_y)

    @property
    def minor_radius(self) -> float:
        return min(self.radius_x, self.radius_y)

    @property
    def eccentricity(self) -> float:
        a = self.major_radius
        b = self.minor_radius
        if a == 0:
            return 0
        return math.sqrt(1 - (b / a) ** 2)

    @property
    def area(self) -> float:
        return math.pi * self.radius_x * self.radius_y

    @property
    def circumference(self) -> float:
        a, b = self.radius_x, self.radius_y
        h = ((a - b) / (a + b)) ** 2 if (a + b) else 0.0
        return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(max(1e-9, 4 - 3 * h)))) if (a + b) else 0.0

    @property
    def major_axis_endpoint(self) -> Point:
        return self._world_from_local(self.radius_x, 0.0)

    @property
    def minor_axis_endpoint(self) -> Point:
        return self._world_from_local(0.0, self.radius_y)

    def to_dict(self) -> dict:
        data = {
            "type": "ellipse",
            "center": self.center.to_dict(),
            "radius_x": self.radius_x,
            "radius_y": self.radius_y,
            "rotation": self.rotation,
        }
        data.update(self._serialize_common())
        return data

    @staticmethod
    def from_dict(data: dict) -> "Ellipse":
        center = Point.from_dict(data["center"])
        radius_x = float(data["radius_x"])
        radius_y = float(data["radius_y"])
        style_name = data.get("style", "Сплошная основная")
        rotation = float(data.get("rotation", 0.0))
        obj = Ellipse(center, radius_x, radius_y, style_name, rotation)
        obj._load_common(data)
        return obj

    def get_snap_points(self) -> List[SnapPoint]:
        return [
            SnapPoint(self.center.x, self.center.y, SnapType.CENTER, self),
            SnapPoint(*self._world_from_local(self.radius_x, 0.0).to_tuple(), SnapType.QUADRANT, self),
            SnapPoint(*self._world_from_local(0.0, self.radius_y).to_tuple(), SnapType.QUADRANT, self),
            SnapPoint(*self._world_from_local(-self.radius_x, 0.0).to_tuple(), SnapType.QUADRANT, self),
            SnapPoint(*self._world_from_local(0.0, -self.radius_y).to_tuple(), SnapType.QUADRANT, self),
        ]

    def get_nearest_point(self, x: float, y: float) -> SnapPoint:
        """Возвращает ближайшую точку на эллипсе (итеративная проекция)."""
        local_x, local_y = self._local_from_world(Point(x, y))
        if self.radius_x == 0 and self.radius_y == 0:
            return SnapPoint(self.center.x, self.center.y, SnapType.NEAREST, self)
        # Начальное приближение — угол к точке
        angle = math.atan2(local_y * self.radius_x, local_x * self.radius_y)
        # Итерации Newton-Raphson
        for _ in range(10):
            ex = self.radius_x * math.cos(angle)
            ey = self.radius_y * math.sin(angle)
            dx_e = local_x - ex
            dy_e = local_y - ey
            dex = -self.radius_x * math.sin(angle)
            dey = self.radius_y * math.cos(angle)
            ddex = -self.radius_x * math.cos(angle)
            ddey = -self.radius_y * math.sin(angle)
            f = dx_e * dex + dy_e * dey
            fp = dx_e * ddex + dy_e * ddey - (dex * dex + dey * dey)
            if abs(fp) < 1e-12:
                break
            angle -= f / fp
        ex = self.radius_x * math.cos(angle)
        ey = self.radius_y * math.sin(angle)
        world_pt = self._world_from_local(ex, ey)
        return SnapPoint(world_pt.x, world_pt.y, SnapType.NEAREST, self)

    def get_control_points(self) -> List[ControlPoint]:
        major = self.major_axis_endpoint
        minor = self.minor_axis_endpoint
        return [
            ControlPoint(self.center.x, self.center.y, "Центр", 0),
            ControlPoint(major.x, major.y, "Ось X", 1),
            ControlPoint(minor.x, minor.y, "Ось Y", 2),
        ]

    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        if index == 0:
            self.center = Point(new_x, new_y)
            return True

        local_x, local_y = self._local_from_world(Point(new_x, new_y))
        if index == 1:
            new_radius_x = math.hypot(local_x, local_y)
            if new_radius_x > 0:
                self.radius_x = new_radius_x
                self.rotation = math.degrees(math.atan2(new_y - self.center.y, new_x - self.center.x))
                return True
        elif index == 2:
            new_radius_y = math.hypot(local_x, local_y)
            if new_radius_y > 0:
                self.radius_y = new_radius_y
                self.rotation = math.degrees(math.atan2(new_y - self.center.y, new_x - self.center.x)) - 90.0
                return True
        return False

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        cos_a = math.cos(math.radians(self.rotation))
        sin_a = math.sin(math.radians(self.rotation))
        extent_x = math.sqrt((self.radius_x * cos_a) ** 2 + (self.radius_y * sin_a) ** 2)
        extent_y = math.sqrt((self.radius_x * sin_a) ** 2 + (self.radius_y * cos_a) ** 2)
        return (
            self.center.x - extent_x,
            self.center.y - extent_y,
            self.center.x + extent_x,
            self.center.y + extent_y,
        )

    def distance_to_point(self, x: float, y: float) -> float:
        local_x, local_y = self._local_from_world(Point(x, y))
        if self.radius_x == 0 and self.radius_y == 0:
            return math.hypot(local_x, local_y)

        angle = math.atan2(local_y * self.radius_x, local_x * self.radius_y)
        for _ in range(5):
            ex = self.radius_x * math.cos(angle)
            ey = self.radius_y * math.sin(angle)
            dex = -self.radius_x * math.sin(angle)
            dey = self.radius_y * math.cos(angle)
            gradient = 2 * ((local_x - ex) * (-dex) + (local_y - ey) * (-dey))
            angle += 0.01 if gradient < 0 else -0.01

        ex = self.radius_x * math.cos(angle)
        ey = self.radius_y * math.sin(angle)
        return math.hypot(local_x - ex, local_y - ey)

    def point_at_angle(self, angle: float) -> Point:
        return self._world_from_local(self.radius_x * math.cos(angle), self.radius_y * math.sin(angle))

    def is_point_inside(self, x: float, y: float) -> bool:
        if self.radius_x == 0 or self.radius_y == 0:
            return False
        local_x, local_y = self._local_from_world(Point(x, y))
        dx = local_x / self.radius_x
        dy = local_y / self.radius_y
        return dx ** 2 + dy ** 2 <= 1

    def _world_from_local(self, local_x: float, local_y: float) -> Point:
        cos_a = math.cos(math.radians(self.rotation))
        sin_a = math.sin(math.radians(self.rotation))
        return Point(
            self.center.x + local_x * cos_a - local_y * sin_a,
            self.center.y + local_x * sin_a + local_y * cos_a,
        )

    def _local_from_world(self, point: Point) -> tuple[float, float]:
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        cos_a = math.cos(math.radians(self.rotation))
        sin_a = math.sin(math.radians(self.rotation))
        return (
            dx * cos_a + dy * sin_a,
            -dx * sin_a + dy * cos_a,
        )

    @staticmethod
    def _unit_normal(rotation: float) -> tuple[float, float]:
        angle = math.radians(rotation + 90.0)
        return math.cos(angle), math.sin(angle)

    def __repr__(self) -> str:
        return (
            f"Ellipse({self.center}, rx={self.radius_x:.2f}, "
            f"ry={self.radius_y:.2f}, rot={self.rotation:.2f})"
        )
