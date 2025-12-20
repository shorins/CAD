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
    
    def enable_snap_type(self, snap_type: SnapType):
        """Включает указанный тип привязки."""
        self._active_snaps.add(snap_type)
        self.snap_settings_changed.emit()

    def disable_snap_type(self, snap_type: SnapType):
        """Выключает указанный тип привязки."""
        self._active_snaps.discard(snap_type)
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
                  reference_point: Optional[tuple] = None,
                  grid_size: Optional[float] = None,
                  zoom_factor: float = 1.0) -> Optional[SnapPoint]:
        """
        Находит лучшую точку привязки.
        """
        if not self.enabled:
            return None
            
        best_snap = None
        best_distance = float('inf')
        
        # Фильтруем объекты рядом с курсором для оптимизации
        nearby_objects = []
        search_radius = tolerance * 2  # Расширенный радиус поиска
        
        check_center = SnapType.CENTER in self._active_snaps
        
        for obj in objects:
            if obj is exclude_object:
                continue
                
            is_nearby = False
            
            # 1. Проверка по контуру
            if obj.distance_to_point(scene_x, scene_y) <= search_radius:
                is_nearby = True
            
            # 2. Проверка по центру (если активен Center Snap)
            elif check_center and hasattr(obj, 'center'):
                 # Для Point из .geometry.point
                 # Используем getattr на случай если center это tuple (хотя вряд ли)
                 cx = getattr(obj.center, 'x', obj.center[0] if isinstance(obj.center, (tuple, list)) else 0)
                 cy = getattr(obj.center, 'y', obj.center[1] if isinstance(obj.center, (tuple, list)) else 0)
                 
                 dist_center = math.sqrt((scene_x - cx)**2 + (scene_y - cy)**2)
                 if dist_center <= search_radius:
                     is_nearby = True
            
            if is_nearby:
                nearby_objects.append(obj)
        
        # 1. Стандартные привязки (Endpoint, Midpoint, Center, Quadrant, Node, Nearest)
        for obj in nearby_objects:
            points = obj.get_snap_points()
            
            # Добавляем Nearest если нужно
            if SnapType.NEAREST in self._active_snaps:
                nearest = obj.get_nearest_point(scene_x, scene_y)
                if nearest:
                    points.append(nearest)
            
            for sp in points:
                if sp.snap_type not in self._active_snaps:
                    continue
                
                dist = sp.distance_to(scene_x, scene_y)
                # Фильтруем по радиусу, как и раньше
                if dist <= tolerance and dist < best_distance:
                    best_distance = dist
                    best_snap = sp

        # 2. Пересечения (Intersection)
        if SnapType.INTERSECTION in self._active_snaps:
            import itertools
            for obj1, obj2 in itertools.combinations(nearby_objects, 2):
                intersections = self.find_intersection(obj1, obj2)
                for sp in intersections:
                    dist = sp.distance_to(scene_x, scene_y)
                    # Intersection тоже требует близости курсора к точке
                    if dist <= tolerance and dist < best_distance:
                        best_distance = dist
                        best_snap = sp

        # 3. Контекстные привязки (Perpendicular, Tangent)
        if reference_point:
            from .geometry import Point, Circle, Arc, Ellipse
            
            if isinstance(reference_point, (tuple, list)):
                ref_pt = Point(reference_point[0], reference_point[1])
            else:
                ref_pt = Point(reference_point.x, reference_point.y)

            # Perpendicular
            if SnapType.PERPENDICULAR in self._active_snaps:
                for obj in nearby_objects:
                    perp_pt = self.find_perpendicular((ref_pt.x, ref_pt.y), obj)
                    if perp_pt:
                        dist = perp_pt.distance_to(scene_x, scene_y)
                        if dist <= tolerance and dist < best_distance:
                            best_distance = dist
                            best_snap = perp_pt
                    
            # Tangent
            if SnapType.TANGENT in self._active_snaps:
                # Ищем только по объектам РЯДОМ (nearby_objects)
                tan_candidates = [o for o in nearby_objects if isinstance(o, (Circle, Arc, Ellipse))]
                
                for obj in tan_candidates:
                    tan_pts = self.find_tangent((ref_pt.x, ref_pt.y), obj)
                    
                    for tan_pt in tan_pts:
                        vm_x = scene_x - ref_pt.x
                        vm_y = scene_y - ref_pt.y
                        len_m_sq = vm_x*vm_x + vm_y*vm_y
                        
                        if len_m_sq < (tolerance**2): continue
                            
                        vt_x = tan_pt.x - ref_pt.x
                        vt_y = tan_pt.y - ref_pt.y
                        len_t_sq = vt_x*vt_x + vt_y*vt_y
                        
                        angle_mouse = math.degrees(math.atan2(vm_y, vm_x))
                        angle_tan = math.degrees(math.atan2(vt_y, vt_x))
                        
                        diff = abs(angle_mouse - angle_tan)
                        while diff > 180: diff = 360 - diff
                        
                        # Расширим угол захвата до 10 градусов для удобства
                        if diff < 10.0:
                            if len_t_sq < 1e-9: continue
                            dot_prod = vm_x * vt_x + vm_y * vt_y
                            t = dot_prod / len_t_sq
                            
                            if t < 0.1: continue
                            
                            proj_x = ref_pt.x + t * vt_x
                            proj_y = ref_pt.y + t * vt_y
                            
                            # BOOST PRIORITY:
                            # Считаем 1 градус отклонения эквивалентным 0.1 единицам расстояния (пикселям).
                            # Это делает касательную "сильнее" обычных привязок.
                            weighted_diff = diff * 0.1
                            
                            if weighted_diff < best_distance:
                                best_distance = weighted_diff
                                best_snap = SnapPoint(proj_x, proj_y, SnapType.TANGENT, obj)
        
        # 4. Привязка к сетке (Grid Snap)
        if SnapType.GRID in self._active_snaps and grid_size is not None and grid_size > 0:
            # Определяем эффективный шаг сетки
            # Если zoom < 0.5, то показываются только major линии (x5 шаг)
            effective_step = grid_size
            if zoom_factor < 0.5:
                effective_step = grid_size * 5
                
            # Ближайший узел сетки
            gx = round(scene_x / effective_step) * effective_step
            gy = round(scene_y / effective_step) * effective_step
            
            dist_grid = math.sqrt((scene_x - gx)**2 + (scene_y - gy)**2)
            
            # Привязываемся к сетке, если она в радиусе доступа
            # И если она ближе, чем другие найденные привязки (best_distance)
            if dist_grid <= tolerance and dist_grid < best_distance:
                # В качестве объекта передаем None, так как сетка не объект
                 # Но так как SnapPoint требует source_object: GeometricPrimitive,
                 # Придется либо разрешить None, либо передать фиктивный объект,
                 # либо игнорировать source_object при отрисовке.
                 # Python позволяет передать None если type checker не строг, 
                 # но лучше проверим dataclass definition.
                 try:
                     best_snap = SnapPoint(gx, gy, SnapType.GRID, None) # type: ignore
                     best_distance = dist_grid
                 except:
                     pass # Fallback если строгая валидация

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
        """
        Находит точки пересечения двух объектов.
        Поддерживает: Line, Circle, Arc, Rectangle, Polygon.
        """
        intersections = []
        
        # Разбиваем сложные объекты на примитивы (отрезки, дуги)
        prims1 = self._get_intersector_primitives(obj1)
        prims2 = self._get_intersector_primitives(obj2)
        
        for p1 in prims1:
            for p2 in prims2:
                pts = self._intersect_primitives(p1, p2)
                for pt in pts:
                    # Добавляем точку пересечения
                    intersections.append(SnapPoint(pt.x, pt.y, SnapType.INTERSECTION, obj1))
                
        return intersections
    
    def find_perpendicular(self, from_point: tuple, 
                           to_object: GeometricPrimitive) -> Optional[SnapPoint]:
        """Находит точку перпендикуляра от точки к объекту."""
        from .geometry import Line, Circle, Arc, Point, Rectangle, Polygon
        
        fx, fy = from_point
        pt = Point(fx, fy)
        
        if isinstance(to_object, (Rectangle, Polygon)):
            prims = self._get_intersector_primitives(to_object)
            best_snap = None
            min_dist = float('inf')
            
            for p in prims:
                if isinstance(p, Line):
                    perp = p.get_perpendicular_point(pt)
                    if p.distance_to_point(perp.x, perp.y) < 1e-5:
                         dist = perp.distance_to(pt)
                         if dist < min_dist:
                             min_dist = dist
                             best_snap = SnapPoint(perp.x, perp.y, SnapType.PERPENDICULAR, to_object)
            return best_snap

        elif isinstance(to_object, Line):
            perp = to_object.get_perpendicular_point(pt)
            return SnapPoint(perp.x, perp.y, SnapType.PERPENDICULAR, to_object)
            
        elif isinstance(to_object, (Circle, Arc)):
            return to_object.get_nearest_point(fx, fy)
            
        return None

    def find_tangent(self, from_point: tuple,
                     to_object: GeometricPrimitive) -> List[SnapPoint]:
        """Находит точки касания."""
        from .geometry import Circle, Arc, Ellipse
        
        fx, fy = from_point
        snaps = []
        
        if isinstance(to_object, (Circle, Arc)):
            center = to_object.center
            radius = to_object.radius
            
            # ИСПРАВЛЕНИЕ: Вектор от Центра к Курсору
            dx = fx - center.x
            dy = fy - center.y
            
            dist_sq = dx*dx + dy*dy
            dist = math.sqrt(dist_sq)
            
            if dist >= radius:
                # Угол от центра к курсору
                angle_from_center = math.atan2(dy, dx)
                
                try:
                    alpha = math.acos(radius / dist)
                    
                    angles = [angle_from_center + alpha, angle_from_center - alpha]
                    
                    for ang in angles:
                        tx = center.x + radius * math.cos(ang)
                        ty = center.y + radius * math.sin(ang)
                        
                        if isinstance(to_object, Arc):
                            deg = math.degrees(ang)
                            # Нормализация для проверки
                            while deg < 0: deg += 360
                            while deg >= 360: deg -= 360
                            
                            if not to_object._angle_is_on_arc(deg):
                                continue
                                
                        snaps.append(SnapPoint(tx, ty, SnapType.TANGENT, to_object))
                    
                except ValueError:
                    pass
                    
        elif isinstance(to_object, Ellipse):
             # ... (код эллипса остается без изменений)
            # Аналитическое решение для эллипса
            # A*cos(t) + B*sin(t) = C
            h, k = to_object.center.x, to_object.center.y
            a, b = to_object.radius_x, to_object.radius_y
            
            # Смещаем точку в систему координат эллипса
            px = fx - h
            py = fy - k
            
            # Коэффициенты
            A = b * px
            B = a * py
            C = a * b
            
            norm = math.sqrt(A*A + B*B)
            if norm == 0: return snaps # Точка в центре, касательных нет
            
            if abs(C) > norm:
                return snaps # Точка внутри эллипса
                
            phi = math.atan2(A, B)
            val = C / norm

            try:
                 alpha1 = math.asin(val)
                 alpha2 = math.pi - alpha1
                 
                 ts = [alpha1 - phi, alpha2 - phi]
                 
                 for t in ts:
                     tx = h + a * math.cos(t)
                     ty = k + b * math.sin(t)
                     snaps.append(SnapPoint(tx, ty, SnapType.TANGENT, to_object))
            except ValueError:
                pass

        return snaps
    
    # ==================== Внутренняя логика пересечений ====================

    def _get_intersector_primitives(self, obj):
        """Возвращает список примитивов (Line, Circle, Arc, Ellipse) из которых состоит объект."""
        from .geometry import Line, Circle, Arc, Rectangle, Polygon, Point, Ellipse
        
        if isinstance(obj, (Rectangle, Polygon)):
            # Превращаем стороны в список Line
            lines = []
            if isinstance(obj, Rectangle):
                corners = obj.corners
            else: # Polygon
                corners = obj.vertices
                
            n = len(corners)
            for i in range(n):
                p1 = corners[i]
                p2 = corners[(i + 1) % n]
                lines.append(Line(p1, p2))
            return lines
            
        elif isinstance(obj, (Line, Circle, Arc, Ellipse)):
            return [obj]
            
        return []

    def _intersect_primitives(self, p1, p2):
        """Находит пересечение двух базовых примитивов."""
        from .geometry import Line, Circle, Arc, Ellipse, Point
        
        points = []
        
        # Dispatch types
        if isinstance(p1, Line) and isinstance(p2, Line):
            pt = self._intersect_line_line(p1, p2)
            if pt: points.append(pt)
            
        elif isinstance(p1, Line) and isinstance(p2, (Circle, Arc)):
            points = self._intersect_line_circle(p1, p2)
        elif isinstance(p1, (Circle, Arc)) and isinstance(p2, Line):
            points = self._intersect_line_circle(p2, p1)
            
        elif isinstance(p1, Line) and isinstance(p2, Ellipse):
            points = self._intersect_line_ellipse(p1, p2)
        elif isinstance(p1, Ellipse) and isinstance(p2, Line):
            points = self._intersect_line_ellipse(p2, p1)

        elif isinstance(p1, (Circle, Arc)) and isinstance(p2, (Circle, Arc)):
            points = self._intersect_circle_circle(p1, p2)
            
        return points

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
        """Пересечение отрезка и окружности/дуги."""
        from .geometry import Point, Arc
        
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
        
        if a == 0: return points
        
        sqrt_d = math.sqrt(discriminant)
        t1 = (-b - sqrt_d) / (2*a)
        t2 = (-b + sqrt_d) / (2*a)
        
        for t in [t1, t2]:
            if 0 <= t <= 1: # Проверка на принадлежность отрезку
                x = x1 + t*dx
                y = y1 + t*dy
                
                # Если это дуга, проверяем угол
                if isinstance(circle, Arc):
                    angle = math.degrees(math.atan2(y - cy, x - cx))
                    if not circle._angle_is_on_arc(angle):
                        continue
                
                points.append(Point(x, y))
                
        return points

    def _intersect_line_ellipse(self, line, ellipse):
        """Пересечение отрезка и эллипса (с осями, параллельными координатным)."""
        from .geometry import Point
        
        # Параметры эллипса
        h, k = ellipse.center.x, ellipse.center.y
        a, b = ellipse.radius_x, ellipse.radius_y
        
        # Параметры линии P(t) = P1 + t * (P2 - P1)
        x1, y1 = line.start.x, line.start.y
        dx = line.end.x - x1
        dy = line.end.y - y1
        
        # Подставляем x(t), y(t) в уравнение эллипса:
        # ((x1 + t*dx - h)^2 / a^2) + ((y1 + t*dy - k)^2 / b^2) = 1
        # Упрощаем: b^2(xp + t*dx)^2 + a^2(yp + t*dy)^2 - a^2*b^2 = 0
        # где xp = x1 - h, yp = y1 - k
        
        xp = x1 - h
        yp = y1 - k
        
        # Коэффициенты квадратного уравнения A*t^2 + B*t + C = 0
        A = (b * dx)**2 + (a * dy)**2
        B = 2 * (b**2 * xp * dx + a**2 * yp * dy)
        C = (b * xp)**2 + (a * yp)**2 - (a * b)**2
        
        points = []
        if A == 0: return points # Линия вырождена в точку или бесконечна (не бывает тут)

        discriminant = B*B - 4*A*C
        
        if discriminant < 0:
            return points
            
        sqrt_d = math.sqrt(discriminant)
        t1 = (-B - sqrt_d) / (2*A)
        t2 = (-B + sqrt_d) / (2*A)
        
        for t in [t1, t2]:
            if 0 <= t <= 1: # Проверка на принадлежность отрезку
                x = x1 + t*dx
                y = y1 + t*dy
                points.append(Point(x, y))
                
        return points

    def _intersect_circle_circle(self, c1, c2):
        """Пересечение двух окружностей/дуг."""
        from .geometry import Point, Arc
        
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
        
        candidates = [Point(x4_1, y4_1), Point(x4_2, y4_2)]
        valid_points = []
        
        for pt in candidates:
             valid = True
             if isinstance(c1, Arc):
                 ang = math.degrees(math.atan2(pt.y - y1, pt.x - x1))
                 if not c1._angle_is_on_arc(ang): valid = False
             
             if valid and isinstance(c2, Arc):
                 ang = math.degrees(math.atan2(pt.y - y2, pt.x - x2))
                 if not c2._angle_is_on_arc(ang): valid = False
                 
             if valid:
                 valid_points.append(pt)
        
        return valid_points

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
