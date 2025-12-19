"""
Геометрический примитив: Эллипс.
"""

import math
from typing import List, Tuple

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class Ellipse(GeometricPrimitive):
    """
    Геометрический примитив: Эллипс.
    Задается центром и двумя полуосями (радиусами).
    Оси параллельны координатным осям (угол наклона = 0).
    
    Способы создания:
    - Центр и две полуоси (конструктор)
    - Центр и конечные точки осей (from_center_and_axis_points)
    """
    
    def __init__(self, center: Point, radius_x: float, radius_y: float,
                 style_name: str = "Сплошная основная"):
        """
        Args:
            center: Центр эллипса
            radius_x: Полуось по X (горизонтальная)
            radius_y: Полуось по Y (вертикальная)
            style_name: Стиль линии
        """
        super().__init__(style_name)
        self.center = center
        self.radius_x = abs(radius_x)
        self.radius_y = abs(radius_y)

    # ==================== Альтернативные конструкторы ====================
    
    @classmethod
    def from_center_and_axis_points(cls, center: Point, axis_point_x: Point, axis_point_y: Point,
                                     style_name: str = "Сплошная основная") -> 'Ellipse':
        """
        Создание по центру и конечным точкам осей.
        
        Args:
            center: Центр эллипса
            axis_point_x: Конечная точка горизонтальной оси
            axis_point_y: Конечная точка вертикальной оси
        """
        radius_x = abs(axis_point_x.x - center.x)
        radius_y = abs(axis_point_y.y - center.y)
        return cls(center, radius_x, radius_y, style_name)
    
    @classmethod
    def from_bounding_rectangle(cls, p1: Point, p2: Point,
                                 style_name: str = "Сплошная основная") -> 'Ellipse':
        """
        Создание эллипса, вписанного в прямоугольник.
        """
        center = p1.midpoint(p2)
        radius_x = abs(p2.x - p1.x) / 2
        radius_y = abs(p2.y - p1.y) / 2
        return cls(center, radius_x, radius_y, style_name)

    # ==================== Свойства ====================
    
    @property
    def major_radius(self) -> float:
        """Большая полуось."""
        return max(self.radius_x, self.radius_y)
    
    @property
    def minor_radius(self) -> float:
        """Малая полуось."""
        return min(self.radius_x, self.radius_y)
    
    @property
    def eccentricity(self) -> float:
        """Эксцентриситет эллипса."""
        a = self.major_radius
        b = self.minor_radius
        if a == 0:
            return 0
        return math.sqrt(1 - (b / a) ** 2)
    
    @property
    def area(self) -> float:
        """Площадь эллипса."""
        return math.pi * self.radius_x * self.radius_y
    
    @property
    def circumference(self) -> float:
        """
        Приблизительная длина окружности эллипса.
        Использует формулу Рамануджана.
        """
        a, b = self.radius_x, self.radius_y
        h = ((a - b) / (a + b)) ** 2
        return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))

    # ==================== Сериализация ====================

    def to_dict(self) -> dict:
        return {
            "type": "ellipse",
            "center": self.center.to_dict(),
            "radius_x": self.radius_x,
            "radius_y": self.radius_y,
            "style": self.style_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'Ellipse':
        center = Point.from_dict(data["center"])
        radius_x = float(data["radius_x"])
        radius_y = float(data["radius_y"])
        style_name = data.get("style", "Сплошная основная")
        return Ellipse(center, radius_x, radius_y, style_name)

    # ==================== Объектные привязки ====================
    
    def get_snap_points(self) -> List[SnapPoint]:
        """
        Возвращает точки привязки: центр и 4 точки на осях (квадранты).
        """
        return [
            SnapPoint(self.center.x, self.center.y, SnapType.CENTER, self),
            # Квадранты (точки на осях)
            SnapPoint(self.center.x + self.radius_x, self.center.y, SnapType.QUADRANT, self),  # Вправо
            SnapPoint(self.center.x, self.center.y + self.radius_y, SnapType.QUADRANT, self),  # Вверх
            SnapPoint(self.center.x - self.radius_x, self.center.y, SnapType.QUADRANT, self),  # Влево
            SnapPoint(self.center.x, self.center.y - self.radius_y, SnapType.QUADRANT, self),  # Вниз
        ]

    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает контрольные точки: центр и конечные точки осей.
        """
        return [
            ControlPoint(self.center.x, self.center.y, "Центр", 0),
            ControlPoint(self.center.x + self.radius_x, self.center.y, "Ось X", 1),
            ControlPoint(self.center.x, self.center.y + self.radius_y, "Ось Y", 2),
        ]
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку.
        index=0: центр, index=1: ось X (радиус X), index=2: ось Y (радиус Y)
        """
        if index == 0:
            # Перемещение центра
            self.center = Point(new_x, new_y)
            return True
        elif index == 1:
            # Изменение радиуса по X
            new_radius_x = abs(new_x - self.center.x)
            if new_radius_x > 0:
                self.radius_x = new_radius_x
                return True
        elif index == 2:
            # Изменение радиуса по Y
            new_radius_y = abs(new_y - self.center.y)
            if new_radius_y > 0:
                self.radius_y = new_radius_y
                return True
        return False

    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Возвращает ограничивающий прямоугольник."""
        return (
            self.center.x - self.radius_x,
            self.center.y - self.radius_y,
            self.center.x + self.radius_x,
            self.center.y + self.radius_y
        )
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет приблизительное расстояние от точки до эллипса.
        Использует итеративный метод для точности.
        """
        # Для упрощения используем приближённый метод
        # Нормализуем координаты относительно центра
        dx = x - self.center.x
        dy = y - self.center.y
        
        # Если оба радиуса равны 0
        if self.radius_x == 0 and self.radius_y == 0:
            return math.sqrt(dx ** 2 + dy ** 2)
        
        # Используем параметрическое представление
        # Находим ближайшую точку на эллипсе итеративно
        # Начальное приближение - угол к точке
        angle = math.atan2(dy * self.radius_x, dx * self.radius_y)
        
        for _ in range(5):  # Несколько итераций для уточнения
            # Точка на эллипсе
            ex = self.radius_x * math.cos(angle)
            ey = self.radius_y * math.sin(angle)
            
            # Расстояние
            dist = math.sqrt((dx - ex) ** 2 + (dy - ey) ** 2)
            
            # Проверка на минимум (градиентный спуск)
            # Производная расстояния по углу
            dex = -self.radius_x * math.sin(angle)
            dey = self.radius_y * math.cos(angle)
            
            gradient = 2 * ((dx - ex) * (-dex) + (dy - ey) * (-dey))
            
            # Шаг градиентного спуска
            step = 0.01
            if gradient > 0:
                angle -= step
            else:
                angle += step
        
        # Финальное расстояние
        ex = self.radius_x * math.cos(angle)
        ey = self.radius_y * math.sin(angle)
        return math.sqrt((dx - ex) ** 2 + (dy - ey) ** 2)
    
    def point_at_angle(self, angle: float) -> Point:
        """
        Возвращает точку на эллипсе по углу (параметру).
        
        Args:
            angle: Угол в радианах
        """
        return Point(
            self.center.x + self.radius_x * math.cos(angle),
            self.center.y + self.radius_y * math.sin(angle)
        )
    
    def is_point_inside(self, x: float, y: float) -> bool:
        """Проверяет, находится ли точка внутри эллипса."""
        if self.radius_x == 0 or self.radius_y == 0:
            return False
        dx = (x - self.center.x) / self.radius_x
        dy = (y - self.center.y) / self.radius_y
        return dx ** 2 + dy ** 2 <= 1

    def __repr__(self) -> str:
        return f"Ellipse({self.center}, rx={self.radius_x:.2f}, ry={self.radius_y:.2f})"
