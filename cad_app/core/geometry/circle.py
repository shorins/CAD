"""
Геометрический примитив: Окружность.
Поддерживает несколько способов создания.
"""

import math
from typing import List, Tuple, Optional

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class Circle(GeometricPrimitive):
    """
    Геометрический примитив: Окружность.
    Задается центром и радиусом.
    
    Способы создания:
    - Центр и радиус (конструктор)
    - Центр и диаметр (from_center_diameter)
    - Две точки - диаметр (from_two_points)
    - Три точки на окружности (from_three_points)
    """
    
    def __init__(self, center: Point, radius: float, style_name: str = "Сплошная основная"):
        super().__init__(style_name)
        self.center = center
        self.radius = abs(radius)  # Радиус всегда положительный

    # ==================== Альтернативные конструкторы ====================
    
    @classmethod
    def from_center_diameter(cls, center: Point, diameter: float, 
                             style_name: str = "Сплошная основная") -> 'Circle':
        """Создание по центру и диаметру."""
        return cls(center, diameter / 2, style_name)
    
    @classmethod
    def from_two_points(cls, p1: Point, p2: Point,
                        style_name: str = "Сплошная основная") -> 'Circle':
        """
        Создание по двум точкам (как диаметр).
        Центр - середина отрезка, радиус - половина расстояния.
        """
        center = p1.midpoint(p2)
        radius = p1.distance_to(p2) / 2
        return cls(center, radius, style_name)
    
    @classmethod
    def from_three_points(cls, p1: Point, p2: Point, p3: Point,
                          style_name: str = "Сплошная основная") -> Optional['Circle']:
        """
        Создание окружности через три точки.
        Возвращает None если точки коллинеарны.
        """
        # Проверяем, не коллинеарны ли точки
        # Используем определитель матрицы
        d = 2 * (p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y))
        
        if abs(d) < 1e-10:
            return None  # Точки коллинеарны
        
        # Вычисляем центр окружности
        p1_sq = p1.x ** 2 + p1.y ** 2
        p2_sq = p2.x ** 2 + p2.y ** 2
        p3_sq = p3.x ** 2 + p3.y ** 2
        
        cx = (p1_sq * (p2.y - p3.y) + p2_sq * (p3.y - p1.y) + p3_sq * (p1.y - p2.y)) / d
        cy = (p1_sq * (p3.x - p2.x) + p2_sq * (p1.x - p3.x) + p3_sq * (p2.x - p1.x)) / d
        
        center = Point(cx, cy)
        radius = center.distance_to(p1)
        
        return cls(center, radius, style_name)

    # ==================== Свойства ====================
    
    @property
    def diameter(self) -> float:
        """Диаметр окружности."""
        return self.radius * 2
    
    @diameter.setter
    def diameter(self, value: float):
        """Установка диаметра."""
        self.radius = abs(value) / 2
    
    @property
    def circumference(self) -> float:
        """Длина окружности."""
        return 2 * math.pi * self.radius
    
    @property
    def area(self) -> float:
        """Площадь круга."""
        return math.pi * self.radius ** 2

    # ==================== Сериализация ====================
    
    def to_dict(self) -> dict:
        return {
            "type": "circle",
            "center": self.center.to_dict(),
            "radius": self.radius,
            "style": self.style_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'Circle':
        center = Point.from_dict(data["center"])
        radius = float(data["radius"])
        style_name = data.get("style", "Сплошная основная")
        return Circle(center, radius, style_name)

    # ==================== Объектные привязки ====================
    
    def get_snap_points(self) -> List[SnapPoint]:
        """
        Возвращает точки привязки: центр и квадранты (0°, 90°, 180°, 270°).
        """
        points = [
            SnapPoint(self.center.x, self.center.y, SnapType.CENTER, self),
        ]
        
        # Квадранты
        for angle_deg in [0, 90, 180, 270]:
            angle_rad = math.radians(angle_deg)
            x = self.center.x + self.radius * math.cos(angle_rad)
            y = self.center.y + self.radius * math.sin(angle_rad)
            points.append(SnapPoint(x, y, SnapType.QUADRANT, self))
        
        return points
    
    def get_nearest_point(self, x: float, y: float) -> SnapPoint:
        """Возвращает ближайшую точку на окружности."""
        angle = math.atan2(y - self.center.y, x - self.center.x)
        px = self.center.x + self.radius * math.cos(angle)
        py = self.center.y + self.radius * math.sin(angle)
        return SnapPoint(px, py, SnapType.NEAREST, self)

    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает контрольные точки: центр и точка на окружности для радиуса.
        """
        # Точка справа от центра (0°) для изменения радиуса
        radius_point_x = self.center.x + self.radius
        radius_point_y = self.center.y
        
        return [
            ControlPoint(self.center.x, self.center.y, "Центр", 0),
            ControlPoint(radius_point_x, radius_point_y, "Радиус", 1),
        ]
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку.
        index=0: центр, index=1: точка радиуса
        """
        if index == 0:
            # Перемещение центра
            self.center = Point(new_x, new_y)
            return True
        elif index == 1:
            # Изменение радиуса
            new_radius = self.center.distance_to(Point(new_x, new_y))
            if new_radius > 0:
                self.radius = new_radius
                return True
        return False

    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Возвращает ограничивающий прямоугольник."""
        return (
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius
        )
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет расстояние от точки до окружности (не до центра!).
        """
        dist_to_center = math.sqrt((x - self.center.x) ** 2 + (y - self.center.y) ** 2)
        return abs(dist_to_center - self.radius)
    
    def point_at_angle(self, angle: float) -> Point:
        """
        Возвращает точку на окружности по углу.
        
        Args:
            angle: Угол в радианах (0 = вправо, π/2 = вверх)
        """
        return Point(
            self.center.x + self.radius * math.cos(angle),
            self.center.y + self.radius * math.sin(angle)
        )
    
    def is_point_inside(self, x: float, y: float) -> bool:
        """Проверяет, находится ли точка внутри окружности."""
        dist_sq = (x - self.center.x) ** 2 + (y - self.center.y) ** 2
        return dist_sq <= self.radius ** 2

    def __repr__(self) -> str:
        return f"Circle({self.center}, r={self.radius:.2f}, style='{self.style_name}')"
