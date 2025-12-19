"""
Менеджер объектных привязок (Object Snap Manager).

Обеспечивает:
- Поиск точек привязки по курсору
- Настройку активных типов привязок
- Визуализацию привязок
"""

import math
from typing import List, Optional, Set
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal

from .geometry import SnapPoint, SnapType, GeometricPrimitive


@dataclass
class SnapResult:
    """Результат поиска привязки."""
    point: SnapPoint
    screen_x: float  # Экранные координаты для отображения
    screen_y: float
    distance: float  # Расстояние до курсора (в сценовых единицах)


class SnapManager(QObject):
    """
    Менеджер объектных привязок.
    
    Отвечает за:
    - Хранение активных типов привязок
    - Поиск ближайшей привязки к курсору
    - Сигналы об изменении настроек привязок
    """
    
    # Сигнал при изменении настроек привязок
    snap_settings_changed = Signal()
    
    # Сигнал при нахождении точки привязки (x, y, snap_type)
    snap_found = Signal(float, float, str)
    
    def __init__(self):
        super().__init__()
        
        # Активные типы привязок
        self._active_snaps: Set[SnapType] = {
            SnapType.ENDPOINT,
            SnapType.MIDPOINT,
            SnapType.CENTER,
            SnapType.INTERSECTION,
            SnapType.PERPENDICULAR,
            SnapType.TANGENT,
        }
        
        # Радиус захвата привязки в пикселях экрана
        self.snap_radius = 15.0
        
        # Глобальное включение/выключение привязок
        self.enabled = True
        
        # Последняя найденная привязка (для отображения)
        self._current_snap: Optional[SnapResult] = None

    # ==================== Настройки привязок ====================
    
    def is_snap_active(self, snap_type: SnapType) -> bool:
        """Проверяет, активен ли тип привязки."""
        return snap_type in self._active_snaps
    
    def set_snap_active(self, snap_type: SnapType, active: bool):
        """Включает или выключает тип привязки."""
        if active:
            self._active_snaps.add(snap_type)
        else:
            self._active_snaps.discard(snap_type)
        self.snap_settings_changed.emit()
    
    def toggle_snap(self, snap_type: SnapType):
        """Переключает тип привязки."""
        if snap_type in self._active_snaps:
            self._active_snaps.discard(snap_type)
        else:
            self._active_snaps.add(snap_type)
        self.snap_settings_changed.emit()
    
    def get_active_snaps(self) -> Set[SnapType]:
        """Возвращает множество активных типов привязок."""
        return self._active_snaps.copy()
    
    def set_active_snaps(self, snap_types: Set[SnapType]):
        """Устанавливает активные типы привязок."""
        self._active_snaps = snap_types.copy()
        self.snap_settings_changed.emit()
    
    def enable_all(self):
        """Включает все типы привязок."""
        self._active_snaps = set(SnapType)
        self.snap_settings_changed.emit()
    
    def disable_all(self):
        """Выключает все типы привязок."""
        self._active_snaps.clear()
        self.snap_settings_changed.emit()
    
    def set_enabled(self, enabled: bool):
        """Глобальное включение/выключение привязок."""
        self.enabled = enabled
        self.snap_settings_changed.emit()

    # ==================== Поиск привязок ====================
    
    def find_snap(self, scene_x: float, scene_y: float, 
                  objects: List[GeometricPrimitive],
                  tolerance: float = 10.0,
                  exclude_object: Optional[GeometricPrimitive] = None,
                  reference_point: Optional['Point'] = None) -> Optional[SnapPoint]:
        """
        Ищет ближайшую точку привязки к заданным координатам.
        
        Args:
            scene_x, scene_y: Координаты в сцене
            objects: Список геометрических объектов для поиска
            tolerance: Максимальное расстояние в сценовых единицах
            exclude_object: Объект, который нужно исключить из поиска
            reference_point: Точка отсчета для контекстных привязок (перпендикуляр, касательная)
            
        Returns:
            Ближайшая точка привязки или None
        """
        if not self.enabled or not self._active_snaps:
            self._current_snap = None
            return None
        
        best_snap: Optional[SnapPoint] = None
        best_distance = tolerance
        
        # Фильтруем объекты рядом с курсором для оптимизации
        nearby_objects = []
        search_radius = tolerance * 2  # Расширенный радиус поиска
        
        for obj in objects:
            if obj is exclude_object:
                continue
            if obj.distance_to_point(scene_x, scene_y) <= search_radius:
                nearby_objects.append(obj)
        
        # 1. Стандартные привязки (Endpoint, Midpoint, Center, Quadrant, Node)
        for obj in nearby_objects:
            snap_points = obj.get_snap_points()
            for sp in snap_points:
                if sp.snap_type not in self._active_snaps:
                    continue
                
                dist = sp.distance_to(scene_x, scene_y)
                if dist < best_distance:
                    best_distance = dist
                    best_snap = sp

        # 2. Пересечения (Intersection)
        if SnapType.INTERSECTION in self._active_snaps:
            import itertools
            for obj1, obj2 in itertools.combinations(nearby_objects, 2):
                intersections = self.find_intersection(obj1, obj2)
                for sp in intersections:
                    dist = sp.distance_to(scene_x, scene_y)
                    if dist < best_distance:
                        best_distance = dist
                        best_snap = sp

        # 3. Контекстные привязки (Perpendicular, Tangent)
        if reference_point:
            can_snap_perp = SnapType.PERPENDICULAR in self._active_snaps
            can_snap_tan = SnapType.TANGENT in self._active_snaps
            
            if can_snap_perp or can_snap_tan:
                from .geometry import Point
                # Убедимся что reference_point это Point (вдруг передали tuple)
                if isinstance(reference_point, (tuple, list)):
                    ref_pt = (reference_point[0], reference_point[1])
                else:
                    ref_pt = (reference_point.x, reference_point.y)

                for obj in nearby_objects:
                    # Perpendicular
                    if can_snap_perp:
                        perp_pt = self.find_perpendicular(ref_pt, obj)
                        if perp_pt:
                            dist = perp_pt.distance_to(scene_x, scene_y)
                            if dist < best_distance:
                                best_distance = dist
                                best_snap = perp_pt
                    
                    # Tangent
                    if can_snap_tan:
                        tan_pts = self.find_tangent(ref_pt, obj)
                        for tan_pt in tan_pts:
                            dist = tan_pt.distance_to(scene_x, scene_y)
                            if dist < best_distance:
                                best_distance = dist
                                best_snap = tan_pt
        
        return best_snap
    
    def find_snap_screen(self, screen_x: float, screen_y: float,
                         objects: List[GeometricPrimitive],
                         map_to_scene_func,
                         zoom_factor: float = 1.0,
                         exclude_object: Optional[GeometricPrimitive] = None,
                         reference_point: Optional['Point'] = None) -> Optional[SnapResult]:
        """
        Ищет привязку по экранным координатам.
        """
        if not self.enabled:
            self._current_snap = None
            return None
        
        from PySide6.QtCore import QPointF
        
        # Преобразуем экранные координаты в сценовые
        scene_pos = map_to_scene_func(QPointF(screen_x, screen_y))
        
        # Tolerance в сценовых единицах = snap_radius / zoom_factor
        tolerance = self.snap_radius / zoom_factor
        
        snap_point = self.find_snap(scene_pos.x(), scene_pos.y(), 
                                    objects, tolerance, exclude_object, reference_point)
        
        if snap_point:
            result = SnapResult(
                point=snap_point,
                screen_x=screen_x,
                screen_y=screen_y,
                distance=snap_point.distance_to(scene_pos.x(), scene_pos.y())
            )
            self._current_snap = result
            return result
        
        self._current_snap = None
        return None
    
    def get_current_snap(self) -> Optional[SnapResult]:
        """Возвращает последнюю найденную привязку."""
        return self._current_snap
    
    def clear_current_snap(self):
        """Очищает текущую привязку."""
        self._current_snap = None

    # ==================== Вспомогательные методы ====================
    
    def find_intersection(self, obj1: GeometricPrimitive, 
                          obj2: GeometricPrimitive) -> List[SnapPoint]:
        """Находит точки пересечения двух объектов."""
        from .geometry import Line, Circle, Arc, Point
        
        intersections = []
        
        # Line - Line
        if isinstance(obj1, Line) and isinstance(obj2, Line):
            pt = self._intersect_line_line(obj1, obj2)
            if pt:
                intersections.append(SnapPoint(pt.x, pt.y, SnapType.INTERSECTION, obj1))
                
        # Line - Circle (and Circle - Line)
        elif isinstance(obj1, Line) and isinstance(obj2, (Circle, Arc)):
             pts = self._intersect_line_circle(obj1, obj2)
             for pt in pts:
                 intersections.append(SnapPoint(pt.x, pt.y, SnapType.INTERSECTION, obj2))
        elif isinstance(obj1, (Circle, Arc)) and isinstance(obj2, Line):
             pts = self._intersect_line_circle(obj2, obj1)
             for pt in pts:
                 intersections.append(SnapPoint(pt.x, pt.y, SnapType.INTERSECTION, obj1))
                 
        # Circle - Circle
        elif isinstance(obj1, (Circle, Arc)) and isinstance(obj2, (Circle, Arc)):
            pts = self._intersect_circle_circle(obj1, obj2)
            for pt in pts:
                intersections.append(SnapPoint(pt.x, pt.y, SnapType.INTERSECTION, obj1))
                
        return intersections
    
    def find_perpendicular(self, from_point: tuple, 
                           to_object: GeometricPrimitive) -> Optional[SnapPoint]:
        """Находит точку перпендикуляра от точки к объекту."""
        from .geometry import Line, Circle, Arc, Point
        
        fx, fy = from_point
        pt = Point(fx, fy)
        
        if isinstance(to_object, Line):
            perp = to_object.get_perpendicular_point(pt)
            return SnapPoint(perp.x, perp.y, SnapType.PERPENDICULAR, to_object)
            
        elif isinstance(to_object, (Circle, Arc)):
            return to_object.get_nearest_point(fx, fy)
            
        return None

    def find_tangent(self, from_point: tuple,
                     to_object: GeometricPrimitive) -> List[SnapPoint]:
        """Находит точки касания."""
        from .geometry import Circle, Arc, Point
        
        fx, fy = from_point
        snaps = []
        
        if isinstance(to_object, (Circle, Arc)):
            center = to_object.center
            radius = to_object.radius
            
            dx = center.x - fx
            dy = center.y - fy
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist >= radius:
                angle_to_center = math.atan2(dy, dx)
                try:
                    alpha = math.acos(radius / dist)
                    
                    # Точка 1
                    t1_x = center.x + radius * math.cos(angle_to_center + alpha)
                    t1_y = center.y + radius * math.sin(angle_to_center + alpha)
                    snaps.append(SnapPoint(t1_x, t1_y, SnapType.TANGENT, to_object))
                    
                    # Точка 2
                    t2_x = center.x + radius * math.cos(angle_to_center - alpha)
                    t2_y = center.y + radius * math.sin(angle_to_center - alpha)
                    snaps.append(SnapPoint(t2_x, t2_y, SnapType.TANGENT, to_object))
                    
                except ValueError:
                    pass
             
        return snaps
    
    def _intersect_line_line(self, l1, l2):
        """Пересечение двух отрезков (как прямых)."""
        from .geometry import Point
        
        x1, y1 = l1.start.x, l1.start.y
        x2, y2 = l1.end.x, l1.end.y
        x3, y3 = l2.start.x, l2.start.y
        x4, y4 = l2.end.x, l2.end.y
        
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return None  # Параллельны
            
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        
        # Проверяем, лежит ли пересечение внутри отрезков
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            return Point(x, y)
        return None

    def _intersect_line_circle(self, line, circle):
        """Пересечение отрезка и окружности."""
        from .geometry import Point
        
        x1, y1 = line.start.x, line.start.y
        x2, y2 = line.end.x, line.end.y
        cx, cy = circle.center.x, circle.center.y
        r = circle.radius
        
        dx = x2 - x1
        dy = y2 - y1
        
        fx = x1 - cx
        fy = y1 - cy
        
        a = dx*dx + dy*dy
        b = 2 * (fx*dx + fy*dy)
        c = (fx*fx + fy*fy) - r*r
        
        discriminant = b*b - 4*a*c
        
        points = []
        if discriminant < 0:
            return points
        
        t1 = (-b - math.sqrt(discriminant)) / (2*a)
        t2 = (-b + math.sqrt(discriminant)) / (2*a)
        
        for t in [t1, t2]:
            if 0 <= t <= 1: # Проверка на принадлежность отрезку
                points.append(Point(x1 + t*dx, y1 + t*dy))
                
        return points

    def _intersect_circle_circle(self, c1, c2):
        """Пересечение двух окружностей."""
        from .geometry import Point
        
        x1, y1 = c1.center.x, c1.center.y
        r1 = c1.radius
        x2, y2 = c2.center.x, c2.center.y
        r2 = c2.radius
        
        d_sq = (x1 - x2)**2 + (y1 - y2)**2
        d = math.sqrt(d_sq)
        
        if d > r1 + r2 or d < abs(r1 - r2) or d == 0:
            return []
            
        a = (r1**2 - r2**2 + d_sq) / (2 * d)
        h = math.sqrt(max(0, r1**2 - a**2))
        
        x2_rel = x2 - x1
        y2_rel = y2 - y1
        
        x3 = x1 + a * (x2_rel / d)
        y3 = y1 + a * (y2_rel / d)
        
        x4_1 = x3 + h * (y2_rel / d)
        y4_1 = y3 - h * (x2_rel / d)
        
        x4_2 = x3 - h * (y2_rel / d)
        y4_2 = y3 + h * (x2_rel / d)
        
        return [Point(x4_1, y4_1), Point(x4_2, y4_2)]

    # ==================== Сериализация ====================
    
    def to_dict(self) -> dict:
        """Сохраняет настройки привязок."""
        return {
            "enabled": self.enabled,
            "snap_radius": self.snap_radius,
            "active_snaps": [st.name for st in self._active_snaps],
        }
    
    def from_dict(self, data: dict):
        """Загружает настройки привязок."""
        self.enabled = data.get("enabled", True)
        self.snap_radius = data.get("snap_radius", 15.0)
        
        active_names = data.get("active_snaps", [])
        self._active_snaps = set()
        for name in active_names:
            try:
                self._active_snaps.add(SnapType[name])
            except KeyError:
                pass  # Игнорируем неизвестные типы
        
        self.snap_settings_changed.emit()


# Глобальный экземпляр менеджера привязок
snap_manager = SnapManager()
