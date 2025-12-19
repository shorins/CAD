"""
Геометрический примитив: Правильный многоугольник.
"""

import math
from typing import List, Tuple

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class PolygonType:
    """Типы построения многоугольника."""
    INSCRIBED = "inscribed"      # Вписанный в окружность
    CIRCUMSCRIBED = "circumscribed"  # Описанный вокруг окружности


class Polygon(GeometricPrimitive):
    """
    Геометрический примитив: Правильный многоугольник.
    Задается центром, радиусом и количеством сторон.
    
    Способы создания:
    - Центр и радиус окружности (конструктор)
    - Вписанный или описанный вокруг окружности
    
    Редактирование:
    - Изменение варианта построения (вписанный/описанный)
    - Изменение количества углов
    """
    
    def __init__(self, center: Point, radius: float, num_sides: int = 6,
                 polygon_type: str = PolygonType.INSCRIBED,
                 rotation: float = 0.0,
                 style_name: str = "Сплошная основная"):
        """
        Args:
            center: Центр многоугольника
            radius: Радиус окружности (вписанной или описанной)
            num_sides: Количество сторон (минимум 3)
            polygon_type: Тип построения (INSCRIBED или CIRCUMSCRIBED)
            rotation: Угол поворота в градусах
            style_name: Стиль линии
        """
        super().__init__(style_name)
        self.center = center
        self.radius = abs(radius)
        self.num_sides = max(3, num_sides)
        self.polygon_type = polygon_type
        self.rotation = rotation  # Угол поворота первой вершины

    # ==================== Свойства ====================
    
    @property
    def vertices(self) -> List[Point]:
        """Возвращает все вершины многоугольника."""
        points = []
        angle_step = 2 * math.pi / self.num_sides
        start_angle = math.radians(self.rotation)
        
        # Для описанного многоугольника корректируем радиус
        if self.polygon_type == PolygonType.CIRCUMSCRIBED:
            # Радиус окружности = радиус * cos(π/n)
            effective_radius = self.radius / math.cos(math.pi / self.num_sides)
        else:
            effective_radius = self.radius
        
        for i in range(self.num_sides):
            angle = start_angle + i * angle_step
            x = self.center.x + effective_radius * math.cos(angle)
            y = self.center.y + effective_radius * math.sin(angle)
            points.append(Point(x, y))
        
        return points
    
    @property
    def side_length(self) -> float:
        """Длина стороны многоугольника."""
        if self.polygon_type == PolygonType.CIRCUMSCRIBED:
            effective_radius = self.radius / math.cos(math.pi / self.num_sides)
        else:
            effective_radius = self.radius
        return 2 * effective_radius * math.sin(math.pi / self.num_sides)
    
    @property
    def apothem(self) -> float:
        """Апофема (расстояние от центра до середины стороны)."""
        if self.polygon_type == PolygonType.CIRCUMSCRIBED:
            return self.radius
        else:
            return self.radius * math.cos(math.pi / self.num_sides)
    
    @property
    def area(self) -> float:
        """Площадь многоугольника."""
        return 0.5 * self.num_sides * self.side_length * self.apothem
    
    @property
    def perimeter(self) -> float:
        """Периметр многоугольника."""
        return self.num_sides * self.side_length

    # ==================== Сериализация ====================

    def to_dict(self) -> dict:
        return {
            "type": "polygon",
            "center": self.center.to_dict(),
            "radius": self.radius,
            "num_sides": self.num_sides,
            "polygon_type": self.polygon_type,
            "rotation": self.rotation,
            "style": self.style_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'Polygon':
        center = Point.from_dict(data["center"])
        radius = float(data["radius"])
        num_sides = int(data.get("num_sides", 6))
        polygon_type = data.get("polygon_type", PolygonType.INSCRIBED)
        rotation = float(data.get("rotation", 0))
        style_name = data.get("style", "Сплошная основная")
        return Polygon(center, radius, num_sides, polygon_type, rotation, style_name)

    # ==================== Объектные привязки ====================
    
    def get_snap_points(self) -> List[SnapPoint]:
        """
        Возвращает точки привязки: центр, вершины и середины сторон.
        """
        points = [
            SnapPoint(self.center.x, self.center.y, SnapType.CENTER, self),
        ]
        
        vertices = self.vertices
        
        # Вершины
        for v in vertices:
            points.append(SnapPoint(v.x, v.y, SnapType.ENDPOINT, self))
        
        # Середины сторон
        for i in range(len(vertices)):
            mid = vertices[i].midpoint(vertices[(i + 1) % len(vertices)])
            points.append(SnapPoint(mid.x, mid.y, SnapType.MIDPOINT, self))
        
        return points

    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает контрольные точки: центр и первая вершина (для радиуса).
        """
        vertices = self.vertices
        return [
            ControlPoint(self.center.x, self.center.y, "Центр", 0),
            ControlPoint(vertices[0].x, vertices[0].y, "Радиус", 1),
        ]
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку.
        index=0: центр, index=1: первая вершина (меняет радиус и угол)
        """
        if index == 0:
            self.center = Point(new_x, new_y)
            return True
        elif index == 1:
            # Изменение радиуса и угла поворота
            new_point = Point(new_x, new_y)
            new_radius = self.center.distance_to(new_point)
            
            # Для описанного многоугольника корректируем обратно
            if self.polygon_type == PolygonType.CIRCUMSCRIBED:
                new_radius = new_radius * math.cos(math.pi / self.num_sides)
            
            if new_radius > 0:
                self.radius = new_radius
                # Обновляем угол поворота
                self.rotation = math.degrees(math.atan2(
                    new_y - self.center.y,
                    new_x - self.center.x
                ))
                return True
        return False

    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Возвращает ограничивающий прямоугольник."""
        vertices = self.vertices
        xs = [v.x for v in vertices]
        ys = [v.y for v in vertices]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет минимальное расстояние от точки до контура многоугольника.
        """
        vertices = self.vertices
        min_dist = float('inf')
        
        for i in range(len(vertices)):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % len(vertices)]
            dist = self._distance_to_segment(x, y, p1, p2)
            min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _distance_to_segment(self, x: float, y: float, p1: Point, p2: Point) -> float:
        """Расстояние от точки до отрезка."""
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        
        len_sq = dx * dx + dy * dy
        if len_sq == 0:
            return math.sqrt((x - p1.x) ** 2 + (y - p1.y) ** 2)
        
        t = max(0, min(1, ((x - p1.x) * dx + (y - p1.y) * dy) / len_sq))
        
        proj_x = p1.x + t * dx
        proj_y = p1.y + t * dy
        
        return math.sqrt((x - proj_x) ** 2 + (y - proj_y) ** 2)
    
    def is_point_inside(self, x: float, y: float) -> bool:
        """
        Проверяет, находится ли точка внутри многоугольника.
        Использует алгоритм ray casting.
        """
        vertices = self.vertices
        n = len(vertices)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = vertices[i].x, vertices[i].y
            xj, yj = vertices[j].x, vertices[j].y
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside

    def __repr__(self) -> str:
        return f"Polygon({self.center}, r={self.radius:.2f}, sides={self.num_sides}, type='{self.polygon_type}')"
