"""
Геометрический примитив: Дуга окружности.
Поддерживает несколько способов создания.
"""

import math
from typing import List, Tuple, Optional

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class Arc(GeometricPrimitive):
    """
    Геометрический примитив: Дуга окружности.
    Задается центром, радиусом, начальным углом и углом охвата.
    
    Способы создания:
    - Центр, радиус, начальный и конечный углы (конструктор)
    - Три точки: начало, промежуточная, конец (from_three_points)
    """
    
    def __init__(self, center: Point, radius: float, start_angle: float, span_angle: float,
                 style_name: str = "Сплошная основная"):
        """
        Args:
            center (Point): Центр дуги.
            radius (float): Радиус.
            start_angle (float): Начальный угол в градусах.
            span_angle (float): Угол охвата дуги в градусах (положительный - против часовой).
            style_name (str): Имя стиля линии.
        """
        super().__init__(style_name)
        self.center = center
        self.radius = abs(radius)
        self.start_angle = start_angle  # в градусах
        self.span_angle = span_angle    # в градусах

    # ==================== Альтернативные конструкторы ====================
    
    @classmethod
    def from_center_and_angles(cls, center: Point, radius: float,
                                start_angle: float, end_angle: float,
                                style_name: str = "Сплошная основная") -> 'Arc':
        """
        Создание по центру, радиусу, начальному и конечному углам.
        Углы в градусах.
        """
        span = end_angle - start_angle
        if span < 0:
            span += 360
        return cls(center, radius, start_angle, span, style_name)
    
    @classmethod
    def from_three_points(cls, p1: Point, p2: Point, p3: Point,
                          style_name: str = "Сплошная основная") -> Optional['Arc']:
        """
        Создание дуги через три точки (начало, точка на дуге, конец).
        Возвращает None если точки коллинеарны.
        
        Args:
            p1: Начальная точка дуги
            p2: Промежуточная точка на дуге
            p3: Конечная точка дуги
        """
        # Находим центр окружности через три точки
        d = 2 * (p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y))
        
        if abs(d) < 1e-10:
            return None  # Точки коллинеарны
        
        p1_sq = p1.x ** 2 + p1.y ** 2
        p2_sq = p2.x ** 2 + p2.y ** 2
        p3_sq = p3.x ** 2 + p3.y ** 2
        
        cx = (p1_sq * (p2.y - p3.y) + p2_sq * (p3.y - p1.y) + p3_sq * (p1.y - p2.y)) / d
        cy = (p1_sq * (p3.x - p2.x) + p2_sq * (p1.x - p3.x) + p3_sq * (p2.x - p1.x)) / d
        
        center = Point(cx, cy)
        radius = center.distance_to(p1)
        
        # Вычисляем углы
        start_angle = math.degrees(math.atan2(p1.y - cy, p1.x - cx))
        mid_angle = math.degrees(math.atan2(p2.y - cy, p2.x - cx))
        end_angle = math.degrees(math.atan2(p3.y - cy, p3.x - cx))
        
        # Определяем направление дуги (через какую сторону идёт)
        # Проверяем, лежит ли mid_angle между start и end
        def normalize_angle(a):
            while a < 0:
                a += 360
            while a >= 360:
                a -= 360
            return a
        
        start_angle = normalize_angle(start_angle)
        mid_angle = normalize_angle(mid_angle)
        end_angle = normalize_angle(end_angle)
        
        # Вычисляем span_angle с учётом промежуточной точки
        span1 = normalize_angle(end_angle - start_angle)
        span2 = span1 - 360
        
        # Проверяем, какой span содержит mid_angle
        if span1 > 0:
            test_mid = normalize_angle(mid_angle - start_angle)
            if test_mid <= span1:
                span_angle = span1
            else:
                span_angle = span2
        else:
            test_mid = normalize_angle(mid_angle - start_angle)
            if test_mid >= span1 or test_mid <= 0:
                span_angle = span1
            else:
                span_angle = span2
        
        return cls(center, radius, start_angle, span_angle, style_name)

    # ==================== Свойства ====================
    
    @property
    def end_angle(self) -> float:
        """Конечный угол в градусах."""
        return self.start_angle + self.span_angle
    
    @property
    def start_point(self) -> Point:
        """Начальная точка дуги."""
        angle_rad = math.radians(self.start_angle)
        return Point(
            self.center.x + self.radius * math.cos(angle_rad),
            self.center.y + self.radius * math.sin(angle_rad)
        )
    
    @property
    def end_point(self) -> Point:
        """Конечная точка дуги."""
        angle_rad = math.radians(self.end_angle)
        return Point(
            self.center.x + self.radius * math.cos(angle_rad),
            self.center.y + self.radius * math.sin(angle_rad)
        )
    
    @property
    def mid_point(self) -> Point:
        """Средняя точка дуги."""
        mid_angle = self.start_angle + self.span_angle / 2
        angle_rad = math.radians(mid_angle)
        return Point(
            self.center.x + self.radius * math.cos(angle_rad),
            self.center.y + self.radius * math.sin(angle_rad)
        )
    
    @property
    def arc_length(self) -> float:
        """Длина дуги."""
        return abs(self.radius * math.radians(self.span_angle))

    # ==================== Сериализация ====================
    
    def to_dict(self) -> dict:
        return {
            "type": "arc",
            "center": self.center.to_dict(),
            "radius": self.radius,
            "start_angle": self.start_angle,
            "span_angle": self.span_angle,
            "style": self.style_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'Arc':
        center = Point.from_dict(data["center"])
        radius = float(data["radius"])
        start_angle = float(data["start_angle"])
        span_angle = float(data["span_angle"])
        style_name = data.get("style", "Сплошная основная")
        return Arc(center, radius, start_angle, span_angle, style_name)

    # ==================== Объектные привязки ====================
    
    def get_snap_points(self) -> List[SnapPoint]:
        """
        Возвращает точки привязки: центр, концы, середина дуги.
        """
        start = self.start_point
        end = self.end_point
        mid = self.mid_point
        
        return [
            SnapPoint(self.center.x, self.center.y, SnapType.CENTER, self),
            SnapPoint(start.x, start.y, SnapType.ENDPOINT, self),
            SnapPoint(end.x, end.y, SnapType.ENDPOINT, self),
            SnapPoint(mid.x, mid.y, SnapType.MIDPOINT, self),
        ]

    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает контрольные точки: центр, начало, конец, середина (для радиуса).
        """
        start = self.start_point
        end = self.end_point
        mid = self.mid_point
        
        return [
            ControlPoint(self.center.x, self.center.y, "Центр", 0),
            ControlPoint(start.x, start.y, "Начало", 1),
            ControlPoint(end.x, end.y, "Конец", 2),
            ControlPoint(mid.x, mid.y, "Радиус", 3),
        ]
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку.
        index=0: центр, index=1: начало, index=2: конец, index=3: середина (радиус)
        """
        if index == 0:
            # Перемещение центра (сохраняем радиус и углы)
            self.center = Point(new_x, new_y)
            return True
        elif index == 1:
            # Изменение начальной точки (меняется start_angle)
            new_start_angle = math.degrees(math.atan2(new_y - self.center.y, new_x - self.center.x))
            # Пересчитываем span_angle, сохраняя конечный угол
            old_end_angle = self.end_angle
            self.start_angle = new_start_angle
            self.span_angle = old_end_angle - new_start_angle
            if abs(self.span_angle) > 360:
                self.span_angle = self.span_angle % 360
            return True
        elif index == 2:
            # Изменение конечной точки (меняется span_angle)
            new_end_angle = math.degrees(math.atan2(new_y - self.center.y, new_x - self.center.x))
            self.span_angle = new_end_angle - self.start_angle
            if self.span_angle < -360:
                self.span_angle += 360
            elif self.span_angle > 360:
                self.span_angle -= 360
            return True
        elif index == 3:
            # Изменение радиуса через среднюю точку
            new_radius = self.center.distance_to(Point(new_x, new_y))
            if new_radius > 0:
                self.radius = new_radius
                return True
        return False

    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """
        Возвращает ограничивающий прямоугольник.
        Учитывает, какие квадранты пересекает дуга.
        """
        points = [self.start_point, self.end_point]
        
        # Проверяем, пересекает ли дуга квадранты (0°, 90°, 180°, 270°)
        start = self.start_angle % 360
        end = (self.start_angle + self.span_angle) % 360
        
        for quad_angle in [0, 90, 180, 270]:
            if self._angle_in_arc(quad_angle):
                angle_rad = math.radians(quad_angle)
                points.append(Point(
                    self.center.x + self.radius * math.cos(angle_rad),
                    self.center.y + self.radius * math.sin(angle_rad)
                ))
        
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        
        return (min(xs), min(ys), max(xs), max(ys))
    
    def _angle_in_arc(self, angle: float) -> bool:
        """Проверяет, находится ли угол внутри дуги."""
        angle = angle % 360
        start = self.start_angle % 360
        span = self.span_angle
        
        if span >= 0:
            if start + span > 360:
                return angle >= start or angle <= (start + span) % 360
            else:
                return start <= angle <= start + span
        else:
            if start + span < 0:
                return angle <= start or angle >= (start + span) % 360
            else:
                return start + span <= angle <= start
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет минимальное расстояние от точки до дуги.
        """
        # Угол от центра до точки
        angle_to_point = math.degrees(math.atan2(y - self.center.y, x - self.center.x))
        angle_to_point = angle_to_point % 360
        
        # Если точка "смотрит" на дугу, расстояние = |dist_to_center - radius|
        if self._angle_in_arc(angle_to_point):
            dist_to_center = math.sqrt((x - self.center.x)**2 + (y - self.center.y)**2)
            return abs(dist_to_center - self.radius)
        else:
            # Иначе - расстояние до ближайшего конца
            start = self.start_point
            end = self.end_point
            d1 = math.sqrt((x - start.x)**2 + (y - start.y)**2)
            d2 = math.sqrt((x - end.x)**2 + (y - end.y)**2)
            return min(d1, d2)
    
    def point_at_angle(self, angle: float) -> Point:
        """
        Возвращает точку на дуге по углу (в градусах).
        """
        angle_rad = math.radians(angle)
        return Point(
            self.center.x + self.radius * math.cos(angle_rad),
            self.center.y + self.radius * math.sin(angle_rad)
        )

    def __repr__(self) -> str:
        return f"Arc({self.center}, r={self.radius:.2f}, start={self.start_angle:.1f}°, span={self.span_angle:.1f}°)"
