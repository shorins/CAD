"""
Геометрический примитив: Сплайн (кривая Безье/B-сплайн).
"""

import math
from typing import List, Tuple, Optional

from .base import GeometricPrimitive, SnapPoint, SnapType, ControlPoint
from .point import Point


class Spline(GeometricPrimitive):
    """
    Геометрический примитив: Сплайн.
    Задается набором контрольных точек.
    Использует кубические кривые Безье для интерполяции.
    
    Способы создания:
    - По набору контрольных точек (конструктор)
    
    Редактирование:
    - Добавление, удаление и перемещение контрольных точек
    """
    
    def __init__(self, control_points: List[Point], closed: bool = False,
                 style_name: str = "Сплошная основная"):
        """
        Args:
            control_points: Список контрольных точек (минимум 2)
            closed: Замкнутый ли сплайн
            style_name: Стиль линии
        """
        super().__init__(style_name)
        self.control_points = control_points if control_points else []
        self.closed = closed
        self._cached_curve_points: Optional[List[Point]] = None

    # ==================== Управление точками ====================
    
    def add_point(self, point: Point, index: Optional[int] = None):
        """
        Добавляет контрольную точку.
        
        Args:
            point: Точка для добавления
            index: Позиция вставки (None = в конец)
        """
        if index is None:
            self.control_points.append(point)
        else:
            self.control_points.insert(index, point)
        self._cached_curve_points = None  # Сбрасываем кэш
    
    def remove_point(self, index: int) -> bool:
        """
        Удаляет контрольную точку по индексу.
        Минимум должны остаться 2 точки.
        """
        if len(self.control_points) <= 2:
            return False
        
        if 0 <= index < len(self.control_points):
            self.control_points.pop(index)
            self._cached_curve_points = None
            return True
        return False
    
    def move_point(self, index: int, new_x: float, new_y: float) -> bool:
        """Перемещает контрольную точку."""
        if 0 <= index < len(self.control_points):
            self.control_points[index] = Point(new_x, new_y)
            self._cached_curve_points = None
            return True
        return False

    # ==================== Генерация кривой ====================
    
    def get_curve_points(self, segments_per_section: int = 20) -> List[Point]:
        """
        Генерирует точки кривой для отрисовки.
        Использует кубические кривые Безье с автоматическим вычислением касательных.
        
        Args:
            segments_per_section: Количество сегментов между каждой парой контрольных точек
        """
        if self._cached_curve_points is not None:
            return self._cached_curve_points
        
        if len(self.control_points) < 2:
            self._cached_curve_points = list(self.control_points)
            return self._cached_curve_points
        
        result = []
        n = len(self.control_points)
        
        # Для каждого сегмента между контрольными точками
        for i in range(n - 1 if not self.closed else n):
            p0 = self.control_points[i]
            p1 = self.control_points[(i + 1) % n]
            
            # Вычисляем касательные для плавной интерполяции
            # Используем метод Catmull-Rom
            if i == 0 and not self.closed:
                # Первая точка - направление к следующей
                t0 = Point(p1.x - p0.x, p1.y - p0.y) * 0.5
            else:
                p_prev = self.control_points[(i - 1) % n]
                t0 = Point(p1.x - p_prev.x, p1.y - p_prev.y) * 0.5
            
            if i == n - 2 and not self.closed:
                # Последний сегмент - направление от предыдущей
                t1 = Point(p1.x - p0.x, p1.y - p0.y) * 0.5
            else:
                p_next = self.control_points[(i + 2) % n]
                t1 = Point(p_next.x - p0.x, p_next.y - p0.y) * 0.5
            
            # Генерируем точки кривой Безье
            for j in range(segments_per_section):
                t = j / segments_per_section
                point = self._hermite_interpolate(p0, p1, t0, t1, t)
                result.append(point)
        
        # Добавляем последнюю точку
        if not self.closed:
            result.append(self.control_points[-1])
        else:
            result.append(result[0])  # Замыкаем
        
        self._cached_curve_points = result
        return result
    
    def _hermite_interpolate(self, p0: Point, p1: Point, 
                              m0: Point, m1: Point, t: float) -> Point:
        """
        Интерполяция Эрмита для плавной кривой.
        
        Args:
            p0, p1: Точки
            m0, m1: Касательные
            t: Параметр [0, 1]
        """
        t2 = t * t
        t3 = t2 * t
        
        # Коэффициенты Эрмита
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        
        x = h00 * p0.x + h10 * m0.x + h01 * p1.x + h11 * m1.x
        y = h00 * p0.y + h10 * m0.y + h01 * p1.y + h11 * m1.y
        
        return Point(x, y)

    # ==================== Свойства ====================
    
    @property
    def num_points(self) -> int:
        """Количество контрольных точек."""
        return len(self.control_points)
    
    @property
    def approximate_length(self) -> float:
        """Приблизительная длина кривой."""
        curve_points = self.get_curve_points()
        if len(curve_points) < 2:
            return 0
        
        length = 0
        for i in range(len(curve_points) - 1):
            length += curve_points[i].distance_to(curve_points[i + 1])
        return length

    # ==================== Сериализация ====================

    def to_dict(self) -> dict:
        return {
            "type": "spline",
            "control_points": [p.to_dict() for p in self.control_points],
            "closed": self.closed,
            "style": self.style_name
        }

    @staticmethod
    def from_dict(data: dict) -> 'Spline':
        control_points = [Point.from_dict(p) for p in data["control_points"]]
        closed = data.get("closed", False)
        style_name = data.get("style", "Сплошная основная")
        return Spline(control_points, closed, style_name)

    # ==================== Объектные привязки ====================
    
    def get_snap_points(self) -> List[SnapPoint]:
        """
        Возвращает точки привязки: контрольные точки (NODE).
        """
        points = []
        
        for cp in self.control_points:
            points.append(SnapPoint(cp.x, cp.y, SnapType.NODE, self))
        
        # Добавляем концы как ENDPOINT
        if len(self.control_points) >= 2 and not self.closed:
            points.append(SnapPoint(
                self.control_points[0].x, 
                self.control_points[0].y, 
                SnapType.ENDPOINT, self
            ))
            points.append(SnapPoint(
                self.control_points[-1].x, 
                self.control_points[-1].y, 
                SnapType.ENDPOINT, self
            ))
        
        return points

    # ==================== Контрольные точки ====================
    
    def get_control_points(self) -> List[ControlPoint]:
        """
        Возвращает все контрольные точки сплайна.
        """
        result = []
        for i, cp in enumerate(self.control_points):
            result.append(ControlPoint(cp.x, cp.y, f"Точка {i + 1}", i))
        return result
    
    def move_control_point(self, index: int, new_x: float, new_y: float) -> bool:
        """Перемещает контрольную точку."""
        return self.move_point(index, new_x, new_y)

    # ==================== Геометрические расчёты ====================
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Возвращает ограничивающий прямоугольник."""
        if not self.control_points:
            return (0, 0, 0, 0)
        
        curve_points = self.get_curve_points()
        xs = [p.x for p in curve_points]
        ys = [p.y for p in curve_points]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def distance_to_point(self, x: float, y: float) -> float:
        """
        Вычисляет минимальное расстояние от точки до кривой.
        """
        curve_points = self.get_curve_points()
        if len(curve_points) < 2:
            if len(curve_points) == 1:
                return math.sqrt((x - curve_points[0].x)**2 + (y - curve_points[0].y)**2)
            return float('inf')
        
        min_dist = float('inf')
        
        for i in range(len(curve_points) - 1):
            p1 = curve_points[i]
            p2 = curve_points[i + 1]
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

    def __repr__(self) -> str:
        return f"Spline({len(self.control_points)} points, closed={self.closed})"
