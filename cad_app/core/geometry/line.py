"""
Геометрический примитив: Отрезок прямой.
"""

import math
from typing import List, Tuple

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class Line(GeometricPrimitive):
    """
    Геометрический примитив: Отрезок прямой.
    Задается двумя точками: начальной и конечной.
    """
    
    def __init__(self, start_point: Point, end_point: Point, style_name: str = "Сплошная основная"):
        super().__init__(style_name)
        self.start = start_point
        self.end = end_point

    # ==================== Свойства ====================
    
    @property
    def length(self) -> float:
        """Длина отрезка."""
        return self.start.distance_to(self.end)
    
    @property
    def midpoint(self) -> Point:
        """Середина отрезка."""
        return self.start.midpoint(self.end)
    
    @property
    def angle(self) -> float:
        """Угол наклона отрезка в радианах."""
        return self.start.angle_to(self.end)
    
    @property
    def dx(self) -> float:
        """Проекция на ось X."""
        return self.end.x - self.start.x
    
    @property
    def dy(self) -> float:
        """Проекция на ось Y."""
        return self.end.y - self.start.y

    # ==================== Сериализация ====================
    
    def to_dict(self) -> dict:
        return {
            "type": "line",
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "style": self.style_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'Line':
        start = Point.from_dict(data["start"])
        end = Point.from_dict(data["end"])
        style_name = data.get("style", "Сплошная основная")
        return Line(start, end, style_name)

    # ==================== Объектные привязки ====================
    
    def get_snap_points(self) -> List[SnapPoint]:
        """Возвращает точки привязки: концы и середина."""
        return [
            SnapPoint(self.start.x, self.start.y, SnapType.ENDPOINT, self),
            SnapPoint(self.end.x, self.end.y, SnapType.ENDPOINT, self),
            SnapPoint(self.midpoint.x, self.midpoint.y, SnapType.MIDPOINT, self),
        ]

    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """Возвращает контрольные точки: начало, конец и середина."""
        mid = self.midpoint
        return [
            ControlPoint(self.start.x, self.start.y, "Начало", 0),
            ControlPoint(self.end.x, self.end.y, "Конец", 1),
            ControlPoint(mid.x, mid.y, "Середина", 2),
        ]
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку.
        index=0: начало, index=1: конец, index=2: середина (перемещает всю линию)
        """
        if index == 0:
            self.start = Point(new_x, new_y)
            return True
        elif index == 1:
            self.end = Point(new_x, new_y)
            return True
        elif index == 2:
            # Перемещение за середину - двигаем всю линию
            current_mid = self.midpoint
            dx = new_x - current_mid.x
            dy = new_y - current_mid.y
            self.start = Point(self.start.x + dx, self.start.y + dy)
            self.end = Point(self.end.x + dx, self.end.y + dy)
            return True
        return False

    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Возвращает ограничивающий прямоугольник."""
        min_x = min(self.start.x, self.end.x)
        max_x = max(self.start.x, self.end.x)
        min_y = min(self.start.y, self.end.y)
        max_y = max(self.start.y, self.end.y)
        return (min_x, min_y, max_x, max_y)
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет минимальное расстояние от точки до отрезка.
        """
        # Вектор от start до end
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        
        # Длина отрезка в квадрате
        len_sq = dx * dx + dy * dy
        
        if len_sq == 0:
            # Отрезок вырожден в точку
            return math.sqrt((x - self.start.x) ** 2 + (y - self.start.y) ** 2)
        
        # Параметр t проекции точки на прямую
        t = ((x - self.start.x) * dx + (y - self.start.y) * dy) / len_sq
        
        # Ограничиваем t диапазоном [0, 1] для отрезка
        t = max(0, min(1, t))
        
        # Точка проекции
        proj_x = self.start.x + t * dx
        proj_y = self.start.y + t * dy
        
        return math.sqrt((x - proj_x) ** 2 + (y - proj_y) ** 2)
    
    def get_point_at_parameter(self, t: float) -> Point:
        """
        Возвращает точку на отрезке по параметру t ∈ [0, 1].
        t=0 → start, t=1 → end
        """
        return Point(
            self.start.x + t * (self.end.x - self.start.x),
            self.start.y + t * (self.end.y - self.start.y)
        )
    
    def get_perpendicular_point(self, from_point: Point) -> Point:
        """
        Возвращает точку на прямой, перпендикулярную к заданной точке.
        Может быть вне отрезка!
        """
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        len_sq = dx * dx + dy * dy
        
        if len_sq == 0:
            return self.start.copy()
        
        t = ((from_point.x - self.start.x) * dx + (from_point.y - self.start.y) * dy) / len_sq
        
        return Point(
            self.start.x + t * dx,
            self.start.y + t * dy
        )

    def __repr__(self) -> str:
        return f"Line({self.start}, {self.end}, style='{self.style_name}')"
