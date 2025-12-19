"""
Геометрический примитив: Прямоугольник.
Поддерживает несколько способов создания и фаски/скругления.
"""

import math
from typing import List, Tuple, Optional

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class Rectangle(GeometricPrimitive):
    """
    Геометрический примитив: Прямоугольник.
    Стороны параллельны осям координат.
    
    Способы создания:
    - Две противоположные точки (конструктор)
    - Одна точка, ширина и высота (from_point_and_size)
    - Центр, ширина и высота (from_center_and_size)
    """
    
    def __init__(self, p1: Point, p2: Point, style_name: str = "Сплошная основная",
                 corner_radius: float = 0.0, chamfer_size: float = 0.0):
        """
        Args:
            p1 (Point): Первая точка (угол).
            p2 (Point): Вторая точка (диагонально противоположный угол).
            style_name (str): Имя стиля.
            corner_radius (float): Радиус скругления углов (0 = без скругления).
            chamfer_size (float): Размер фаски (0 = без фаски).
        """
        super().__init__(style_name)
        self.p1 = p1
        self.p2 = p2
        self.corner_radius = max(0, corner_radius)
        self.chamfer_size = max(0, chamfer_size)

    # ==================== Альтернативные конструкторы ====================
    
    @classmethod
    def from_point_and_size(cls, origin: Point, width: float, height: float,
                            style_name: str = "Сплошная основная",
                            corner_radius: float = 0.0, chamfer_size: float = 0.0) -> 'Rectangle':
        """
        Создание по одной точке (левый нижний угол) и размерам.
        """
        p2 = Point(origin.x + width, origin.y + height)
        return cls(origin, p2, style_name, corner_radius, chamfer_size)
    
    @classmethod
    def from_center_and_size(cls, center: Point, width: float, height: float,
                             style_name: str = "Сплошная основная",
                             corner_radius: float = 0.0, chamfer_size: float = 0.0) -> 'Rectangle':
        """
        Создание по центру и размерам.
        """
        half_w = width / 2
        half_h = height / 2
        p1 = Point(center.x - half_w, center.y - half_h)
        p2 = Point(center.x + half_w, center.y + half_h)
        return cls(p1, p2, style_name, corner_radius, chamfer_size)

    # ==================== Свойства ====================

    @property
    def left(self) -> float:
        return min(self.p1.x, self.p2.x)

    @property
    def right(self) -> float:
        return max(self.p1.x, self.p2.x)
    
    @property
    def top(self) -> float:
        return max(self.p1.y, self.p2.y)

    @property
    def bottom(self) -> float:
        return min(self.p1.y, self.p2.y)

    @property
    def width(self) -> float:
        return abs(self.p1.x - self.p2.x)

    @property
    def height(self) -> float:
        return abs(self.p1.y - self.p2.y)
    
    @property
    def center(self) -> Point:
        """Центр прямоугольника."""
        return Point((self.left + self.right) / 2, (self.bottom + self.top) / 2)
    
    @property
    def area(self) -> float:
        """Площадь прямоугольника."""
        return self.width * self.height
    
    @property
    def perimeter(self) -> float:
        """Периметр прямоугольника."""
        return 2 * (self.width + self.height)
    
    @property
    def corners(self) -> List[Point]:
        """Возвращает все 4 угла прямоугольника (по часовой, начиная с левого нижнего)."""
        return [
            Point(self.left, self.bottom),   # Левый нижний
            Point(self.right, self.bottom),  # Правый нижний
            Point(self.right, self.top),     # Правый верхний
            Point(self.left, self.top),      # Левый верхний
        ]

    # ==================== Сериализация ====================

    def to_dict(self) -> dict:
        return {
            "type": "rectangle",
            "p1": self.p1.to_dict(),
            "p2": self.p2.to_dict(),
            "style": self.style_name,
            "corner_radius": self.corner_radius,
            "chamfer_size": self.chamfer_size,
        }

    @staticmethod
    def from_dict(data: dict) -> 'Rectangle':
        p1 = Point.from_dict(data["p1"])
        p2 = Point.from_dict(data["p2"])
        style_name = data.get("style", "Сплошная основная")
        corner_radius = float(data.get("corner_radius", 0))
        chamfer_size = float(data.get("chamfer_size", 0))
        return Rectangle(p1, p2, style_name, corner_radius, chamfer_size)

    # ==================== Объектные привязки ====================
    
    def get_snap_points(self) -> List[SnapPoint]:
        """
        Возвращает точки привязки: углы, середины сторон, центр.
        """
        corners = self.corners
        center = self.center
        
        points = [
            SnapPoint(center.x, center.y, SnapType.CENTER, self),
        ]
        
        # Углы
        for c in corners:
            points.append(SnapPoint(c.x, c.y, SnapType.ENDPOINT, self))
        
        # Середины сторон
        for i in range(4):
            mid = corners[i].midpoint(corners[(i + 1) % 4])
            points.append(SnapPoint(mid.x, mid.y, SnapType.MIDPOINT, self))
        
        return points

    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает контрольные точки: углы и центр.
        """
        corners = self.corners
        center = self.center
        
        return [
            ControlPoint(corners[0].x, corners[0].y, "Левый нижний", 0),
            ControlPoint(corners[1].x, corners[1].y, "Правый нижний", 1),
            ControlPoint(corners[2].x, corners[2].y, "Правый верхний", 2),
            ControlPoint(corners[3].x, corners[3].y, "Левый верхний", 3),
            ControlPoint(center.x, center.y, "Центр", 4),
        ]
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку.
        index=0-3: углы, index=4: центр (перемещает весь прямоугольник)
        """
        if index == 0:
            # Левый нижний угол
            self.p1 = Point(new_x, new_y)
            return True
        elif index == 1:
            # Правый нижний угол - меняем x у p2 и y у p1
            self.p2 = Point(new_x, self.p2.y)
            self.p1 = Point(self.p1.x, new_y)
            return True
        elif index == 2:
            # Правый верхний угол
            self.p2 = Point(new_x, new_y)
            return True
        elif index == 3:
            # Левый верхний угол - меняем x у p1 и y у p2
            self.p1 = Point(new_x, self.p1.y)
            self.p2 = Point(self.p2.x, new_y)
            return True
        elif index == 4:
            # Центр - перемещаем весь прямоугольник
            current_center = self.center
            dx = new_x - current_center.x
            dy = new_y - current_center.y
            self.p1 = Point(self.p1.x + dx, self.p1.y + dy)
            self.p2 = Point(self.p2.x + dx, self.p2.y + dy)
            return True
        return False

    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Возвращает ограничивающий прямоугольник."""
        return (self.left, self.bottom, self.right, self.top)
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет минимальное расстояние от точки до контура прямоугольника.
        """
        # Проверяем расстояние до каждой стороны
        corners = self.corners
        min_dist = float('inf')
        
        for i in range(4):
            p1 = corners[i]
            p2 = corners[(i + 1) % 4]
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
        """Проверяет, находится ли точка внутри прямоугольника."""
        return self.left <= x <= self.right and self.bottom <= y <= self.top

    def __repr__(self) -> str:
        return f"Rectangle({self.p1}, {self.p2}, style='{self.style_name}')"
