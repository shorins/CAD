"""
Геометрический примитив: Дуга.
Поддерживает несколько способов создания.
"""

import math
from typing import List, Tuple, Optional

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class Arc(GeometricPrimitive):
    """
    Геометрический примитив: Дуга окружности.
    Задается центром, радиусом, начальным и конечным углом.
    
    Способы создания:
    - Центр, радиус, углы (конструктор)
    - Три точки (from_three_points)
    - Центр и углы в градусах (from_center_and_angles)
    
    Углы хранятся в градусах в математической системе координат:
    - 0° = вправо (ось X+)
    - 90° = вверх (ось Y+)
    - Положительное направление = против часовой стрелки
    """
    
    EPSILON = 1e-10  # Для проверки коллинеарности
    
    def __init__(self, center: Point, radius: float, 
                 start_angle: float, span_angle: float,
                 style_name: str = "Сплошная основная"):
        """
        Создаёт дугу.
        
        Args:
            center: Центр окружности
            radius: Радиус
            start_angle: Начальный угол в градусах (математическая система: 0° вправо, против часовой)
            span_angle: Угол развёртки в градусах (положительный = против часовой)
            style_name: Имя стиля линии
        """
        super().__init__(style_name)
        self.center = center
        self.radius = abs(radius)
        self.start_angle = start_angle
        self.span_angle = span_angle
    
    # ==================== Альтернативные конструкторы ====================
    
    @classmethod
    def from_center_and_angles(cls, center: Point, radius: float,
                                start_angle_deg: float, end_angle_deg: float,
                                style_name: str = "Сплошная основная",
                                shortest_path: bool = False) -> 'Arc':
        """
        Создание дуги по центру, радиусу и углам (в градусах).
        
        Args:
            center: Центр окружности
            radius: Радиус
            start_angle_deg: Начальный угол в градусах
            end_angle_deg: Конечный угол в градусах
            style_name: Имя стиля
            shortest_path: Если True, строит дугу по кратчайшему пути (span от -180 до 180).
                           Если False, строит всегда против часовой стрелки (span > 0).
        """
        # Вычисляем span_angle (угол развёртки)
        span = end_angle_deg - start_angle_deg
        
        # Нормализуем span к (-360, 360)
        while span <= -360:
            span += 360
        while span >= 360:
            span -= 360
            
        if shortest_path:
            # Кратчайший путь: [-180, 180]
            if span > 180:
                span -= 360
            elif span <= -180:
                span += 360
        else:
            # Только положительный (против часовой)
            if span < 0:
                span += 360
            # Если span = 0, делаем полный круг (только для режима CCW)
            if abs(span) < cls.EPSILON:
                span = 360
        
        return cls(center, radius, start_angle_deg, span, style_name)
    
    @classmethod
    def from_three_points(cls, p1: Point, p2: Point, p3: Point,
                          style_name: str = "Сплошная основная") -> Optional['Arc']:
        """
        Создание дуги через три точки.
        
        Дуга проходит от p1 (начало) до p3 (конец), через p2 (точка на дуге).
        
        Args:
            p1: Начальная точка дуги
            p2: Точка на дуге (определяет направление изгиба)
            p3: Конечная точка дуги
            style_name: Имя стиля
            
        Returns:
            Arc или None если точки коллинеарны
        """
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y
        
        # Вычисление определителя для проверки коллинеарности
        delta = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        
        if abs(delta) < cls.EPSILON:
            return None  # Точки коллинеарны
        
        # Вычисляем центр окружности
        x1_sq_y1_sq = x1 ** 2 + y1 ** 2
        x2_sq_y2_sq = x2 ** 2 + y2 ** 2
        x3_sq_y3_sq = x3 ** 2 + y3 ** 2
        
        cx = (x1_sq_y1_sq * (y2 - y3) + 
              x2_sq_y2_sq * (y3 - y1) + 
              x3_sq_y3_sq * (y1 - y2)) / delta
        
        cy = (x1_sq_y1_sq * (x3 - x2) + 
              x2_sq_y2_sq * (x1 - x3) + 
              x3_sq_y3_sq * (x2 - x1)) / delta
        
        center = Point(cx, cy)
        radius = p1.distance_to(center)
        
        # Вычисляем углы всех трёх точек относительно центра
        theta1 = math.atan2(y1 - cy, x1 - cx)
        theta2 = math.atan2(y2 - cy, x2 - cx)
        theta3 = math.atan2(y3 - cy, x3 - cx)
        
        # Нормализуем углы к [0, 2π)
        def normalize_angle(angle: float) -> float:
            while angle < 0:
                angle += 2 * math.pi
            while angle >= 2 * math.pi:
                angle -= 2 * math.pi
            return angle
        
        theta1 = normalize_angle(theta1)
        theta2 = normalize_angle(theta2)
        theta3 = normalize_angle(theta3)
        
        # Определяем направление дуги
        # Дуга идёт от theta1 к theta3 и должна пройти через theta2
        # Проверяем, в каком направлении нужно идти от theta1 к theta3, чтобы пройти через theta2
        
        # CCW (против часовой): если theta2 лежит между theta1 и theta3 при движении CCW
        # CW (по часовой): если theta2 лежит между theta1 и theta3 при движении CW
        
        def angle_between_ccw(start: float, end: float) -> float:
            """Угол от start до end при движении CCW (положительное направление)"""
            diff = end - start
            while diff < 0:
                diff += 2 * math.pi
            while diff >= 2 * math.pi:
                diff -= 2 * math.pi
            return diff
        
        # Угол от theta1 до theta3 CCW
        span_ccw = angle_between_ccw(theta1, theta3)
        
        # Угол от theta1 до theta2 CCW
        to_p2_ccw = angle_between_ccw(theta1, theta2)
        
        # Если theta2 находится "внутри" дуги CCW (между theta1 и theta3),
        # то идём CCW, иначе CW
        if to_p2_ccw < span_ccw or abs(to_p2_ccw - span_ccw) < cls.EPSILON:
            # CCW направление правильное
            span_angle_deg = math.degrees(span_ccw)
        else:
            # Нужно идти CW (отрицательный span)
            span_cw = 2 * math.pi - span_ccw
            span_angle_deg = -math.degrees(span_cw)
        
        start_angle_deg = math.degrees(theta1)
        
        return cls(center, radius, start_angle_deg, span_angle_deg, style_name)
    
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
        mid_angle_rad = math.radians(self.start_angle + self.span_angle / 2)
        return Point(
            self.center.x + self.radius * math.cos(mid_angle_rad),
            self.center.y + self.radius * math.sin(mid_angle_rad)
        )
    
    @property
    def arc_length(self) -> float:
        """Длина дуги."""
        return abs(self.radius * math.radians(self.span_angle))
    
    @property
    def chord_length(self) -> float:
        """Длина хорды (расстояние между начальной и конечной точками)."""
        return self.start_point.distance_to(self.end_point)
    
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
        Возвращает точки привязки: центр, начало, конец, середина.
        """
        points = [
            SnapPoint(self.center.x, self.center.y, SnapType.CENTER, self),
            SnapPoint(self.start_point.x, self.start_point.y, SnapType.ENDPOINT, self),
            SnapPoint(self.end_point.x, self.end_point.y, SnapType.ENDPOINT, self),
            SnapPoint(self.mid_point.x, self.mid_point.y, SnapType.MIDPOINT, self),
        ]
        
        # Добавляем квадранты, которые попадают в дугу
        for angle_deg in [0, 90, 180, 270]:
            if self._angle_is_on_arc(angle_deg):
                angle_rad = math.radians(angle_deg)
                x = self.center.x + self.radius * math.cos(angle_rad)
                y = self.center.y + self.radius * math.sin(angle_rad)
                points.append(SnapPoint(x, y, SnapType.QUADRANT, self))
        
        return points
    
    def _angle_is_on_arc(self, angle_deg: float) -> bool:
        """Проверяет, находится ли угол в пределах дуги."""
        # Нормализуем все углы
        def normalize(a):
            while a < 0:
                a += 360
            while a >= 360:
                a -= 360
            return a
        
        angle = normalize(angle_deg)
        start = normalize(self.start_angle)
        
        if self.span_angle >= 0:
            # CCW направление
            end = normalize(self.start_angle + self.span_angle)
            if start <= end:
                return start <= angle <= end
            else:
                # Дуга пересекает 0°
                return angle >= start or angle <= end
        else:
            # CW направление
            end = normalize(self.start_angle + self.span_angle)
            if end <= start:
                return end <= angle <= start
            else:
                # Дуга пересекает 0°
                return angle <= start or angle >= end
    
    def get_nearest_point(self, x: float, y: float) -> SnapPoint:
        """Возвращает ближайшую точку на дуге."""
        # Угол от центра к данной точке
        angle = math.degrees(math.atan2(y - self.center.y, x - self.center.x))
        
        # Если угол на дуге - проецируем на дугу
        if self._angle_is_on_arc(angle):
            angle_rad = math.radians(angle)
            px = self.center.x + self.radius * math.cos(angle_rad)
            py = self.center.y + self.radius * math.sin(angle_rad)
            return SnapPoint(px, py, SnapType.NEAREST, self)
        
        # Иначе возвращаем ближайшую конечную точку
        start = self.start_point
        end = self.end_point
        
        dist_to_start = math.sqrt((x - start.x) ** 2 + (y - start.y) ** 2)
        dist_to_end = math.sqrt((x - end.x) ** 2 + (y - end.y) ** 2)
        
        if dist_to_start <= dist_to_end:
            return SnapPoint(start.x, start.y, SnapType.ENDPOINT, self)
        else:
            return SnapPoint(end.x, end.y, SnapType.ENDPOINT, self)
    
    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает контрольные точки: центр, начало и конец дуги.
        """
        return [
            ControlPoint(self.center.x, self.center.y, "Центр", 0),
            ControlPoint(self.start_point.x, self.start_point.y, "Начало", 1),
            ControlPoint(self.end_point.x, self.end_point.y, "Конец", 2),
        ]
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """
        Перемещает контрольную точку.
        index=0: центр, index=1: начало, index=2: конец
        """
        if index == 0:
            # Перемещение центра (всей дуги)
            self.center = Point(new_x, new_y)
            return True
        
        elif index == 1:
            # Изменение начального угла/радиуса
            new_radius = self.center.distance_to(Point(new_x, new_y))
            if new_radius > 0:
                new_start_angle = math.degrees(math.atan2(
                    new_y - self.center.y, 
                    new_x - self.center.x
                ))
                # Сохраняем end_angle, пересчитываем span
                old_end = self.end_angle
                self.radius = new_radius
                self.start_angle = new_start_angle
                self.span_angle = old_end - new_start_angle
                return True
        
        elif index == 2:
            # Изменение конечного угла (и радиуса)
            new_radius = self.center.distance_to(Point(new_x, new_y))
            if new_radius > 0:
                new_end_angle = math.degrees(math.atan2(
                    new_y - self.center.y, 
                    new_x - self.center.x
                ))
                self.radius = new_radius
                self.span_angle = new_end_angle - self.start_angle
                return True
        
        return False
    
    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Возвращает ограничивающий прямоугольник дуги."""
        # Начальные точки
        points = [self.start_point, self.end_point]
        
        # Добавляем экстремумы (квадранты), которые попадают на дугу
        for angle_deg in [0, 90, 180, 270]:
            if self._angle_is_on_arc(angle_deg):
                angle_rad = math.radians(angle_deg)
                points.append(Point(
                    self.center.x + self.radius * math.cos(angle_rad),
                    self.center.y + self.radius * math.sin(angle_rad)
                ))
        
        x_coords = [p.x for p in points]
        y_coords = [p.y for p in points]
        
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет минимальное расстояние от точки до дуги.
        """
        # Угол от центра к точке
        angle = math.degrees(math.atan2(y - self.center.y, x - self.center.x))
        
        # Расстояние до центра
        dist_to_center = math.sqrt((x - self.center.x) ** 2 + (y - self.center.y) ** 2)
        
        if self._angle_is_on_arc(angle):
            # Точка "видит" дугу - расстояние до дуги
            return abs(dist_to_center - self.radius)
        
        # Иначе - расстояние до ближайшей конечной точки
        start = self.start_point
        end = self.end_point
        
        dist_to_start = math.sqrt((x - start.x) ** 2 + (y - start.y) ** 2)
        dist_to_end = math.sqrt((x - end.x) ** 2 + (y - end.y) ** 2)
        
        return min(dist_to_start, dist_to_end)
    
    def point_at_angle(self, angle: float) -> Point:
        """
        Возвращает точку на дуге по углу (в градусах).
        
        Args:
            angle: Угол в градусах
        """
        angle_rad = math.radians(angle)
        return Point(
            self.center.x + self.radius * math.cos(angle_rad),
            self.center.y + self.radius * math.sin(angle_rad)
        )
    
    def get_arc_points(self, num_segments: int = 100) -> List[Point]:
        """
        Генерирует список точек для отрисовки дуги полилинией.
        
        Args:
            num_segments: Количество сегментов для аппроксимации
            
        Returns:
            Список точек на дуге
        """
        points = []
        
        for i in range(num_segments + 1):
            t = i / num_segments
            angle_deg = self.start_angle + t * self.span_angle
            angle_rad = math.radians(angle_deg)
            
            x = self.center.x + self.radius * math.cos(angle_rad)
            y = self.center.y + self.radius * math.sin(angle_rad)
            
            points.append(Point(x, y))
        
        return points
    
    def __repr__(self) -> str:
        return (f"Arc({self.center}, r={self.radius:.2f}, "
                f"start={self.start_angle:.1f}°, span={self.span_angle:.1f}°, "
                f"style='{self.style_name}')")
