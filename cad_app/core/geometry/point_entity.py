"""
Геометрический примитив: Точка DXF.
"""

from typing import List, Tuple

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class PointEntity(GeometricPrimitive):
    """Сценовый примитив точки для импорта/экспорта DXF."""

    def __init__(self, position: Point, style_name: str = "Сплошная основная"):
        super().__init__(style_name)
        self.position = position

    def to_dict(self) -> dict:
        data = {
            "type": "point",
            "position": self.position.to_dict(),
        }
        data.update(self._serialize_common())
        return data

    @staticmethod
    def from_dict(data: dict) -> "PointEntity":
        obj = PointEntity(Point.from_dict(data["position"]), data.get("style", "Сплошная основная"))
        obj._load_common(data)
        return obj

    def get_snap_points(self) -> List[SnapPoint]:
        return [
            SnapPoint(self.position.x, self.position.y, SnapType.ENDPOINT, self),
            SnapPoint(self.position.x, self.position.y, SnapType.NODE, self),
        ]

    def get_control_points(self) -> List[ControlPoint]:
        return [ControlPoint(self.position.x, self.position.y, "Точка", 0)]

    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        if index != 0:
            return False
        self.position = Point(new_x, new_y)
        return True

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        return (self.position.x, self.position.y, self.position.x, self.position.y)

    def distance_to_point(self, x: float, y: float) -> float:
        return self.position.distance_to(Point(x, y))
